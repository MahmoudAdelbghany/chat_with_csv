from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
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
from backend.core.storage import storage
from fastapi import Depends
from data.dataframe import load_csv

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

# UPLOAD_DIR is handled by storage service now

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), user_id: str = Depends(get_user_id)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")
    
    try:
        # Generate unique filename for storage key
        file_ext = file.filename.split('.')[-1]
        unique_filename = f"{uuid.uuid4()}.{file_ext}"
        
        # Save file to storage (S3 or local)
        # Returns the path/key stored
        stored_path = storage.upload_file(file.file, unique_filename)
        
        # Create Dataset record in DB
        async for session in get_session():
            dataset = Dataset(
                filename=file.filename,
                file_path=stored_path, # S3 key or local path
                uploaded_at=datetime.utcnow(),
                user_id=user_id
            )
            session.add(dataset)
            await session.commit()
            await session.refresh(dataset)
            dataset_id = dataset.id
            break
        
        # Load preview. For cloud storage, we might need to download it back or read bytes before upload
        # But we already uploaded. Let's download to a temp buffer or just read the uploaded file if local
        # Optimization: We could have read into memory before upload, but for huge files that's bad.
        # Let's download it to a temp file for preview.
        # Actually, for preview we just need head.
        # To avoid re-downloading immediately, maybe we can read the file object before upload?
        # But upload_file consumes it. 
        # Let's just download it to a temp location for the preview generation.
        
        temp_preview_path = f"/tmp/{unique_filename}"
        storage.download_file(stored_path, temp_preview_path)
        
        df = pd.read_csv(temp_preview_path)
        cols = df.columns.tolist()
        preview_data = df.head().to_dict(orient='records')
        
        # Clean up temp file
        if os.path.exists(temp_preview_path):
            os.remove(temp_preview_path)
        
        # Create session
        session_id = await session_manager.create_conversation(dataset_id=dataset_id, title=file.filename, user_id=user_id)
        
        return JSONResponse({
            "sessionId": session_id,
            "filename": file.filename,
            "columns": cols,
            "preview": preview_data
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")

@router.post("/chat/{session_id}")
async def chat(session_id: str, request: ChatRequest, user_id: str = Depends(get_user_id)):
    try:
        agent = await session_manager.get_agent(session_id, user_id)
    except FileNotFoundError:
        # This handles the case where S3 or local file is missing
        # We use a 410 Gone to indicate resource is missing permanently
        raise HTTPException(status_code=410, detail="The dataset file for this conversation is missing. It may have been deleted due to inactivity or server restart.")
    except Exception as e:
        from core.logger import logger
        logger.error(f"Failed to initialize chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to initialize chat: {str(e)}")

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
                    # We want the tool code to be in a details block
                    code_html = f"\n<details><summary>Executing Code</summary>\n\n```python\n{part['content']}\n```\n"
                    full_response += code_html
                    yield json.dumps({"type": "delta", "content": code_html}) + "\n"
                elif part["type"] == "artifact":
                    # Close the code execution details to show artifact prominently
                    # We used to close details here.
                    # Important: Artifact content might contain HTML (iframe).
                    # We must ensure we are closing the PREVIOUS details block (Executing Code).
                    artifact_html = f"\n</details>\n\n{part['content']}\n\n<details><summary>Execution Output</summary>\n"
                    full_response += artifact_html
                    yield json.dumps({"type": "delta", "content": artifact_html}) + "\n"
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

@router.get("/files/{filename}")
async def get_file(filename: str, user_id: str = Depends(get_user_id)):
    """
    Serve files (plots, reports) from storage.
    """
    try:
        # Create a temp location
        temp_path = f"/tmp/{filename}"
        # If running locally, storage might just point to a path, but let's re-use download interface for abstraction
        # Ideally storage should have a get_file_stream or presigned url method.
        # For now, download to temp and stream.
        
        # Security check: prevent directory traversal
        if ".." in filename or "/" in filename:
             raise HTTPException(status_code=400, detail="Invalid filename")
             
        storage.download_file(filename, temp_path)
        
        # Determine media type
        media_type = "application/octet-stream"
        if filename.endswith(".png"): media_type = "image/png"
        elif filename.endswith(".html"): media_type = "text/html"
        elif filename.endswith(".json"): media_type = "application/json"
        
        return FileResponse(temp_path, media_type=media_type, filename=filename, content_disposition_type="inline")
        
    except Exception as e:
        # If file not found
        raise HTTPException(status_code=404, detail="File not found")
