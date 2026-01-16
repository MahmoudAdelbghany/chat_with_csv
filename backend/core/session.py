import uuid
from typing import Optional
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.core.database import get_session
from backend.models import Conversation, Dataset, Message
from agent.service import CSVAgent
from agent.prompts import format_system_prompt
import pandas as pd
import os

class SessionManager:
    async def create_conversation(self, dataset_id: int, title: str, user_id: str) -> str:
        async for session in get_session():
            conversation = Conversation(
                id=str(uuid.uuid4()),
                title=title,
                dataset_id=dataset_id,
                user_id=user_id
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            return conversation.id
        return ""

    async def get_agent(self, conversation_id: str, user_id: str) -> Optional[CSVAgent]:
        # This regenerates the agent stateless-ly from DB context
        async for session in get_session():
            # 1. Fetch Conversation and Dataset
            stmt = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
            result = await session.exec(stmt)
            conversation = result.first()
            if not conversation:
                return None
            
            if not conversation.dataset_id:
                # Should not happen in new logic, but handle legacy? 
                return None
                
            dataset_stmt = select(Dataset).where(Dataset.id == conversation.dataset_id)
            dataset_result = await session.exec(dataset_stmt)
            dataset = dataset_result.first()
            
            if not dataset:
                return None

            # 2. Load DataFrame (from storage)
            # Fetch file from S3/Storage to local temp
            from backend.core.storage import storage
            
            # We must use a unique temp path per dataset to avoid collisions but also maybe reuse if exists?
            # For simplicity and statelessness (Railway), always download.
            # Use /tmp for ephemeral storage
            import os
            
            # Extract filename from path or just use dataset ID
            temp_filename = f"dataset_{dataset.id}.csv"
            temp_path = os.path.join("/tmp", temp_filename)
            
            # Download file only if it doesn't exist locally
            if not os.path.exists(temp_path):
                from core.logger import logger
                logger.info(f"Downloading dataset {dataset.id} to {temp_path}")
                storage.download_file(dataset.file_path, temp_path)
            else:
                from core.logger import logger
                logger.info(f"Dataset {dataset.id} found in cache at {temp_path}")
            
            try:
                # Try multiple encodings for CSV files that aren't UTF-8
                df = None
                encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
                
                for encoding in encodings_to_try:
                    try:
                        df = pd.read_csv(temp_path, encoding=encoding)
                        break  # Success!
                    except UnicodeDecodeError:
                        continue
                
                if df is None:
                    from core.logger import logger
                    logger.error(f"Could not decode CSV file {temp_path} with any supported encoding")
                    return None
                    
                cols = df.columns.tolist()
            except Exception as e:
                from core.logger import logger
                logger.error(f"Failed to read CSV file {temp_path}: {e}")
                # If CSV is corrupt or some other error
                return None

            # 3. Fetch recent messages
            # For now, let's fetch all. In future, limit to last N.
            msg_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp)
            msg_result = await session.exec(msg_stmt)
            messages_db = msg_result.all()

            # 4. Initialize Agent with session_id for artifact scoping
            system_prompt = format_system_prompt(cols)
            agent = CSVAgent(system_prompt=system_prompt, context={"df": df}, session_id=conversation_id)
            
            # 5. Replay history into agent
            # We skip the system prompt as it's already added in __init__
            for msg in messages_db:
                agent.add_message(msg.role, msg.content)
            
            return agent
            
    async def save_message(self, conversation_id: str, role: str, content: str):
        async for session in get_session():
            message = Message(
                role=role,
                content=content,
                conversation_id=conversation_id
            )
            session.add(message)
            await session.commit()

    async def list_conversations(self, user_id: str):
        async for session in get_session():
            stmt = select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.created_at.desc())
            result = await session.exec(stmt)
            return result.all()

    async def get_conversation_details(self, conversation_id: str, user_id: str):
        async for session in get_session():
            stmt = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
            result = await session.exec(stmt)
            conversation = result.first()
            if not conversation:
                return None
            
            # Fetch messages
            msg_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp)
            msg_result = await session.exec(msg_stmt)
            messages = msg_result.all()
            
            
            return conversation, messages

    async def delete_conversation(self, conversation_id: str, user_id: str):
        async for session in get_session():
            # Delete messages first (cascade usually handles this but let's be explicit/safe)
            msg_stmt = select(Message).where(Message.conversation_id == conversation_id)
            results = await session.exec(msg_stmt)
            for msg in results.all():
                await session.delete(msg)
            
            # Delete conversation
            stmt = select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
            result = await session.exec(stmt)
            conversation = result.first()
            if conversation:
                await session.delete(conversation)
            
            await session.commit()
            return True

session_manager = SessionManager()
