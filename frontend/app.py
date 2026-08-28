import streamlit as st

st.set_page_config(page_title="Teaching Platform", page_icon="🎓", layout="wide")

st.title("Welcome to the Teaching Platform 🎓")
st.subheader("Your AI-Powered Personalized Learning & Evaluation System")

st.markdown("""
This platform bridges student self-paced learning with teacher supervision and AI tutoring.

---
### 🚀 Get Started

Choose your portal to continue:
""")

col1, col2 = st.columns(2)

with col1:
    st.info("### 🧑‍🎓 Student Portal")
    st.markdown("""
    - Explore adaptive tutoring sessions tailored to your subjects.
    - Follow AI-generated structured learning paths.
    - Test your knowledge with adaptive multi-level quizzes.
    - Earn verified completion certificates.
    """)
    if st.button("Go to Student Login ➡️", use_container_width=True):
        st.switch_page("pages/01_Student_Login.py")

with col2:
    st.success("### 🧑‍🏫 Teacher Portal")
    st.markdown("""
    - Monitor student learning progress and chat sessions.
    - Intervene in AI tutoring chats with discreet teacher guidance.
    - Generate comprehensive student performance reports.
    - Upload and curate course materials for RAG-enhanced tutoring.
    """)
    if st.button("Go to Teacher Login ➡️", use_container_width=True):
        st.switch_page("pages/02_Teacher_Login.py")

st.markdown("---")
st.caption("🔒 Secure, role-isolated learning platform powered by Google Gemini and ChromaDB.")
