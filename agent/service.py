import json
from typing import List, Generator, Any, Dict

from core.client import get_client
from agent.executor import TOOLS, run_code_capture
from agent.models import AgentMessage, ToolCall, ToolResult
from core.config import settings
from core.logger import logger
from core.ratelimit import limiter, RateLimitExceeded

class CSVAgent:
    def __init__(self, system_prompt: str = "", context: Dict[str, Any] = None):
        self.client = get_client()
        self.messages: List[Dict[str, Any]] = []
        self.context = context or {}
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    def run(self) -> Generator[str, None, None]:
        """
        Runs the agent loop and yields partial responses or tool outputs.
        """
        steps = 0
        while steps < settings.MAX_STEPS:
            try:
                limiter.acquire()
            except RateLimitExceeded as e:
                logger.warning("Rate limit exceeded")
                yield f"Error: {str(e)}"
                return

            try:
                logger.info(f"Calling LLM with {len(self.messages)} messages")
                stream = self.client.chat.completions.create(
                    model=settings.MODEL_NAME,
                    messages=self.messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    stream=True
                )
            except Exception as e:
                logger.error(f"LLM API Error: {e}", exc_info=True)
                yield f"Error calling LLM: {str(e)}"
                return

            # Accumulators
            full_content = ""
            current_tool_calls: Dict[int, Dict[str, Any]] = {}

            for chunk in stream:
                delta = chunk.choices[0].delta
                
                # Handle Content
                if delta.content:
                    full_content += delta.content
                    yield full_content

                # Handle Tool Calls
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in current_tool_calls:
                            current_tool_calls[idx] = {
                                "id": "",
                                "type": "function",
                                "function": {"name": "", "arguments": ""}
                            }
                        
                        if tc.id:
                            current_tool_calls[idx]["id"] += tc.id
                        
                        if tc.function:
                            if tc.function.name:
                                current_tool_calls[idx]["function"]["name"] += tc.function.name
                            if tc.function.arguments:
                                current_tool_calls[idx]["function"]["arguments"] += tc.function.arguments

            steps += 1

            # Process Results
            if full_content:
                # Text response
                self.messages.append({"role": "assistant", "content": full_content})
                # If we had content, we are likely done or asking for user input next
                # But if there are also tool calls (rare in same message for some models, common for others), we handle them too.
                # Usually it's either/or in standard OpenAI/Mistral tool use flow, 
                # OR content comes before tool calls (Thinking).

            if current_tool_calls:
                # Reconstruct tool calls list
                tool_calls_list = [v for k, v in sorted(current_tool_calls.items())]
                
                # Append assistant message with tools
                # Note: If we already appended content above, we might need to merge or append a separate message?
                # OpenAI usually expects one message with both content and tool_calls if they happen together.
                
                msg_data = {
                    "role": "assistant",
                    "content": full_content if full_content else None,
                    "tool_calls": tool_calls_list
                }
                
                # If we already appended a message for content above, we should correct it to include the tool calls
                if full_content:
                    # Remove the partial content-only message and replace with full message
                    self.messages.pop()
                    
                self.messages.append(msg_data)

                for tool_call_data in tool_calls_list:
                    func_name = tool_call_data["function"]["name"]
                    args_str = tool_call_data["function"]["arguments"]
                    logger.info(f"Tool Call: {func_name} args={args_str}")

                    yield f"Running code..."

                    if func_name == "run_code_capture":
                        try:
                            args = json.loads(args_str)
                            result: ToolResult = run_code_capture(args["code"], initial_locals=self.context)
                            
                            logger.debug(f"Tool Output: {result.stdout[:100]}...")
                            
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_data["id"],
                                "name": "run_code_capture",
                                "content": json.dumps(result.model_dump())
                            })
                            
                            if result.error:
                                yield f"Code Error: {result.error}"
                            else:
                                yield f"Code Output:\n{result.stdout}"
                                
                        except Exception as e:
                            logger.error(f"Tool Execution Error: {e}", exc_info=True)
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_data["id"],
                                "name": func_name,
                                "content": f"Error executing tool: {str(e)}"
                            })
            elif not full_content:
                 # No content and no tool calls?
                 pass
            else:
                 # Content only, already handled
                 return
        
        yield "Max steps reached without final answer."
