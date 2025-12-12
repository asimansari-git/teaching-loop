import httpx
import streamlit as st
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

def login_user(username, password):
    try:
        response = httpx.post(f"{API_URL}/auth/token", data={"username": username, "password": password})
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Connection error: {e}")
        return None

def register_user(username, password, role):
    try:
        response = httpx.post(
            f"{API_URL}/auth/register", 
            json={"username": username, "password": password, "role": role}
        )
        if response.status_code == 200:
            return True
        return False
    except Exception as e:
        st.error(f"Connection error: {e}")
        return False

def send_chat_message(prompt, subject, token, topics=[]):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/chat/",
            json={"prompt": prompt, "subject": subject, "topics": topics},
            headers=headers,
            timeout=60.0
        )
        if response.status_code == 200:
            return response.json().get("response")
        return None
    except Exception as e:
        st.error(f"Chat error: {e}")
        return None

def get_chat_history(subject, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(
            f"{API_URL}/chat/history",
            params={"subject": subject},
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Fetch error: {e}")
        return []

def get_students(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/reports/students", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching students: {e}")
        return []

def generate_report(student_id, subject, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/reports/generate",
            json={"student_id": student_id, "subject": subject, "content": ""},
            headers=headers,
            timeout=60.0
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error generating report: {e}")
        return None

def get_student_reports(student_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(
            f"{API_URL}/reports/student/{student_id}",
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching reports: {e}")
        return []
