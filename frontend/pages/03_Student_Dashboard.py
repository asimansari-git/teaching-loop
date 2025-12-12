import streamlit as st
import sys
import os
from streamlit.components.v1 import html

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import send_chat_message, get_chat_history

st.set_page_config(page_title="Student Dashboard", page_icon="🧑‍🎓")

if "token" not in st.session_state or st.session_state.get("role") != "student":
    st.warning("Please login as a student first.")
    st.stop()

st.title(f"Welcome, {st.session_state['username']}! 👋")
st.subheader("Your Personal AI Tutor")

SUBJECTS = {
    "C#": ["Syntax", "OOP", "Async/Await", "LINQ", "Delegates & Events"],
    "SQL Server": ["T-SQL", "Indexing", "Stored Procedures", "Joins", "Transactions"],
    ".NET": ["CLR", "Garbage Collection", "ASP.NET Core", "Entity Framework", "Dependency Injection"],
    "General": ["General"]
}

subject = st.sidebar.selectbox("Select Subject", list(SUBJECTS.keys()))
available_topics = SUBJECTS.get(subject, [])
selected_topics = st.sidebar.multiselect("Select Topics (Optional)", available_topics)

# --- Chat Interface ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Load history on first load or subject change
# Ideally we should cache this or handle state management better
# For simplicity, we fetch fresh history on page load
history = get_chat_history(subject, st.session_state["token"])
st.session_state.messages = history

for message in st.session_state.messages:
    role = message["role"]
    content = message["parts"][0] if isinstance(message["parts"], list) else message["parts"]
    
    # Display logic matching standard Streamlit chat
    if role == "user":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            st.markdown(content)

# Chat Input
if prompt := st.chat_input("Ask me anything..."):
    # Add user message to state and display
    st.session_state.messages.append({"role": "user", "parts": [prompt]})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Send to backend
    with st.spinner("Thinking..."):
        response_text = send_chat_message(prompt, subject, st.session_state["token"], selected_topics)
    
    if response_text:
        # Add assistant response to state and display
        st.session_state.messages.append({"role": "model", "parts": [response_text]})
        with st.chat_message("assistant"):
            st.markdown(response_text)
    else:
        st.error("Failed to get response from AI.")
