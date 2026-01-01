
import asyncio
from unittest.mock import MagicMock, patch
import os
import json
import sys

# Add root to path
sys.path.append(os.getcwd())

from agent.service import CSVAgent
from agent.models import ToolResult

async def test_agent_handle_json_artifact():
    print("Testing agent artifact handling...")
    
    # Mock everything needed to instantiate CSVAgent or just test the logic if isolated
    agent = CSVAgent()
    agent.client = MagicMock()
    
    # Mock settings
    with patch("agent.service.settings") as mock_settings:
        mock_settings.MAX_STEPS = 1
        mock_settings.MODEL_NAME = "test-model"
        
        # Mock LLM response to trigger tool call
        mock_chunk_tool = MagicMock()
        mock_chunk_tool.choices[0].delta.content = None
        mock_tool_call = MagicMock(index=0, id="call_1")
        mock_tool_call.function.name = "run_code_capture"
        mock_tool_call.function.arguments = json.dumps({"code": "print('hi')"})
        
        mock_chunk_tool.choices[0].delta.tool_calls = [mock_tool_call]
        
        # Mock stream
        async def mock_create(*args, **kwargs):
            async def run_stream():
                yield mock_chunk_tool
            return run_stream()
        
        agent.client.chat.completions.create = mock_create
        
        # Mock run_code_capture
        with patch("agent.service.run_code_capture") as mock_run:
            # Create a dummy json file
            with open("/tmp/test_report.json", "w") as f:
                json.dump({"summary": "This is a test summary"}, f)
            
            with open("/tmp/test_plot.html", "w") as f:
                f.write("<html></html>")
                
            mock_run.return_value = ToolResult(
                stdout="Computed stuff.",
                stderr="",
                locals={},
                artifacts=["/tmp/test_report.json", "/tmp/test_plot.html"]
            )
            
            # Mock storage
            with patch("backend.core.storage.storage") as mock_storage:
                mock_storage.upload_file.return_value = "s3_key"
                
                # Capture yields
                yields = []
                async for y in agent.run():
                    yields.append(y)
                
                # Check results
                iframe_found = False
                for y in yields:
                    if y["type"] == "artifact" and "<iframe" in y["content"]:
                        iframe_found = True
                        print(f"PASS: Found iframe: {y['content'][:50]}...")
                
                if not iframe_found:
                    print("FAIL: HTML Artifact should be rendered as iframe")
                    sys.exit(1)
                
                # Check for JSON content in tool_output
                json_found = False
                for y in yields:
                    if y["type"] == "tool_output" and "This is a test summary" in y["content"]:
                        json_found = True
                        print(f"PASS: Found JSON content in output.")
                        
                if not json_found:
                    print("FAIL: JSON content should be appended to tool output")
                    sys.exit(1)
                    
    print("All tests passed!")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    loop.run_until_complete(test_agent_handle_json_artifact())
