import json
from agent.client import get_client
from agent.tools import TOOLS, run_code_capture

client = get_client()


def run_agent(messages, model="mistralai/devstral-2512:free", max_steps=6):
    for _ in range(max_steps):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        msg = response.choices[0].message

        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            result = run_code_capture(args["code"])

            messages.append({
                "role": "assistant",
                "tool_calls": msg.tool_calls
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": "run_code_capture",
                "content": json.dumps(result)
            })
        else:
            messages.append({
                "role": "assistant",
                "content": msg.content
            })
            return msg.content

    return "Max steps reached"
