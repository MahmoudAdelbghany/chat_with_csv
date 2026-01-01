import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import traceback
from datetime import datetime

from core.client import get_client
from agent.executor import TOOLS, run_code_capture
from agent.prompts import SYSTEM_PROMPT_TEMPLATE, format_system_prompt
from agent.models import ToolResult
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

                    # yield {"type": "status", "content": "Running code..."} 


                    if func_name == "run_code_capture":
                        try:
                            args = json.loads(args_str)
                            code_to_run = args.get("code", "")
                            
                            # Yield code first
                            yield {"type": "tool_code", "content": code_to_run}

                            # Run code execution in a separate thread to avoid blocking loop
                            # Since run_code_capture uses exec()
                            result: ToolResult = await asyncio.to_thread(
                                run_code_capture, 
                                code_to_run, 
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
                                yield {"type": "tool_output", "content": f"Error: {result.error}"}
                            else:
                                # Process Artifacts
                                artifact_msg = ""
                                if result.artifacts:
                                    from backend.core.storage import storage
                                    import uuid
                                    import os
                                    
                                    for artifact_path in result.artifacts:
                                        filename = os.path.basename(artifact_path)
                                        unique_name = f"artifact_{uuid.uuid4()}_{filename}"
                                        
                                        # Upload
                                        with open(artifact_path, "rb") as f:
                                            storage.upload_file(f, unique_name)
                                        
                                        url = f"/api/files/{unique_name}"
                                        if filename.endswith(".png"):
                                            md = f"\n![Generated Plot]({url})\n"
                                            yield {"type": "artifact", "content": md}
                                            artifact_msg += f"\n[Generated File: {filename}]"
                                        elif filename.endswith(".html"):
                                            # Render iframe for interactive plots
                                            # Use a generic div with data attribute to avoid iframe stripping by markdown parsers
                                            md = f'\n<div class="interactive-plot" data-src="{url}" style="width:100%; height:600px;"></div>\n\n<a href="{url}" target="_blank" rel="noopener noreferrer">Open Full Report</a>\n'
                                            logger.info(f"Generated HTML Artifact: {md}")
                                            yield {"type": "artifact", "content": md}
                                            artifact_msg += f"\n[Generated File: {filename}]"
                                        elif filename.endswith(".json"):
                                            # Read JSON for LLM context
                                            try:
                                                with open(artifact_path, "r") as f:
                                                    data = json.load(f)
                                                    
                                                    # Smart extraction for YData Profiling
                                                    summary = []
                                                    summary.append(f"### detailed YData Profiling Report for {filename}")
                                                    
                                                    # 1. Alerts (CRITICAL)
                                                    alerts = data.get("alerts", [])
                                                    if alerts:
                                                        summary.append("\n#### 🚨 Alerts (High Priority)")
                                                        for alert in alerts:
                                                            summary.append(f"- {alert}")
                                                    else:
                                                        summary.append("\n#### Alerts: None found.")
                                                    
                                                    # 2. Variables Statistics (Detailed)
                                                    summary.append("\n#### 📊 Variables Statistics")
                                                    variables = data.get("variables", {})
                                                    for var_name, stats in variables.items():
                                                        var_type = stats.get("type", "Unknown")
                                                        n_missing = stats.get("n_missing", 0)
                                                        p_missing = stats.get("p_missing", 0)
                                                        
                                                        # Basic info
                                                        var_info = [f"**{var_name}** ({var_type})"]
                                                        var_info.append(f"Missing: {n_missing} ({p_missing:.1%})")
                                                        
                                                        if var_type == "Numeric":
                                                            # Numeric Stats
                                                            mean = stats.get("mean")
                                                            std = stats.get("std")
                                                            min_val = stats.get("min")
                                                            max_val = stats.get("max")
                                                            skew = stats.get("skewness")
                                                            kurtosis = stats.get("kurtosis")
                                                            
                                                            if mean is not None: var_info.append(f"Mean: {mean:.4f}")
                                                            if std is not None: var_info.append(f"Std: {std:.4f}")
                                                            if min_val is not None: var_info.append(f"Min: {min_val}")
                                                            if max_val is not None: var_info.append(f"Max: {max_val}")
                                                            if skew is not None: var_info.append(f"Skewness: {skew:.4f}")
                                                            if kurtosis is not None: var_info.append(f"Kurtosis: {kurtosis:.4f}")
                                                            
                                                        elif var_type == "Categorical":
                                                            # Categorical Stats
                                                            n_unique = stats.get("n_unique")
                                                            if n_unique is not None: var_info.append(f"Unique: {n_unique}")
                                                            
                                                        elif var_type == "Boolean":
                                                            count = stats.get("count")
                                                            var_info.append(f"Count: {count}")

                                                        summary.append("- " + ", ".join(var_info))
                                                    
                                                    # 3. Correlations
                                                    # Dump high correlation warnings if in alerts, but explicitly mentioning availability
                                                    correlations = data.get("correlations", {})
                                                    if correlations:
                                                        summary.append(f"\n#### 🔗 Correlations Available: {', '.join(correlations.keys())}")
                                                        summary.append("(Refer to Alerts for significant high correlations)")

                                                    summary_text = "\n".join(summary)

                                                    # Increase Limit significantly
                                                    if len(summary_text) > 50000:
                                                        summary_text = summary_text[:50000] + "... (truncated)"
                                                    
                                                    result.stdout += f"\n\n[System] PROFILING REPORT SUMMARY:\n{summary_text}\n"
                                            except Exception as e:
                                                logger.error(f"Failed to read JSON artifact: {e}")

                                yield {"type": "tool_output", "content": result.stdout + artifact_msg}
                                
                        except Exception as e:
                            logger.error(f"Tool Execution Error: {e}", exc_info=True)
                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_data["id"],
                                "name": func_name,
                                "content": f"Error executing tool: {str(e)}"
                            })
                            yield {"type": "tool_output", "content": f"System Error: {str(e)}"}
            elif not full_content:
                 pass
            else:
                 return
        
        yield {"type": "status", "content": "Max steps reached without final answer."}
