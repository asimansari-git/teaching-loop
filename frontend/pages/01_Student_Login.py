import streamlit as st
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import login_user, register_user, get_organizations

st.set_page_config(page_title="Student Login", page_icon="🧑‍🎓")

st.title("Student Login 🧑‍🎓")

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            token_data = login_user(username, password)
            if token_data:
                st.session_state["token"] = token_data["access_token"]
                st.session_state["role"] = "student"
                st.session_state["username"] = username
                st.success("Logged in successfully!")
                st.switch_page("pages/03_Student_Dashboard.py")
            else:
                st.error("Invalid credentials")

with tab2:
    st.subheader("Join your School/Organization")
    organizations = get_organizations()
    org_options = {org["name"]: org["id"] for org in organizations}
    
    if not organizations:
        st.warning("No organizations found. Ask your teacher to create one first.")
    
    with st.form("register_form"):
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        
        selected_org_name = st.selectbox("Select Organization", list(org_options.keys()) if organizations else [])
        
        submit_reg = st.form_submit_button("Register")
        
        if submit_reg:
            if not organizations:
                st.error("Cannot register without an organization.")
            else:
                org_id = org_options[selected_org_name]
                if register_user(new_username, new_password, "student", organization_id=org_id):
                    st.success("Registration successful! Please login.")
                else:
                    st.error("Registration failed.")
