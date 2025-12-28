import streamlit as st
import json

from data.dataframe import load_csv
from agent.prompts import format_system_prompt
from agent.agent_loop import run_agent

st.set_page_config(
    page_title="Chat with CSV",
    layout="wide"
)

st.title("Chat with your CSV")

st.sidebar.title("Controls")
show_debug = st.sidebar.toggle("Show agent debug", value=False)


if "messages" not in st.session_state:
    st.session_state.messages = []


uploaded_file = st.file_uploader(
    "Upload a CSV file",
    type=["csv"]
)

if not uploaded_file:
    st.info("Upload a CSV to start chatting.")
    st.stop()


df, cols = load_csv(uploaded_file)


if not any(m["role"] == "system" for m in st.session_state.messages):
    system_prompt = format_system_prompt(
        path=uploaded_file.name,
        cols=cols
    )
    st.session_state.messages.append({
        "role": "system",
        "content": system_prompt
    })


with st.expander("Preview data", expanded=False):
    st.dataframe(df.head())


user_input = st.chat_input("Ask a question about the data")

if user_input:
    # Mutate state only
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

   
    run_agent(st.session_state.messages)


for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.chat_message("user").write(msg["content"])

    elif msg["role"] == "assistant" and "content" in msg:
        st.chat_message("assistant").write(msg["content"])


if show_debug:
    st.divider()
    st.subheader("Agent Debug Trace")

    for idx, msg in enumerate(st.session_state.messages):

        # Assistant tool calls
        if msg["role"] == "assistant" and "tool_calls" in msg:
            with st.expander(f"Tool call #{idx}", expanded=False):
                for call in msg["tool_calls"]:
                    st.markdown("**Tool name**")
                    st.code(call.function.name)

                    st.markdown("**Arguments (generated code)**")
                    st.code(call.function.arguments, language="json")

        # Tool execution results
        elif msg["role"] == "tool":
            with st.expander(f"Tool result #{idx}", expanded=False):
                try:
                    result = json.loads(msg["content"])
                except Exception:
                    result = {}

                st.markdown("**STDOUT**")
                st.code(result.get("stdout", ""))

                st.markdown("**ERROR**")
                st.code(result.get("error", ""))

                st.markdown("**LOCALS**")
                st.json(result.get("locals", {}))
