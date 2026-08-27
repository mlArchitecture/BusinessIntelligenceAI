from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="BusinessIntelligence.AI Engine")

class VarianceRequest(BaseModel):
    csv_path: str
    analysis_date: str

class VarianceResponse(BaseModel):
    narrative: str
    evidence_json: str

@app.post("/api/v1/analyze-variance", response_model=VarianceResponse)
async def analyze_variance_endpoint(request: VarianceRequest):
    try:
        initial_state = {
            "csv_path": request.csv_path,
            "analysis_date": request.analysis_date,
            "evidence_json": "",
            "historical_r2_score": 0.0,
            "narrative": ""
        }
        
        result = orchestrator.invoke(initial_state)
        
        return VarianceResponse(
            narrative=result["narrative"],
            evidence_json=result["evidence_json"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
