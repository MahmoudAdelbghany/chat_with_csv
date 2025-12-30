from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class Dataset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    file_path: str
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: str = Field(index=True)
    
    conversations: List["Conversation"] = Relationship(back_populates="dataset")

class Conversation(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True) # UUID
    title: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    dataset_id: Optional[int] = Field(default=None, foreign_key="dataset.id")
    user_id: str = Field(index=True)
    
    dataset: Optional[Dataset] = Relationship(back_populates="conversations")
    messages: List["Message"] = Relationship(back_populates="conversation")

class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    role: str # user, assistant, tool
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    conversation_id: str = Field(foreign_key="conversation.id")
    
    conversation: Conversation = Relationship(back_populates="messages")
