import streamlit as st
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import (
    send_chat_message, create_chat_session, get_chat_sessions, get_session_history_by_id,
    validate_subject, create_learning_plan, generate_quiz, submit_quiz, get_subjects,
    get_certificate, get_student_reports, decode_jwt_payload, logout
)

st.set_page_config(page_title="Student Dashboard", page_icon="🧑‍🎓", layout="wide")

if "token" not in st.session_state or st.session_state.get("role") != "student":
    st.warning("Please login as a student first.")
    st.stop()

# Ensure user_id is populated from token claims if missing
if "user_id" not in st.session_state:
    claims = decode_jwt_payload(st.session_state.get("token", ""))
    st.session_state["user_id"] = claims.get("user_id", 0)

# --- Sidebar: User Profile & Session Controls ---
with st.sidebar:
    st.markdown(f"### 🧑‍🎓 **{st.session_state.get('username', 'Student')}**")
    st.caption("Role: Enrolled Student")
    if st.button("🚪 Sign Out", use_container_width=True):
        logout()
    
    st.divider()
    st.title("Chat History")
    if st.button("➕ New Chat Session", use_container_width=True):
        st.session_state["active_session_id"] = None
        st.session_state.pop("learning_plan", None)
        st.session_state.pop("current_quiz", None)
        st.session_state.pop("quiz_result", None)
        st.rerun()

    sessions = get_chat_sessions(st.session_state["token"])
    if sessions:
        for s in sessions:
            label = s.get("title", f"Session {s.get('session_id', '')[:8]}")
            is_active = st.session_state.get("active_session_id") == s["session_id"]
            prefix = "👉 " if is_active else "💬 "
            if st.button(f"{prefix}{label}", key=f"sess_{s['session_id']}", use_container_width=True):
                st.session_state["active_session_id"] = s["session_id"]
                st.session_state.pop("current_quiz", None)
                st.session_state.pop("quiz_result", None)
                st.rerun()
    else:
        st.caption("No past sessions found.")

# --- Header ---
st.title(f"Welcome back, {st.session_state.get('username', 'Student')}! 👋")
st.caption("Your personalized AI-driven learning and evaluation environment.")

# --- Session Loading & Metadata ---
active_session_id = st.session_state.get("active_session_id")
session_data = {}
selected_subject = "General"

if active_session_id:
    session_data = get_session_history_by_id(active_session_id, st.session_state["token"])
    if isinstance(session_data, dict):
        selected_subject = session_data.get("subject", "General")
        if "learning_plan" in session_data and session_data["learning_plan"]:
            st.session_state["learning_plan"] = session_data["learning_plan"]

# --- Main Dashboard Tabs ---
tab_chat, tab_quiz, tab_reports = st.tabs(["💬 Live AI Tutor", "📝 Adaptive Quizzes", "📊 My Reports & Certificates"])

