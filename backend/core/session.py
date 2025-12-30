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
    async def create_conversation(self, dataset_id: int, title: str) -> str:
        async for session in get_session():
            conversation = Conversation(
                id=str(uuid.uuid4()),
                title=title,
                dataset_id=dataset_id
            )
            session.add(conversation)
            await session.commit()
            await session.refresh(conversation)
            return conversation.id
        return ""

    async def get_agent(self, conversation_id: str) -> Optional[CSVAgent]:
        # This regenerates the agent stateless-ly from DB context
        async for session in get_session():
            # 1. Fetch Conversation and Dataset
            stmt = select(Conversation).where(Conversation.id == conversation_id)
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

            # 2. Load DataFrame (from disk)
            # We need to reconstruct the file path.
            # Assuming file_path is stored in Dataset
            try:
                df = pd.read_csv(dataset.file_path)
                cols = df.columns.tolist()
            except FileNotFoundError:
                # Fallback or error
                return None

            # 3. Fetch recent messages
            # For now, let's fetch all. In future, limit to last N.
            msg_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp)
            msg_result = await session.exec(msg_stmt)
            messages_db = msg_result.all()

            # 4. Initialize Agent
            system_prompt = format_system_prompt(cols)
            agent = CSVAgent(system_prompt=system_prompt, context={"df": df})
            
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

    async def list_conversations(self):
        async for session in get_session():
            stmt = select(Conversation).order_by(Conversation.created_at.desc())
            result = await session.exec(stmt)
            return result.all()

    async def get_conversation_details(self, conversation_id: str):
        async for session in get_session():
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await session.exec(stmt)
            conversation = result.first()
            if not conversation:
                return None
            
            # Fetch messages
            msg_stmt = select(Message).where(Message.conversation_id == conversation_id).order_by(Message.timestamp)
            msg_result = await session.exec(msg_stmt)
            messages = msg_result.all()
            
            
            return conversation, messages

    async def delete_conversation(self, conversation_id: str):
        async for session in get_session():
            # Delete messages first (cascade usually handles this but let's be explicit/safe)
            msg_stmt = select(Message).where(Message.conversation_id == conversation_id)
            results = await session.exec(msg_stmt)
            for msg in results.all():
                await session.delete(msg)
            
            # Delete conversation
            stmt = select(Conversation).where(Conversation.id == conversation_id)
            result = await session.exec(stmt)
            conversation = result.first()
            if conversation:
                await session.delete(conversation)
            
            await session.commit()
            return True

session_manager = SessionManager()
