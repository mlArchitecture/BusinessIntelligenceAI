import json
from typing import TypedDict
from langgraph.graph import StateGraph, END
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI
from forecasting_engine import analyze_forecast_variance

# 1. Update State Definition
class GraphState(TypedDict):
    target_kpi: str
    analysis_date: str
    evidence_json: str
    historical_r2_score: float
    narrative: str

# 2. Execution Node: Run the ML Forecast Model
def run_forecast_ml_node(state: GraphState):
    json_output = analyze_forecast_variance(state["analysis_date"])
    data = json.loads(json_output)
    
    # Handle the safety catch if today's data is missing
    if "error" in data:
        return {
            "evidence_json": json_output,
            "historical_r2_score": 0.0 # Forces the gate to route to abstain
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

# 4. Execution Node: LLM Generation
def generate_narrative_node(state: GraphState):
    # llm_pro = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, max_retries=0)
    llm_flash = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=1, thinking_level='high')
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
    response = chain.invoke({"evidence": state["evidence_json"]})
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

workflow.add_node("run_forecast_ml", run_forecast_ml_node)
workflow.add_node("generate_narrative", generate_narrative_node)
workflow.add_node("abstain", abstain_node)

workflow.set_entry_point("run_forecast_ml")

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