# ==========================================
# TAB 1: Live AI Tutor
# ==========================================
with tab_chat:
    if not active_session_id:
        st.subheader("🚀 Start a New Learning Session")
        subject_source = st.radio("Choose Subject Source", ["Preset", "Custom"], horizontal=True)
        
        selected_subject_init = ""
        selected_topics_init = []
        
        db_subjects_list = get_subjects(st.session_state["token"])
        db_subjects = {s["name"]: s.get("topics", []) for s in db_subjects_list} if db_subjects_list else {}

        if subject_source == "Preset":
            if not db_subjects:
                st.info("No preset subjects found in the database. Choose 'Custom' to explore any topic.")
            else:
                selected_subject_name = st.selectbox("Select Subject", list(db_subjects.keys()))
                if selected_subject_name:
                    selected_subject_init = selected_subject_name
                    available_topics = db_subjects.get(selected_subject_name, [])
                    selected_topics_init = st.multiselect("Select Focus Topics", available_topics, default=available_topics[:3] if available_topics else [])
        else:
            custom_input = st.text_input("Enter Subject Name (e.g., 'React.js', 'Quantum Physics', 'Calculus')")
            if st.button("🔍 Validate & Discover Topics"):
                if custom_input:
                    with st.spinner("Analyzing curriculum with AI..."):
                        data = validate_subject(custom_input, st.session_state["token"])
                        if data:
                            st.session_state["custom_subject_data"] = data
                        else:
                            st.error("Could not validate subject.")
            
            if "custom_subject_data" in st.session_state:
                data = st.session_state["custom_subject_data"]
                st.success(f"Curriculum verified: **{data.get('name')}**")
                selected_subject_init = data.get("name")
                all_topics = data.get("topics", [])
                selected_topics_init = st.multiselect("Select Topics to Cover", all_topics, default=all_topics[:4] if all_topics else [])

        if st.button("🚀 Start Learning Session", type="primary", use_container_width=True):
            if not selected_subject_init:
                st.error("Please specify a subject.")
            elif not selected_topics_init:
                st.error("Please select at least one topic.")
            else:
                with st.spinner("Initializing session & crafting personalized curriculum..."):
                    new_session_id = create_chat_session(selected_subject_init, selected_topics_init, st.session_state["token"])
                    if new_session_id:
                        plan = create_learning_plan(new_session_id, st.session_state["token"])
                        st.session_state["active_session_id"] = new_session_id
                        if plan:
                            st.session_state["learning_plan"] = plan
                        st.success("Session ready! Let's begin.")
                        st.rerun()
                    else:
                        st.error("Failed to start session.")
    else:
        # Display Active Session Layout
        col_main, col_plan = st.columns([3, 1])

        with col_plan:
            st.markdown("### 🗺️ **Learning Path**")
            plan = st.session_state.get("learning_plan", {})
            modules = plan.get("modules", []) if isinstance(plan, dict) else []
            if modules:
                for idx, mod in enumerate(modules):
                    with st.expander(f"Module {idx+1}: {mod.get('title', 'Unit')}", expanded=(idx == 0)):
                        st.write(mod.get("description", ""))
                        topics_list = mod.get("topics", [])
                        if topics_list:
                            st.caption(f"**Topics:** {', '.join(topics_list)}")
            else:
                st.info("General Learning Path active.")

        with col_main:
            history = session_data.get("messages", []) if isinstance(session_data, dict) else []
            
            # Chat history container
            chat_box = st.container()
            with chat_box:
                skip_next_model = False
                for message in history:
                    role = message.get("role", "user")
                    author = message.get("author")
                    visible = message.get("visible_to_student", True)
                    
                    if not visible or author in ["teacher", "teacher_model", "teacher_assistant", "model_to_teacher"]:
                        if author == "teacher":
                            skip_next_model = True
                        continue
                    
                    if skip_next_model and role != "user":
                        skip_next_model = False
                        continue
                    skip_next_model = False
                    
                    parts = message.get("parts", [])
                    content = parts[0] if isinstance(parts, list) and parts else str(parts)
                    
                    if role == "user":
                        with st.chat_message("user"):
                            st.markdown(content)
                    else:
                        with st.chat_message("assistant", avatar="🎓"):
                            st.markdown(content)

            # Chat input
            if prompt := st.chat_input("Ask a question or explain a concept..."):
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.spinner("AI Tutor is formulating an explanation..."):
                    response_text = send_chat_message(prompt, active_session_id, st.session_state["token"])
                
                if response_text:
                    with st.chat_message("assistant", avatar="🎓"):
                        st.markdown(response_text)
                    st.rerun()
                else:
                    st.error("Failed to get response from AI tutor.")

