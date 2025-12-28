from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict

class ToolCallFunction(BaseModel):
    name: str
    arguments: str  # arguments are often a JSON string

class ToolCall(BaseModel):
    id: str
    type: str = "function"
    function: ToolCallFunction

class AgentMessage(BaseModel):
    role: str
    content: Optional[str] = None
    tool_calls: Optional[List[ToolCall]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None

class ToolResult(BaseModel):
    stdout: str
    error: Optional[str] = None
    locals: Dict[str, str]
