import streamlit as st
from data.dataframe import load_csv
from agent.prompts import format_system_prompt
from agent.agent_loop import run_agent

st.set_page_config(page_title="CSV Chat Analyst", layout="wide")
st.title("Chat with your CSV")

if "messages" not in st.session_state:
    st.session_state.messages = []

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    df, cols = load_csv(uploaded_file)

    if not any(m["role"] == "system" for m in st.session_state.messages):
        system_prompt = format_system_prompt(uploaded_file.name, cols)
        st.session_state.messages.append({
            "role": "system",
            "content": system_prompt
        })

    st.dataframe(df.head())

    user_input = st.chat_input("Ask about the data")

    if user_input:
        # mutate state only
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })

        run_agent(st.session_state.messages)  # agent appends assistant

    
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])

        elif msg["role"] == "assistant" and "content" in msg:
            st.chat_message("assistant").write(msg["content"])
