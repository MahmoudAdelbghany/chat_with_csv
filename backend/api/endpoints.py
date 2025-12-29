from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import io
import json

from backend.core.session import session_manager
from data.dataframe import load_csv

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        content = await file.read()
        # Create a file-like object
        file_obj = io.BytesIO(content)
        file_obj.name = file.filename # helper for load_csv if it uses name
        
        # Load dataframe
        df, cols = load_csv(file_obj)
        
        # Create session
        session_id = session_manager.create_session(df, cols)
        
        return JSONResponse({
            "sessionId": session_id,
            "filename": file.filename,
            "columns": cols,
            "preview": df.head().to_dict(orient='records')
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@router.post("/chat/{session_id}")
async def chat(session_id: str, request: ChatRequest):
    agent = session_manager.get_agent(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    
    agent.add_message("user", request.message)
    
    async def generate():
        try:
            for part in agent.run():
                # Yield each part as a JSON line
                yield json.dumps(part) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "content": f"Error: {str(e)}"}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
