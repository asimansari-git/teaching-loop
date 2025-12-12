import streamlit as st

st.set_page_config(page_title="Teaching Platform", page_icon="🎓")

st.title("Welcome to the Teaching Platform 🎓")

st.markdown("""
This platform helps students evaluate their skills and teachers to monitor progress.

### Get Started
- **Students**: Go to the **Student Login** page to access your learning dashboard.
- **Teachers**: Go to the **Teacher Login** page to view reports and student progress.

### Features
- 🤖 **AI-Powered Evaluation**: Conversational interface to test your knowledge.
- 📊 **Detailed Reports**: Insightful feedback on strengths and weaknesses.
- 📂 **History Tracking**: Access past evaluations anytime.
""")

st.sidebar.success("Select a page above.")
