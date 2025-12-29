import uuid
from typing import Dict, Optional, Any
from agent.service import CSVAgent

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, CSVAgent] = {}
        self.files: Dict[str, Any] = {} # Store file context if needed separately

    def create_session(self, df, cols) -> str:
        session_id = str(uuid.uuid4())
        # We initialize the agent lazily or here. Let's initialize here.
        from agent.prompts import format_system_prompt
        system_prompt = format_system_prompt(cols)
        agent = CSVAgent(system_prompt=system_prompt, context={"df": df})
        self.sessions[session_id] = agent
        return session_id

    def get_agent(self, session_id: str) -> Optional[CSVAgent]:
        return self.sessions.get(session_id)

session_manager = SessionManager()
