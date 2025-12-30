import json
import asyncio
from typing import List, AsyncGenerator, Any, Dict

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

    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs the agent loop and yields partial responses or tool outputs.
        Yields dict: {"type": "delta"|"status"|"error", "content": str}
        """
        steps = 0
        while steps < settings.MAX_STEPS:
            try:
                # synchronous limiter for now, or make it async if needed. 
                # Assuming limiter.acquire() is fast enough or we leave it sync.
                limiter.acquire() 
            except RateLimitExceeded as e:
                logger.warning("Rate limit exceeded")
                yield {"type": "error", "content": f"Error: {str(e)}"}
                return

            try:
                logger.info(f"Calling LLM with {len(self.messages)} messages")
                stream = await self.client.chat.completions.create(
                    model=settings.MODEL_NAME,
                    messages=self.messages,
                    tools=TOOLS,
                    tool_choice="auto",
                    stream=True
                )
            except Exception as e:
                logger.error(f"LLM API Error: {e}", exc_info=True)
                yield {"type": "error", "content": f"Error calling LLM: {str(e)}"}
                return

            # Accumulators
            full_content = ""
            current_tool_calls: Dict[int, Dict[str, Any]] = {}

            async for chunk in stream:
                delta = chunk.choices[0].delta
                
                if delta.content:
                    full_content += delta.content
                    yield {"type": "delta", "content": delta.content}

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
                self.messages.append({"role": "assistant", "content": full_content})

            if current_tool_calls:
                tool_calls_list = [v for k, v in sorted(current_tool_calls.items())]
                
                msg_data = {
                    "role": "assistant",
                    "content": full_content if full_content else None,
                    "tool_calls": tool_calls_list
                }
                
                if full_content:
                    self.messages.pop()
                    
                self.messages.append(msg_data)

                for tool_call_data in tool_calls_list:
                    func_name = tool_call_data["function"]["name"]
                    args_str = tool_call_data["function"]["arguments"]
                    logger.info(f"Tool Call: {func_name} args={args_str}")

                    yield {"type": "status", "content": "Running code..."}

                    if func_name == "run_code_capture":
                        try:
                            args = json.loads(args_str)
                            # Run code execution in a separate thread to avoid blocking loop
                            # Since run_code_capture uses exec()
                            result: ToolResult = await asyncio.to_thread(
                                run_code_capture, 
                                args["code"], 
                                initial_locals=self.context
                            )
                            
                            logger.debug(f"Tool Output: {result.stdout[:100]}...")
                            
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_data["id"],
                                "name": "run_code_capture",
                                "content": json.dumps(result.model_dump())
                            })
                            
                            if result.error:
                                yield {"type": "status", "content": f"Code Error: {result.error}"}
                            else:
                                yield {"type": "status", "content": f"Code Output:\n{result.stdout}"}
                                
                        except Exception as e:
                            logger.error(f"Tool Execution Error: {e}", exc_info=True)
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_data["id"],
                                "name": func_name,
                                "content": f"Error executing tool: {str(e)}"
                            })
            elif not full_content:
                 pass
            else:
                 return
        
        yield {"type": "status", "content": "Max steps reached without final answer."}
