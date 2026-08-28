import streamlit as st

st.set_page_config(page_title="Teaching Platform", page_icon="🎓", layout="wide")

st.markdown("""
# 🎓 **Teaching Platform**
### *Adaptive AI Tutoring, Educator Supervision & Precision Evaluation*
---
""")

col_hero1, col_hero2 = st.columns([1, 1], gap="large")

with col_hero1:
    st.info("### 🧑‍🎓 **Student Learning Portal**")
    st.markdown("""
    Experience a truly personalized learning journey:
    * 💬 **Interactive AI Tutor** with dynamic explanations and subject deep-dives
    * 🗺️ **Personalized Curriculums** generated on-the-fly for any topic
    * 📝 **Adaptive Multi-Level Quizzes** (Easy 🟢 → Mid 🟡 → Hard 🔴)
    * 📜 **Verified Mastery Certificates** awarded upon completing advanced levels
    * 📊 **Transparent Feedback Reports** from your educators
    """)
    if st.button("🚀 Enter Student Portal", type="primary", use_container_width=True):
        st.switch_page("pages/01_Student_Login.py")

with col_hero2:
    st.success("### 🧑‍🏫 **Teacher Command Center**")
    st.markdown("""
    Empower your teaching with AI-augmented intelligence:
    * 👥 **Classroom Monitoring** for all enrolled students in your organization
    * 🕵️ **Live Discreet Intervention** to inject pedagogical instructions unseen by students
    * ⚡ **Comprehensive Performance Analytics** analyzing transcripts and quiz metrics
    * 📚 **RAG Knowledge Base Curation** to vectorize course textbooks and PDFs into ChromaDB
    """)
    if st.button("🔐 Enter Teacher Portal", type="secondary", use_container_width=True):
        st.switch_page("pages/02_Teacher_Login.py")

st.divider()

# --- Platform Highlights Grid ---
st.markdown("### 🌟 **Key Platform Capabilities**")
col_a, col_b, col_c = st.columns(3)

with col_a:
    st.markdown("""
    #### 🧠 **Adaptive AI Tutor**
    Context-aware dialogue grounded in structured learning paths and verified course materials.
    """)

with col_b:
    st.markdown("""
    #### 🛡️ **Discreet Supervision**
    Teachers guide AI behavior in real-time without interrupting student focus or flow.
    """)

with col_c:
    st.markdown("""
    #### 📚 **Verified RAG Knowledge**
    Semantic vector retrieval ensures factual consistency using your uploaded lecture PDFs.
    """)

st.caption("🔒 Multi-tenant architecture with JWT claim verification, SQLite/PostgreSQL, and Google Gemini.")
