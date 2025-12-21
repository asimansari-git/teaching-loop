import streamlit as st
import sys
import os
from streamlit.components.v1 import html

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import (
    send_chat_message, create_chat_session, get_chat_sessions, get_session_history_by_id,
    validate_subject, create_learning_plan, generate_quiz, submit_quiz
)

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
    
    # Subject Selection Mode
    subject_source = st.radio("Choose Subject Source", ["Preset", "Custom"])
    
    selected_subject = ""
    selected_topics = []
    
    if subject_source == "Preset":
        selected_subject = st.selectbox("Select Subject", list(SUBJECTS.keys()))
        if selected_subject:
             available_topics = SUBJECTS.get(selected_subject, [])
             selected_topics = st.multiselect("Select Topics", available_topics, default=available_topics[:3])
             
    else:
        custom_input = st.text_input("Enter Subject Name (e.g., 'ReactJS', 'Physics')")
        if st.button("Validate & Fetch Topics"):
            if custom_input:
                with st.spinner("Validating..."):
                    data = validate_subject(custom_input, st.session_state["token"])
                    if data:
                        st.session_state["custom_subject_data"] = data
                    else:
                        st.error("Could not validate subject.")
        
        if "custom_subject_data" in st.session_state:
            data = st.session_state["custom_subject_data"]
            st.success(f"Validated as: {data.get('name')}")
            selected_subject = data.get("name")
            all_topics = data.get("topics", [])
            selected_topics = st.multiselect("Select Topics", all_topics, default=all_topics[:3])

    if st.button("Start Chat"):
        if not selected_subject:
            st.error("Please select a subject.")
        elif not selected_topics:
            st.error("Please select at least one topic.")
        else:
            with st.spinner("Creating session & Learning Plan..."):
                session_id = create_chat_session(selected_subject, selected_topics, st.session_state["token"])
                if session_id:
                    # Generate Learning Plan
                    plan = create_learning_plan(session_id, st.session_state["token"])
                    if plan:
                        st.session_state["active_session_id"] = session_id
                        st.session_state["learning_plan"] = plan # Store plan in session state
                        st.rerun()
                    else:
                        st.error("Session created but failed to generate learning plan.")
                else:
                    st.error("Failed to start session.")

else:
    # --- Active Chat View ---    
    session_id = st.session_state["active_session_id"]
    # Fetch history and learning plan
    session_data = get_session_history_by_id(session_id, st.session_state["token"])
    
    history = []
    if isinstance(session_data, dict):
        history = session_data.get("messages", [])
        learning_plan = session_data.get("learning_plan")
        selected_subject = session_data.get("subject")
        if learning_plan:
            st.session_state["learning_plan"] = learning_plan
    elif isinstance(session_data, list): # Fallback for backward compatibility
        history = session_data
    
    if not st.session_state.get("quiz_mode"):
        # Standard Chat View
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

    
    # Layout: Sidebar for Learning Path, Main for Chat
    with st.sidebar:
        st.markdown("---")
        st.subheader("🎓 Learning Path")
        # Check if plan exists in state, if not maybe safe to ignore or fetch?
        # For simplicity assume it's there or user just created it. 
        # Ideally fetch from DB if missing.
        
        if "learning_plan" in st.session_state:
            plan = st.session_state["learning_plan"]
            modules = plan.get("modules", [])
            for idx, mod in enumerate(modules):
                 st.write(f"**{idx+1}. {mod['title']}**")
                 st.caption(mod['description'])
                 mod_topics = ", ".join(mod.get("topics", []))
                 if mod_topics:
                     st.caption(f"_{mod_topics}_")
        
        st.markdown("---")
        if st.button("Take Quiz"):
            st.session_state["quiz_mode"] = True
            st.rerun()
            
    if st.session_state.get("quiz_mode"):
        st.subheader("📝 Adaptive Quiz")
        if "current_quiz" not in st.session_state:
             with st.spinner("Generating Quiz..."):
                 # Determine difficulty? Start with easy.
                 diff = st.session_state.get("quiz_difficulty", "easy")
                 quiz_data = generate_quiz(session_id, diff, st.session_state["token"])
                 st.session_state["current_quiz"] = quiz_data
        
        quiz = st.session_state["current_quiz"]
        if quiz and "questions" in quiz:
            with st.form("quiz_form"):
                answers = {}
                for q in quiz["questions"]:
                    st.write(f"**{q['text']}**")
                    choice = st.radio("Choose:", q['options'], key=q['id'])
                    # Map choice back to index
                    answers[str(q['id'])] = q['options'].index(choice) if choice else -1
                
                submitted = st.form_submit_button("Submit Quiz")
                if submitted:
                    result = submit_quiz(quiz, answers, st.session_state["token"])
                    st.session_state["quiz_result"] = result
                    st.rerun()
        
        if "quiz_result" in st.session_state:
            res = st.session_state["quiz_result"]
            st.write(f"**Score:** {res['score']}/{res['total']} ({res['percentage']}%)")
            
            if res['passed']:
                st.success("Passed! 🎉")
                # Logic for Next Level
                current_diff = st.session_state.get("quiz_difficulty", "easy")
                if current_diff == "easy":
                    if st.button("Proceed to Mid Level"):
                        st.session_state["quiz_difficulty"] = "mid"
                        del st.session_state["current_quiz"]
                        del st.session_state["quiz_result"]
                        st.rerun()
                elif current_diff == "mid":
                    if st.button("Proceed to Hard Level"):
                        st.session_state["quiz_difficulty"] = "hard"
                        del st.session_state["current_quiz"]
                        del st.session_state["quiz_result"]
                        st.rerun()
                else: 
                     st.balloons()
                     st.success("You are an Expert! 🏆")
                     st.download_button("Download Certificate", f"Certificate: Expert in {selected_subject}", file_name="certificate.txt")
                     
            else:
                st.error("Not quite there. Review the material and try again.")
                if st.button("Back to Chat"):
                    st.session_state["quiz_mode"] = False
                    del st.session_state["quiz_result"] # Keep quiz to retry? or reset?
                    del st.session_state["current_quiz"]
                    st.rerun()
    