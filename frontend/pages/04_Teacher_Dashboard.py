import streamlit as st
import sys
import os
import pandas as pd

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import get_students, generate_report, get_student_reports, get_student_sessions_for_teacher

st.set_page_config(page_title="Teacher Dashboard", page_icon="🧑‍🏫")

if "token" not in st.session_state or st.session_state.get("role") != "teacher":
    st.warning("Please login as a teacher first.")
    st.stop()

st.title(f"Teacher Dashboard - {st.session_state['username']}")

tab1, tab2 = st.tabs(["Student List", "Reports"])

students = get_students(st.session_state["token"])

with tab1:
    st.subheader("Enrolled Students")
    if students:
        df = pd.DataFrame(students)
        st.dataframe(df[["id", "username", "role"]])
    else:
        st.info("No students found.")

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
