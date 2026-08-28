import streamlit as st
import sys
import os

# Add parent directory to path to import utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils import login_user, register_user, get_organizations, decode_jwt_payload

st.set_page_config(page_title="Teacher Login", page_icon="🧑‍🏫")

st.title("Teacher Login 🧑‍🏫")

tab1, tab2 = st.tabs(["Login", "Register"])

with tab1:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            token_data = login_user(username, password)
            if token_data:
                token = token_data.get("access_token")
                payload = decode_jwt_payload(token)
                role = payload.get("role")
                if role != "teacher":
                    st.error(f"Access Denied: This account has the role '{role}'. Please use the Student Login page.")
                else:
                    st.session_state["token"] = token
                    st.session_state["role"] = "teacher"
                    st.session_state["username"] = username
                    st.session_state["org_id"] = payload.get("org_id")
                    st.success("Logged in successfully!")
                    st.switch_page("pages/04_Teacher_Dashboard.py")
            else:
                st.error("Invalid credentials")

with tab2:
    mode = st.radio("Organization Mode", ["Join Existing", "Create New"])
    
    organizations = []
    if mode == "Join Existing":
        organizations = get_organizations()
        org_options = {org["name"]: org["id"] for org in organizations}
    
    with st.form("register_form"):
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        
        selected_org_id = None
        new_org_name = None
        
        if mode == "Join Existing":
            if organizations:
                selected_org_name = st.selectbox("Select Organization", list(org_options.keys()))
                selected_org_id = org_options[selected_org_name]
            else:
                 st.write("No organizations found.")
        else:
            new_org_name = st.text_input("Organization Name")

        submit_reg = st.form_submit_button("Register")
        
        if submit_reg:
            success = False
            if mode == "Join Existing":
                if selected_org_id:
                     success = register_user(new_username, new_password, "teacher", organization_id=selected_org_id)
                else:
                    st.error("Please select an organization.")
            else:
                if new_org_name:
                    success = register_user(new_username, new_password, "teacher", new_organization_name=new_org_name)
                else:
                    st.error("Please enter an organization name.")

            if success:
                st.success("Registration successful! Please login.")
            elif submit_reg and not success and (selected_org_id or new_org_name): # Avoid double error if validation failed above
                st.error("Registration failed.")
