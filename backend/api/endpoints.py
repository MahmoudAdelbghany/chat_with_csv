from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import pandas as pd
import io
import json
import os
import shutil
import uuid
from datetime import datetime

from backend.core.session import session_manager
from backend.core.database import get_session
from backend.models import Dataset
from backend.core.auth import get_user_id
from fastapi import Depends
from data.dataframe import load_csv

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user_id: str = Depends(get_user_id)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        # Generate unique filename
        file_ext = file.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file to disk
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Create Dataset record in DB
        async for session in get_session():
            dataset = Dataset(
                filename=file.filename,
                file_path=file_path,
                uploaded_at=datetime.utcnow(),
                user_id=user_id
            )
            session.add(dataset)
            await session.commit()
            await session.refresh(dataset)
            dataset_id = dataset.id
            break # Expecting single session yield

        # Load dataframe for preview (and validation)
        df = pd.read_csv(file_path)
        cols = df.columns.tolist()
        
        # Create session (Conversation)
        session_id = await session_manager.create_conversation(dataset_id=dataset_id, title=file.filename, user_id=user_id)
        
        return JSONResponse({
            "sessionId": session_id,
            "filename": file.filename,
            "columns": cols,
            "preview": df.head().to_dict(orient='records')
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@router.post("/chat/{session_id}")
async def chat(session_id: str, request: ChatRequest, user_id: str = Depends(get_user_id)):
    agent = await session_manager.get_agent(session_id, user_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Save user message
    await session_manager.save_message(session_id, "user", request.message)
    agent.add_message("user", request.message)
    
    async def generate():
        full_response = ""
        try:
            async for part in agent.run():
                # Yield each part as a JSON line
                json_part = json.dumps(part)
                yield json_part + "\n"
                
                # Accumulate actual response content for saving
                if part["type"] == "delta":
                    full_response += part["content"]
                elif part["type"] == "status":
                    pass 
                elif part["type"] == "tool_code":
                    code_html = f"\n<details><summary>Executing Code</summary>\n\n```python\n{part['content']}\n```\n"
                    full_response += code_html
                    yield json.dumps({"type": "delta", "content": code_html}) + "\n"
                elif part["type"] == "tool_output":
                    output_html = f"\n**Output:**\n\n```\n{part['content']}\n```\n\n</details>\n"
                    full_response += output_html
                    yield json.dumps({"type": "delta", "content": output_html}) + "\n"
            
            # Save assistant response
            if full_response:
                await session_manager.save_message(session_id, "assistant", full_response)
                
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            yield json.dumps({"type": "error", "content": error_msg}) + "\n"
            # Optionally save error message as assistant response?

    return StreamingResponse(generate(), media_type="application/x-ndjson")

@router.get("/conversations")
async def list_conversations(user_id: str = Depends(get_user_id)):
    conversations = await session_manager.list_conversations(user_id)
    return [
        {
            "id": c.id,
            "title": c.title,
            "created_at": c.created_at,
            "dataset_id": c.dataset_id # In future we might want dataset filename here
        }
        for c in conversations
    ]

@router.get("/conversations/{session_id}")
async def get_conversation(session_id: str, user_id: str = Depends(get_user_id)):
    result = await session_manager.get_conversation_details(session_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conversation, messages = result
    
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": conversation.created_at,
        "dataset_id": conversation.dataset_id,
        "messages": [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.timestamp
            }
            for m in messages
        ]
    }

@router.delete("/conversations/{session_id}")
async def delete_conversation(session_id: str, user_id: str = Depends(get_user_id)):
    await session_manager.delete_conversation(session_id, user_id)
    return {"status": "success", "message": "Conversation deleted"}
