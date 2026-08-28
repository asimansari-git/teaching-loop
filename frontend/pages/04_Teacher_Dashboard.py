import streamlit as st
import sys
import os
import pandas as pd

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import (
    get_students, generate_report, get_student_reports, get_student_sessions_for_teacher, 
    get_session_history_by_id, send_chat_message, upload_content, get_pending_content, 
    update_chunk, verify_item, logout
)

st.set_page_config(page_title="Teacher Dashboard", page_icon="🧑‍🏫", layout="wide")

if "token" not in st.session_state or st.session_state.get("role") != "teacher":
    st.warning("Please login as a teacher first.")
    st.stop()

# --- Sidebar: Teacher Profile & Actions ---
with st.sidebar:
    st.markdown(f"### 🧑‍🏫 **{st.session_state.get('username', 'Teacher')}**")
    st.caption("Role: Verified Educator")
    if st.button("🚪 Sign Out", use_container_width=True):
        logout()
    
    st.divider()
    st.markdown("### 📌 Quick Guidelines")
    st.caption("• Monitor student conversations live.")
    st.caption("• Intervene seamlessly without student awareness.")
    st.caption("• Curate and index RAG teaching material.")

st.title(f"Teacher Command Center 🧑‍🏫")
st.caption(f"Logged in as: **{st.session_state.get('username', 'Teacher')}**")

tab1, tab2, tab3, tab4 = st.tabs(["👥 Student List", "📊 Reports & Analytics", "🕵️ Live Intervention", "📚 Knowledge Base (RAG)"])

students = get_students(st.session_state["token"])

# ==========================================
# TAB 1: Student List
# ==========================================
with tab1:
    st.subheader("Enrolled Students in Organization")
    if students:
        search_query = st.text_input("🔍 Filter students by username...", "", key="student_search_query")
        filtered_students = [s for s in students if search_query.lower() in s.get("username", "").lower()] if search_query else students
        
        if filtered_students:
            df = pd.DataFrame(filtered_students)
            st.dataframe(df[["id", "username", "role"]], use_container_width=True)
            st.caption(f"Showing {len(filtered_students)} of {len(students)} student(s)")
        else:
            st.info(f"No students matching '{search_query}'.")
    else:
        st.info("No students currently registered in your organization.")

# ==========================================
# TAB 3: Live Intervention
# ==========================================
with tab3:
    st.subheader("Discreet Teacher Intervention")
    st.caption("Inject pedagogical directions directly into the AI Tutor's system context. Instructions remain completely invisible to the student.")
    if students:
        selected_student_username_int = st.selectbox("Select Student for Intervention", [s["username"] for s in students], key="int_student_select")
        # Fetch sessions
        sessions_int = get_student_sessions_for_teacher(selected_student_username_int, st.session_state["token"])
        
        if sessions_int:
            session_options_int = {s["title"]: s for s in sessions_int}
            selected_session_title_int = st.selectbox("Select Session to Join", list(session_options_int.keys()))
            selected_session_int = session_options_int[selected_session_title_int]
            session_id_int = selected_session_int["session_id"]
            
            st.divider()
            st.write(f"**Chat History: {selected_session_title_int}**")
            
            # Fetch and display history
            history_int = get_session_history_by_id(session_id_int, st.session_state["token"])
            
            # Display Chat (Container for scroll)
            chat_container = st.container(height=400)
            with chat_container:
                for message in history_int["messages"]:
                    role = message["role"]
                    author = message.get("author")
                    
                    parts = message.get("parts", [])
                    content = parts[0] if isinstance(parts, list) and parts else str(parts)
                    
                    if role == "user":
                        if author == "teacher":
                            with st.chat_message("user", avatar="🧑‍🏫"):
                                st.write(f"*(Teacher Instruction)*: {content}")
                        else:
                            with st.chat_message("user"):
                                st.markdown(content)
                    else:
                        with st.chat_message("assistant"):
                            st.markdown(content)
            
            # Teacher Input
            if prompt_int := st.chat_input("Send instruction to AI (Hidden from Student)..."):
                with st.spinner("Sending instruction..."):
                     # Send with updated logic if possible, or reliance on backend knowing user is teacher
                     # The backend routers/chat_router.py uses current_user.role.
                     # If user is teacher, author will be set to "teacher"?
                     # Let's check backend/routers/chat_router.py logic... 
                     # It calls chat_service.generate_response(..., role=current_user.role).
                     # And chat_service.generate_response calls save_message(..., author=role).
                     # So as long as we are logged in as teacher, author="teacher". Correct.
                     
                     response_text = send_chat_message(prompt_int, session_id_int, st.session_state["token"])
                     if response_text:
                         st.success("Instruction sent!")
                         st.rerun()
                     else:
                         st.error("Failed to send instruction.")
        else:
             st.info("Selected student has no active sessions.")
    else:
        st.warning("No students available.")

