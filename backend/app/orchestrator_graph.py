import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from forecasting_engine import analyze_forecast_variance
import duckdb

# 1. Update State Definition
class GraphState(TypedDict):
    target_kpi: str
    analysis_date: str
    evidence_json: str
    historical_r2_score: float
    narrative: str
    sub_queries: list[str]
    retrieved_context: str

# 2. Execution Node: Run the ML Forecast Model
def run_forecast_ml_node(state: GraphState):
    json_output = analyze_forecast_variance(state["analysis_date"])
    data = json.loads(json_output)
    
    if "error" in data:
        return {
            "evidence_json": json_output,
            "historical_r2_score": 0.0
        }
        
    return {
        "evidence_json": json_output,
        "historical_r2_score": data["model_metrics"]["historical_r2_score"]
    }

# 3. Routing Node: The Confidence Gate
def confidence_gate(state: GraphState):
    # Only proceed if the historical model explains at least 70% of the variance
    if state["historical_r2_score"] >= 0.70:
        return "generate_narrative"
    return "abstain"

def retrieve_data_node(state: GraphState):
    conn = duckdb.connect("business_intelligence.db")
    date_str = state["analysis_date"]
    
    query = """
        SELECT * FROM kpi_data 
        WHERE date <= ?::DATE 
        ORDER BY date DESC 
        LIMIT 5
    """
    df = conn.execute(query, [date_str]).df()
    conn.close()
    
    context_text = df.to_json(orient="records")
    return {"retrieved_context": context_text}

def generate_multi_queries_node(state: GraphState):
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0, thinking_level='high')
    
    prompt = PromptTemplate.from_template(
        "You are an advanced BI Agent. Given the target KPI '{kpi}' and date '{date}', "
        "generate 3 distinct search queries to query internal historical logs and metrics "
        "to perform a comprehensive root cause analysis.\n"
        "Return ONLY a JSON list of strings under the key 'queries'. Example: "
        '{{"queries": ["query 1", "query 2", "query 3"]}}'
    )
    
    chain = prompt | llm | JsonOutputParser()
    result = chain.invoke({"kpi": state["target_kpi"], "date": state["analysis_date"]})
    
    queries = result.get("queries", [state["target_kpi"]])
    return {"sub_queries": queries}

# 4. Execution Node: LLM Generation
def generate_narrative_node(state: GraphState):
    # llm_pro = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, max_retries=0)
    llm_flash = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0, thinking_level='high')
    # llm_with_fallback = llm_pro.with_fallbacks([llm_flash])
    
    prompt = PromptTemplate.from_template(
        "You are a strict business intelligence assistant.\n"
        "We forecasted the target KPI for today, but the actual value differed. "
        "Translate this exact mathematical output into a business summary.\n\n"
        "Your response must include:\n"
        "- What happened (Actual vs Forecast).\n"
        "- The primary drivers causing this variance (Ranked by weight).\n"
        "- Logical business recommendations to solve or capitalize on this variance based on the drivers.\n\n"
        "Do not calculate any numbers. Only use the provided data.\n"
        "Data: {evidence}"
    )
    
    # chain = prompt | llm_with_fallback
    chain = prompt | llm_flash | StrOutputParser()
    response = chain.invoke({
        "evidence": state["evidence_json"],
        "sub_queries": state["sub_queries"],
        "retrieved_context": state["retrieved_context"]
    })
    return {"narrative": response}

# 5. Execution Node: System Abstention
def abstain_node(state: GraphState):
    data = json.loads(state["evidence_json"])
    if "error" in data:
        message = f"System Notification: {data['error']}"
    else:
        message = "System Abstention: The model's historical R² score is too low to reliably explain today's variance. Manual investigation required."
    
    return {"narrative": message}

# 6. Graph Compilation
workflow = StateGraph(GraphState)

workflow.add_node("generate_queries", generate_multi_queries_node)
workflow.add_node("retrieve_data", retrieve_data_node)
workflow.add_node("run_forecast_ml", run_forecast_ml_node)
workflow.add_node("generate_narrative", generate_narrative_node)
workflow.add_node("abstain", abstain_node)

workflow.set_entry_point("generate_queries")

workflow.add_edge("generate_queries", "retrieve_data")
workflow.add_edge("retrieve_data", "run_forecast_ml")

workflow.add_conditional_edges(
    "run_forecast_ml",
    confidence_gate,
    {
        "generate_narrative": "generate_narrative",
        "abstain": "abstain"
    }
)

workflow.add_edge("generate_narrative", END)
workflow.add_edge("abstain", END)

orchestrator = workflow.compile()