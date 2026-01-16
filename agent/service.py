import json
import asyncio
import os
import shutil
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
    def __init__(self, system_prompt: str = "", context: Dict[str, Any] = None, session_id: str = None):
        self.client = get_client()
        self.messages: List[Dict[str, Any]] = []
        self.context = context or {}
        self.session_id = session_id  # Required for artifact scoping
        if system_prompt:
            self.messages.append({"role": "system", "content": system_prompt})

    def add_message(self, role: str, content: str):
        self.messages.append({"role": role, "content": content})

    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Runs the agent loop and yields partial responses or tool outputs.
        Yields dict: {"type": "delta"|"status"|"error"|"artifact"|"tool_code"|"tool_output", "content": str}
        """
        # Import artifact service here to avoid circular imports
        from backend.core.artifacts import artifact_service
        
        steps = 0
        while steps < settings.MAX_STEPS:
            try:
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

                    if func_name == "run_code_capture":
                        try:
                            args = json.loads(args_str)
                            code_to_run = args.get("code", "")
                            
                            # Yield code first
                            yield {"type": "tool_code", "content": code_to_run}

                            # Run code execution in a separate thread
                            result: ToolResult = await asyncio.to_thread(
                                run_code_capture, 
                                code_to_run, 
                                initial_locals=self.context
                            )
                            
                            logger.debug(f"Tool Output: {result.stdout[:100] if result.stdout else '(empty)'}...")
                            
                            # Initialize artifact_msg outside the conditional to avoid reference errors
                            artifact_msg = ""
                            
                            if result.error:
                                yield {"type": "tool_output", "content": f"Error: {result.error}"}
                            else:
                                # Process Artifacts using the new service
                                artifacts_to_cleanup = []
                                
                                for artifact_path in result.artifacts:
                                    logger.info(f"[ARTIFACT LIFECYCLE] Processing artifact: {artifact_path}")
                                    try:
                                        filename = os.path.basename(artifact_path)
                                        conversation_id = self.session_id or "default"
                                        logger.info(f"[ARTIFACT LIFECYCLE] Filename={filename}, conversation_id={conversation_id}")
                                        
                                        # Save to permanent storage
                                        logger.info(f"[ARTIFACT LIFECYCLE] Saving artifact to permanent storage...")
                                        key = artifact_service.save_artifact(artifact_path, conversation_id)
                                        logger.info(f"[ARTIFACT LIFECYCLE] Artifact saved with key: {key}")
                                        url = artifact_service.get_artifact_url(key)
                                        logger.info(f"[ARTIFACT LIFECYCLE] Artifact URL: {url}")
                                        artifacts_to_cleanup.append(artifact_path)
                                        
                                        # Generate appropriate markdown based on file type
                                        if filename.endswith(".png"):
                                            md = f"\n![Generated Plot]({url})\n"
                                            logger.info(f"[ARTIFACT LIFECYCLE] Generated PNG artifact markdown: {md}")
                                            logger.info(f"[ARTIFACT LIFECYCLE] Yielding PNG artifact event")
                                            yield {"type": "artifact", "content": md}
                                            logger.info(f"[ARTIFACT LIFECYCLE] PNG artifact event yielded")
                                            artifact_msg += f"\n[Generated File: {filename}]"
                                            
                                        elif filename.endswith(".html"):
                                            md = f'\n<div class="interactive-plot" data-src="{url}" style="width:100%; height:600px;"></div>\n\n<a href="{url}" target="_blank" rel="noopener noreferrer">Open Full Report</a>\n'
                                            logger.info(f"[ARTIFACT LIFECYCLE] Generated HTML artifact markdown (length={len(md)}): {md[:200]}...")
                                            logger.info(f"[ARTIFACT LIFECYCLE] Yielding HTML artifact event")
                                            yield {"type": "artifact", "content": md}
                                            logger.info(f"[ARTIFACT LIFECYCLE] HTML artifact event yielded successfully")
                                            artifact_msg += f"\n[Generated File: {filename}]"
                                            
                                        elif filename.endswith(".json"):
                                            # Read JSON for LLM context
                                            try:
                                                with open(artifact_path, "r") as f:
                                                    data = json.load(f)
                                                    summary = self._extract_json_summary(data, filename)
                                                    if summary:
                                                        result.stdout += f"\n\n[System] PROFILING REPORT SUMMARY:\n{summary}\n"
                                            except Exception as e:
                                                logger.error(f"Failed to read JSON artifact: {e}")
                                        else:
                                            # Generic file - just note it was created
                                            artifact_msg += f"\n[Generated File: {filename}]"
                                            
                                    except Exception as e:
                                        logger.error(f"Failed to process artifact {artifact_path}: {e}", exc_info=True)
                                        artifact_msg += f"\n[Error processing {filename}: {str(e)}]"
                                
                                # Cleanup temp artifact files after upload
                                for path in artifacts_to_cleanup:
                                    try:
                                        os.remove(path)
                                        # Also try to remove the parent temp directory if empty
                                        parent = os.path.dirname(path)
                                        if parent and os.path.isdir(parent) and not os.listdir(parent):
                                            os.rmdir(parent)
                                    except Exception:
                                        pass

                            self.messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call_data["id"],
                                "name": "run_code_capture",
                                "content": json.dumps(result.model_dump())
                            })

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

    def _extract_json_summary(self, data: dict, filename: str) -> str:
        """Extract a summary from JSON data (e.g., YData Profiling report)."""
        summary = []
        summary.append(f"### Detailed YData Profiling Report for {filename}")
        
        # 1. Alerts (CRITICAL)
        alerts = data.get("alerts", [])
        if alerts:
            summary.append("\n#### 🚨 Alerts (High Priority)")
            for alert in alerts:
                summary.append(f"- {alert}")
        else:
            summary.append("\n#### Alerts: None found.")
        
        # 2. Variables Statistics
        summary.append("\n#### 📊 Variables Statistics")
        variables = data.get("variables", {})
        for var_name, stats in variables.items():
            var_type = stats.get("type", "Unknown")
            n_missing = stats.get("n_missing", 0)
            p_missing = stats.get("p_missing", 0)
            
            var_info = [f"**{var_name}** ({var_type})"]
            var_info.append(f"Missing: {n_missing} ({p_missing:.1%})")
            
            if var_type == "Numeric":
                for stat in ["mean", "std", "min", "max", "skewness", "kurtosis"]:
                    val = stats.get(stat)
                    if val is not None:
                        var_info.append(f"{stat.capitalize()}: {val:.4f}")
            elif var_type == "Categorical":
                n_unique = stats.get("n_unique")
                if n_unique is not None:
                    var_info.append(f"Unique: {n_unique}")
            elif var_type == "Boolean":
                count = stats.get("count")
                if count is not None:
                    var_info.append(f"Count: {count}")

            summary.append("- " + ", ".join(var_info))
        
        # 3. Correlations
        correlations = data.get("correlations", {})
        if correlations:
            summary.append(f"\n#### 🔗 Correlations Available: {', '.join(correlations.keys())}")
            summary.append("(Refer to Alerts for significant high correlations)")

        summary_text = "\n".join(summary)
        
        # Truncate if too long
        if len(summary_text) > 50000:
            summary_text = summary_text[:50000] + "... (truncated)"
        
        return summary_text