# ==========================================
# TAB 2: Adaptive Quizzes
# ==========================================
with tab_quiz:
    if not active_session_id:
        st.info("👉 Please select or start a learning chat session first to unlock its quiz.")
    else:
        diff = st.session_state.get("quiz_difficulty", "easy")
        
        # Difficulty badges
        badge_map = {
            "easy": "🟢 **Level: Easy**",
            "mid": "🟡 **Level: Intermediate**",
            "hard": "🔴 **Level: Advanced (Hard)**"
        }
        
        col_diff, col_reset = st.columns([3, 1])
        with col_diff:
            st.markdown(f"### 📝 {badge_map.get(diff, 'Adaptive Quiz')}")
        with col_reset:
            if st.button("🔄 Reset / New Quiz"):
                st.session_state.pop("current_quiz", None)
                st.session_state.pop("quiz_result", None)
                st.rerun()

        # Quiz Generation & Rendering
        if "current_quiz" not in st.session_state or st.session_state["current_quiz"] is None:
            with st.spinner(f"Generating {diff.capitalize()}-level assessment questions..."):
                quiz_data = generate_quiz(active_session_id, diff, st.session_state["token"])
                if quiz_data and quiz_data.get("questions"):
                    st.session_state["current_quiz"] = quiz_data
                else:
                    st.session_state["current_quiz"] = None

        quiz = st.session_state.get("current_quiz")
        quiz_result = st.session_state.get("quiz_result")

        if quiz_result:
            score = quiz_result.get("score", 0)
            total = quiz_result.get("total", 0)
            pct = quiz_result.get("percentage", 0)
            passed = quiz_result.get("passed", False)
            review = quiz_result.get("review", [])
            
            st.metric(label="Quiz Score", value=f"{score}/{total}", delta=f"{pct:.1f}%")
            
            if passed:
                st.success("🎉 Outstanding work! You passed this level.")
                if diff == "easy":
                    if st.button("Proceed to Intermediate Level 🟡", type="primary"):
                        st.session_state["quiz_difficulty"] = "mid"
                        st.session_state.pop("current_quiz", None)
                        st.session_state.pop("quiz_result", None)
                        st.rerun()
                elif diff == "mid":
                    if st.button("Proceed to Advanced (Hard) Level 🔴", type="primary"):
                        st.session_state["quiz_difficulty"] = "hard"
                        st.session_state.pop("current_quiz", None)
                        st.session_state.pop("quiz_result", None)
                        st.rerun()
                else:
                    st.balloons()
                    st.success("🏆 Mastery Achieved! You have passed all adaptive levels.")
                    st.session_state["passed_hard"] = True
                    if st.button("📜 Generate Verified Certificate", type="primary"):
                        cert_text = get_certificate(active_session_id, selected_subject, st.session_state["token"])
                        if cert_text:
                            st.session_state["certificate_markdown"] = cert_text
                            st.rerun()
            else:
                st.error("You did not reach the 70% threshold. Review the material with your AI tutor and try again!")
                if st.button("🔄 Try Quiz Again"):
                    st.session_state.pop("current_quiz", None)
                    st.session_state.pop("quiz_result", None)
                    st.rerun()
                    
            if review:
                st.divider()
                st.markdown("### 📋 **Assessment Breakdown & Explanations**")
                for idx, item in enumerate(review):
                    status_icon = "✅" if item.get("is_correct") else "❌"
                    with st.expander(f"{status_icon} Question {idx+1}: {item.get('text', '')}", expanded=not item.get("is_correct")):
                        st.markdown(f"**Your Answer:** {item.get('user_choice_text') or '*(No answer selected)*'}")
                        if not item.get("is_correct"):
                            st.markdown(f"**Correct Answer:** `{item.get('correct_option_text')}`")
                        else:
                            st.markdown("🎯 *Correctly answered!*")

        elif quiz and quiz.get("questions"):
            with st.form(f"quiz_form_{active_session_id}_{diff}"):
                answers = {}
                for i, q in enumerate(quiz["questions"]):
                    qid = str(q.get("id", i + 1))
                    st.markdown(f"**Question {i+1}:** {q.get('text', '')}")
                    options = q.get('options', [])
                    if options:
                        choice = st.radio(
                            "Select your answer:",
                            options,
                            key=f"opt_{active_session_id}_{diff}_{qid}_{i}"
                        )
                        answers[qid] = options.index(choice) if choice in options else -1
                    st.divider()

                if st.form_submit_button("Submit Assessment", type="primary", use_container_width=True):
                    quiz_ref = quiz.get("db_id") or quiz
                    result = submit_quiz(quiz_ref, answers, st.session_state["token"])
                    if result:
                        st.session_state["quiz_result"] = result
                    else:
                        st.error("Failed to evaluate quiz.")
                    st.rerun()
        else:
            st.warning("⚠️ Quiz questions could not be prepared at this moment.")

# ==========================================
# TAB 3: My Reports & Certificates
# ==========================================
with tab_reports:
    st.subheader("📊 Performance Reports & Certificates")
    
    col_rep, col_cert = st.columns([1, 1])

    with col_rep:
        st.markdown("#### 📑 Teacher Evaluations & Feedback")
        user_id = st.session_state.get("user_id", 0)
        reports = get_student_reports(user_id, st.session_state["token"]) if user_id else []
        
        if reports:
            for rep in reports:
                with st.expander(f"Report: {rep.get('subject', 'General')} — {str(rep.get('created_at', ''))[:10]}"):
                    st.markdown(rep.get("content", ""))
                    st.download_button(
                        label="📥 Download Report (.md)",
                        data=rep.get("content", ""),
                        file_name=f"Report_{rep.get('subject', 'general')}_{rep.get('id')}.md",
                        mime="text/markdown",
                        key=f"dl_rep_{rep.get('id')}"
                    )
        else:
            st.info("No evaluations generated yet. When your teacher analyzes your sessions, reports will appear here.")

    with col_cert:
        st.markdown("#### 📜 Course Certificates")
        
        if "certificate_markdown" in st.session_state and st.session_state["certificate_markdown"]:
            st.success("Verified Certificate Available for Download!")
            st.markdown(st.session_state["certificate_markdown"])
            st.download_button(
                label="📥 Download Official Certificate",
                data=st.session_state["certificate_markdown"],
                file_name=f"Certificate_{selected_subject}.md",
                mime="text/markdown",
                key="dl_cert_btn"
            )
        else:
            if not st.session_state.get("passed_hard"):
                st.warning("🔒 **Certificate Locked**")
                st.markdown("""
                To earn an official completion certificate:
                1. Complete your learning modules.
                2. Pass the **Easy** and **Intermediate** quizzes.
                3. Score 70%+ on the **Advanced (Hard)** quiz.
                """)
            else:
                if st.button("Generate Verified Certificate Now", type="primary"):
                    cert_text = get_certificate(active_session_id, selected_subject, st.session_state["token"])
                    if cert_text:
                        st.session_state["certificate_markdown"] = cert_text
                        st.rerun()
    