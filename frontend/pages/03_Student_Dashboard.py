import streamlit as st
import sys
import os
from streamlit.components.v1 import html

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import send_chat_message, create_chat_session, get_chat_sessions, get_session_history_by_id

st.set_page_config(page_title="Student Dashboard", page_icon="🧑‍🎓")

if "token" not in st.session_state or st.session_state.get("role") != "student":
    st.warning("Please login as a student first.")
    st.stop()

st.title(f"Welcome, {st.session_state['username']}! 👋")
st.subheader("Your Personal AI Tutor")

# --- Sidebar History ---
st.sidebar.title("Chat History")
if st.sidebar.button("➕ New Chat"):
    st.session_state["active_session_id"] = None
    st.rerun()

sessions = get_chat_sessions(st.session_state["token"])
for s in sessions:
    label = s["title"]
    # We can use a button for each session
    if st.sidebar.button(label, key=s["session_id"]):
        st.session_state["active_session_id"] = s["session_id"]
        st.rerun()

# --- Main Area ---

SUBJECTS = {
    "C#": ["Syntax", "OOP", "Async/Await", "LINQ", "Delegates & Events"],
    "SQL Server": ["T-SQL", "Indexing", "Stored Procedures", "Joins", "Transactions"],
    ".NET": ["CLR", "Garbage Collection", "ASP.NET Core", "Entity Framework", "Dependency Injection"],
    "General": ["General"]
}

if "active_session_id" not in st.session_state or st.session_state["active_session_id"] is None:
    # --- Start New Session View ---
    st.subheader("Start a New Learning Session")
    
    subject = st.selectbox("Select Subject", list(SUBJECTS.keys()))
    available_topics = SUBJECTS.get(subject, [])
    selected_topics = st.multiselect("Select Topics", available_topics)
    
    if st.button("Start Chat"):
        with st.spinner("Creating session..."):
            session_id = create_chat_session(subject, selected_topics, st.session_state["token"])
            if session_id:
                st.session_state["active_session_id"] = session_id
                st.rerun()
            else:
                st.error("Failed to start session.")

else:
    # --- Active Chat View ---
    session_id = st.session_state["active_session_id"]
    
    # Fetch history
    history = get_session_history_by_id(session_id, st.session_state["token"])
    
    # Display Chat
    for message in history:
        role = message["role"]
        # Handle various part structures
        parts = message.get("parts", [])
        if isinstance(parts, list) and parts:
             content = parts[0]
        elif isinstance(parts, str):
             content = parts
        else:
             content = ""
        # Filter out teacher instructions (Intervention)
        author = message.get("author")
        if author == "teacher":
            continue

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        else:
            with st.chat_message("assistant"):
                st.markdown(content)
    
    # Input
    if prompt := st.chat_input("Ask me anything..."):
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.spinner("Thinking..."):
            response_text = send_chat_message(prompt, session_id, st.session_state["token"])
            
        if response_text:
            with st.chat_message("assistant"):
                st.markdown(response_text)
            # Rerun to update history view properly? Or just append? 
            # Appending is faster but history fetch ensures consistency.
            # Let's rely on st.rerun() to refresh the full history for simplicity and consistency
            st.rerun()
        else:
            st.error("Failed to get response.")
