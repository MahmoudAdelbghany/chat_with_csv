import streamlit as st
import sys
import os

# Add root directory to sys.path to allow imports from core and data
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data.dataframe import load_csv
from agent.prompts import format_system_prompt
from agent.service import CSVAgent
from core.config import settings

st.set_page_config(page_title="CSV Chat Analyst", layout="wide")
st.title("Chat with your CSV")

if "agent" not in st.session_state:
    st.session_state.agent = None

if "messages" not in st.session_state:
    st.session_state.messages = []

uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

if uploaded_file:
    df, cols = load_csv(uploaded_file)
    st.dataframe(df.head())

    # Render chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Initialize agent if not already done or if file changed (logic could be improved)
    if st.session_state.agent is None:
        system_prompt = format_system_prompt(cols)
        st.session_state.agent = CSVAgent(system_prompt=system_prompt, context={"df": df})
        
    user_input = st.chat_input("Ask about the data")

    if user_input:
        # Display user message
        st.chat_message("user").write(user_input)
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Add to agent
        st.session_state.agent.add_message("user", user_input)
        
        # Run agent
        with st.chat_message("assistant"):
            container = st.empty()
            full_response = ""
            
            # Stream response
            for partial in st.session_state.agent.run():
                # Primitive streaming/status display
                # If partial starts with "Code Output" or similar, maybe format it?
                # For now just append to full response for the final block, 
                # or update status.
                
                # We can handle intermediate steps better if agent yields structured events
                # But our agent yields strings.
                
                if partial.startswith("Running code") or partial.startswith("Code Output"):
                   with st.status("Analyzing...", expanded=False):
                       st.markdown(f"```{partial}```")
                else:
                    full_response = partial
                    container.markdown(full_response)
            
            # Save assistant message
            st.session_state.messages.append({"role": "assistant", "content": full_response})

    # Render history (excluding the new one we just added?) 
    # Actually streamlit reruns. We should render history at the top.
    # Refactoring rendering logic:
    
    # Clear previous run display to avoid duplication? 
    # Streamlit flows top to bottom. 
    # We should render existing history first.
    
    # Logic fix:
    # 1. Render history.
    # 2. Handle input.
    
    # Let's adjust the file content in the next turn if needed, or do it right now.
