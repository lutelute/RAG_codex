#!/usr/bin/env python3
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from analysis_pipeline import analyze_question, plan_requirements

app = FastAPI()


class AnalyzeRequest(BaseModel):
    question: str
    dry_run: Optional[bool] = False


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    if not os.environ.get("LLAMA_MODEL_PATH"):
        raise HTTPException(status_code=400, detail="LLAMA_MODEL_PATH is not set")
    if req.dry_run:
        return {"plan": plan_requirements(req.question)}
    return analyze_question(req.question)


@app.get("/")
def root():
    html = """
    <html>
      <head><title>Local Power Analysis</title></head>
      <body>
        <h2>Local Power Analysis</h2>
        <p>Use POST /analyze with JSON {"question": "..."}.</p>
        <p>Example:</p>
        <pre>
curl -X POST http://127.0.0.1:8000/analyze \\
  -H "Content-Type: application/json" \\
  -d '{"question":"Run a case14 power flow with load_scale 1.2 and summarize."}'
        </pre>
      </body>
    </html>
    """
    return HTMLResponse(content=html)
