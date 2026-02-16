import streamlit as st
import sys
import os
import pandas as pd

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import (
    get_students, generate_report, get_student_reports, get_student_sessions_for_teacher, 
    get_session_history_by_id, send_chat_message, upload_content, get_pending_content, 
    update_chunk, verify_item
)

st.set_page_config(page_title="Teacher Dashboard", page_icon="🧑‍🏫")

if "token" not in st.session_state or st.session_state.get("role") != "teacher":
    st.warning("Please login as a teacher first.")
    st.stop()

st.title(f"Teacher Dashboard - {st.session_state['username']}")

tab1, tab2, tab3, tab4 = st.tabs(["Student List", "Reports", "Intervention", "Content Management"])

students = get_students(st.session_state["token"])

with tab1:
    st.subheader("Enrolled Students")
    if students:
        df = pd.DataFrame(students)
        st.dataframe(df[["id", "username", "role"]])
    else:
        st.info("No students found.")

with tab3:
    st.subheader("Intervention Mode")
    if students:
        selected_student_username_int = st.selectbox("Select Student for Intervention", [s["username"] for s in students])
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
    st.subheader("Content Management (RAG)")
    
    # Upload Section
    st.markdown("### Upload New Material")
    uploaded_file = st.file_uploader("Upload PDF or Text file", type=["pdf", "txt", "md"])
    if uploaded_file:
        if st.button("Process & Upload"):
            with st.spinner("Processing content with AI (this may take a moment)..."):
                result = upload_content(uploaded_file, st.session_state["token"])
                if result:
                    st.success(f"Uploaded! Created {result.get('chunks_count')} chunks.")
                    st.rerun()
    
    st.divider()
    
    # Verification Section
    st.markdown("### Pending Verification")
    pending_items = get_pending_content(st.session_state["token"])
    
    if pending_items:
        for item in pending_items:
            with st.expander(f"{item['filename']} ({len(item['chunks'])} chunks) - {item['created_at']}"):
                
                # Check status
                if item["status"] == "verified":
                    st.success("This item is verified and indexed.")
                    continue

                for chunk in item["chunks"]:
                    st.markdown(f"**Chunk {chunk['id']}**")
                    
                    # Editable Text
                    new_text = st.text_area("Content", chunk["text"], height=150, key=f"text_{chunk['id']}")
                    
                    # Editable Topics
                    # Convert list to string for editing
                    topics_str = ", ".join(chunk["topics"])
                    new_topics_str = st.text_input("Topics (comma separated)", topics_str, key=f"topics_{chunk['id']}")
                    new_topics = [t.strip() for t in new_topics_str.split(",") if t.strip()]
                    
                    # Save Changes Button (Per chunk? Or Bulk? Let's do per chunk for simplicity now)
                    if st.button("Update Chunk", key=f"update_{chunk['id']}"):
                        if update_chunk(chunk["id"], {"text": new_text, "topics": new_topics}, st.session_state["token"]):
                            st.success("Chunk updated!")
                            # Ideally rerun to refresh state, but might close expander. 
                            # Let's verify if state persists.
                        
                    st.divider()
                
                # Verify Whole Item
                if st.button("Verify & Index", key=f"verify_{item['id']}"):
                     with st.spinner("Indexing content into Vector DB..."):
                         if verify_item(item["id"], st.session_state["token"]):
                             st.success("Item verified and indexed successfully!")
                             st.rerun()
    else:
        st.info("No content pending verification.")
