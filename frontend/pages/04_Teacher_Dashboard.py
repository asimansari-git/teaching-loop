import streamlit as st
import sys
import os
import pandas as pd

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import get_students, generate_report, get_student_reports

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
            else:
                st.info("No reports available.")

        with col2:
            st.write("**Generate New Report**")
            subject = st.selectbox("Subject", ["Math", "Science", "History", "General"])
            if st.button("Generate Report"):
                with st.spinner("Analyzing chat history and generating report..."):
                    new_report = generate_report(selected_student["id"], subject, st.session_state["token"])
                    if new_report:
                        st.success("Report generated successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to generate report. Check if chat history exists.")
    else:
        st.warning("No students available to generate reports for.")