with tab2:
    st.subheader("Student Reports")
    
    if students:
        selected_student_username = st.selectbox("Select Student", [s["username"] for s in students])
        selected_student = next(s for s in students if s["username"] == selected_student_username)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Reports for {selected_student['username']}**")
            reports = get_student_reports(selected_student["id"], st.session_state["token"])
            if reports:
                for report in reports:
                    with st.expander(f"{report['subject']} - {report['created_at']}"):
                        st.markdown(report['content'])
                        st.download_button(
                            label="Download Report",
                            data=report['content'],
                            file_name=f"report_{selected_student['username']}_{report['subject']}.md",
                            mime="text/markdown",
                            key=f"download_{report['id']}"
                        )
            else:
                st.info("No reports available.")

        with col2:
            st.write("**Generate New Report**")
            
            # Fetch sessions for the selected student
            sessions = get_student_sessions_for_teacher(selected_student_username, st.session_state["token"])
            
            if sessions:
                session_options = {s["title"]: s for s in sessions}
                selected_session_title = st.selectbox("Select Session", list(session_options.keys()))
                selected_session = session_options[selected_session_title]
                
                if st.button("Generate Report"):
                    with st.spinner("Analyzing chat history and generating report..."):
                        new_report = generate_report(
                            selected_student["id"], 
                            selected_session["session_id"],
                            selected_session["subject"],
                            st.session_state["token"]
                        )
                        if new_report:
                            st.success("Report generated successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to generate report.")
            else:
                st.info("Student has no chat sessions.")
    else:
        st.warning("No students available to generate reports for.")

with tab4:
    st.subheader("Course Knowledge Base & Document Curation")
    st.caption("Upload course texts or PDFs. Verified materials are vectorized into ChromaDB and prioritized during student tutoring.")
    
    col_up, col_list = st.columns([1, 2])
    
    with col_up:
        st.markdown("#### 📤 Upload Material")
        uploaded_file = st.file_uploader("Upload PDF, TXT, or MD", type=["pdf", "txt", "md"])
        if uploaded_file:
            if st.button("🚀 Process & Chunk with AI", type="primary", use_container_width=True):
                with st.spinner("Extracting, enhancing, and generating semantic chunks..."):
                    result = upload_content(uploaded_file, st.session_state["token"])
                    if result:
                        st.success(f"Processed! Created {result.get('chunks_count')} semantic chunks.")
                        st.rerun()
    
    with col_list:
        st.markdown("#### 📋 Material Verification Queue")
        pending_items = get_pending_content(st.session_state["token"])
        
        if pending_items:
            for item in pending_items:
                is_verified = item.get("status") == "verified"
                status_badge = "🟢 Verified" if is_verified else "🟡 Pending Verification"
                
                with st.expander(f"{status_badge} | {item['filename']} ({len(item.get('chunks', []))} chunks) — {str(item.get('created_at', ''))[:10]}"):
                    if is_verified:
                        st.success("This document is verified and active in the RAG vector index.")
                    else:
                        for chunk in item.get("chunks", []):
                            st.markdown(f"**Chunk ID: {chunk['id']}**")
                            new_text = st.text_area("Content", chunk["text"], height=120, key=f"text_{chunk['id']}")
                            topics_str = ", ".join(chunk.get("topics", []))
                            new_topics_str = st.text_input("Topics (comma-separated)", topics_str, key=f"topics_{chunk['id']}")
                            new_topics = [t.strip() for t in new_topics_str.split(",") if t.strip()]
                            
                            if st.button("💾 Save Chunk Changes", key=f"update_{chunk['id']}"):
                                if update_chunk(chunk["id"], {"text": new_text, "topics": new_topics}, st.session_state["token"]):
                                    st.success("Chunk updated!")
                            st.divider()
                        
                        if st.button("✅ Verify & Index Entire Document", key=f"verify_{item['id']}", type="primary", use_container_width=True):
                            with st.spinner("Embedding and storing in vector index..."):
                                if verify_item(item["id"], st.session_state["token"]):
                                    st.success("Document verified and indexed successfully!")
                                    st.rerun()
        else:
            st.info("No documents awaiting verification.")
