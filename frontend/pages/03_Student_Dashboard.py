import streamlit as st
import sys
import os
from streamlit.components.v1 import html

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import (
    send_chat_message, create_chat_session, get_chat_sessions, get_session_history_by_id,
    validate_subject, create_learning_plan, generate_quiz, submit_quiz, get_subjects,
    get_certificate
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

# --- Main Area ---

# Removed hardcoded SUBJECTS

if "active_session_id" not in st.session_state or st.session_state["active_session_id"] is None:
    # --- Start New Session View ---
    st.subheader("Start a New Learning Session")
    
    # Subject Selection Mode
    subject_source = st.radio("Choose Subject Source", ["Preset", "Custom"])
    
    selected_subject = ""
    selected_topics = []
    
    # Fetch Subjects from DB
    db_subjects_list = get_subjects(st.session_state["token"])
    # Convert to dict for easier lookup: {name: topics}
    db_subjects = {s["name"]: s["topics"] for s in db_subjects_list}

    if subject_source == "Preset":
        if not db_subjects:
            st.warning("No subjects found in database. Try adding a Custom subject.")
        
        selected_subject_name = st.selectbox("Select Subject", list(db_subjects.keys()))
        if selected_subject_name:
             selected_subject = selected_subject_name
             available_topics = db_subjects.get(selected_subject, [])
             selected_topics = st.multiselect("Select Topics", available_topics, default=available_topics[:3] if available_topics else [])
             
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
            if st.button("Back to Chat"):
                st.session_state["quiz_mode"] = False
                st.rerun()
            
    if st.session_state.get("quiz_mode"):
        diff = st.session_state.get("quiz_difficulty", "easy")
        st.subheader(f"📝 Adaptive Quiz ({diff.capitalize()} Level)")
        
        if "current_quiz" not in st.session_state or st.session_state["current_quiz"] is None:
            with st.spinner(f"Generating {diff.capitalize()} level quiz..."):
                quiz_data = generate_quiz(session_id, diff, st.session_state["token"])
                if quiz_data and quiz_data.get("questions"):
                    st.session_state["current_quiz"] = quiz_data
                else:
                    st.session_state["current_quiz"] = None
        
        quiz = st.session_state.get("current_quiz")
        
        if "quiz_result" in st.session_state and st.session_state["quiz_result"]:
            res = st.session_state["quiz_result"]
            st.write(f"**Score:** {res.get('score', 0)}/{res.get('total', 0)} ({res.get('percentage', 0):.0f}%)")
            
            if res.get('passed'):
                st.success("Passed! 🎉")
                current_diff = st.session_state.get("quiz_difficulty", "easy")
                if current_diff == "easy":
                    if st.button("Proceed to Mid Level"):
                        st.session_state["quiz_difficulty"] = "mid"
                        st.session_state.pop("current_quiz", None)
                        st.session_state.pop("quiz_result", None)
                        st.rerun()
                elif current_diff == "mid":
                    if st.button("Proceed to Hard Level"):
                        st.session_state["quiz_difficulty"] = "hard"
                        st.session_state.pop("current_quiz", None)
                        st.session_state.pop("quiz_result", None)
                        st.rerun()
                else: 
                    st.balloons()
                    st.success("You are an Expert! 🏆")
                    if st.button("Generate Certificate"):
                        cert_text = get_certificate(session_id, selected_subject or "Adaptive Course", st.session_state["token"])
                        if cert_text:
                            st.download_button("Download Certificate", cert_text, file_name=f"Certificate_{session_id}.md")
            else:
                st.error("Not quite there. Review the material and try again.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Retake Quiz"):
                        st.session_state.pop("current_quiz", None)
                        st.session_state.pop("quiz_result", None)
                        st.rerun()
                with col2:
                    if st.button("💬 Back to Chat", key="back_from_failed_quiz"):
                        st.session_state["quiz_mode"] = False
                        st.session_state.pop("quiz_result", None)
                        st.session_state.pop("current_quiz", None)
                        st.rerun()
        elif quiz and quiz.get("questions"):
            with st.form("quiz_form"):
                answers = {}
                for i, q in enumerate(quiz["questions"]):
                    qid = str(q.get("id", i + 1))
                    st.markdown(f"**Question {i+1}: {q.get('text', '')}**")
                    options = q.get('options', [])
                    if options:
                        choice = st.radio(
                            "Choose:",
                            options,
                            key=f"quiz_opt_{session_id}_{diff}_{qid}_{i}"
                        )
                        answers[qid] = options.index(choice) if choice in options else -1
                    st.markdown("---")
                
                submitted = st.form_submit_button("Submit Quiz")
                if submitted:
                    result = submit_quiz(quiz, answers, st.session_state["token"])
                    if result:
                        st.session_state["quiz_result"] = result
                    else:
                        st.error("Failed to submit quiz. Please try again.")
                    st.rerun()
        else:
            st.warning("⚠️ Quiz could not be generated at this time.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Try Generating Again"):
                    st.session_state.pop("current_quiz", None)
                    st.session_state.pop("quiz_result", None)
                    st.rerun()
            with col2:
                if st.button("💬 Back to Chat", key="back_from_empty_quiz"):
                    st.session_state["quiz_mode"] = False
                    st.session_state.pop("current_quiz", None)
                    st.session_state.pop("quiz_result", None)
                    st.rerun()
    