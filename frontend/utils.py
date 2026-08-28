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

def get_organizations():
    try:
        response = httpx.get(f"{API_URL}/auth/organizations")
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching organizations: {e}")
        return []

def register_user(username, password, role, organization_id=None, new_organization_name=None):
    try:
        data = {
            "username": username, 
            "password": password, 
            "role": role,
            "organization_id": organization_id,
            "new_organization_name": new_organization_name
        }
        response = httpx.post(f"{API_URL}/auth/register", json=data)
        if response.status_code == 200:
            return True
        elif response.status_code == 400:
            st.error(response.json().get("detail", "Registration failed"))
            return False
        return False
    except Exception as e:
        st.error(f"Connection error: {e}")
        return False

def create_chat_session(subject, topics, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/chat/start",
            json={"subject": subject, "topics": topics},
            headers=headers
        )
        if response.status_code == 200:
            return response.json().get("session_id")
        return None
    except Exception as e:
        st.error(f"Error creating session: {e}")
        return None

def get_chat_sessions(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/chat/sessions", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching sessions: {e}")
        return []

def get_session_history_by_id(session_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/chat/{session_id}/history", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching history: {e}")
        return []

def send_chat_message(prompt, session_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/chat/{session_id}",
            json={"prompt": prompt},
            headers=headers,
            timeout=60.0 # Increased timeout for Gemini
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

def get_student_sessions_for_teacher(student_username, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/reports/sessions/{student_username}", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching student sessions: {e}")
        return []

def generate_report(student_id, session_id, subject, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        # Note: subject is passed for report metadata, but analysis is based on session_id
        response = httpx.post(
            f"{API_URL}/reports/generate",
            json={"student_id": student_id, "session_id": session_id, "subject": subject},
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

def get_subjects(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/chat/subjects", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching subjects: {e}")
        return []

def validate_subject(subject_name, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/chat/subjects/validate",
            json={"name": subject_name, "topics": []}, # topics optional initially
            headers=headers
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error validating subject: {e}")
        return None

def create_learning_plan(session_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/chat/learning/plan",
            json={"session_id": session_id, "plan_content": {}}, # content generated by backend
            headers=headers,
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error creating plan: {e}")
        return None

def generate_quiz(session_id, difficulty, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/chat/quiz/generate",
            json={"session_id": str(session_id), "difficulty": difficulty},
            headers=headers,
            timeout=60.0
        )
        if response.status_code == 200:
            return response.json()
        detail = response.json().get("detail", response.text) if response.headers.get("content-type", "").startswith("application/json") else response.text
        st.error(f"Failed to generate quiz ({response.status_code}): {detail}")
        return None
    except Exception as e:
        st.error(f"Error generating quiz: {e}")
        return None

def submit_quiz(quiz_data, user_answers, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/chat/quiz/submit",
            json={"quiz_data": quiz_data, "user_answers": user_answers},
            headers=headers,
            timeout=30.0
        )
        if response.status_code == 200:
            return response.json()
        st.error(f"Failed to submit quiz ({response.status_code}): {response.text}")
        return None
    except Exception as e:
        st.error(f"Error submitting quiz: {e}")
        return None

def get_certificate(session_id, subject, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/reports/certificate",
            json={"session_id": session_id, "subject": subject, "student_id": 0, "content": ""}, # student_id/content ignored
            headers=headers,
            timeout=60.0
        )
        if response.status_code == 200:
            return response.json().get("content")
        elif response.status_code == 400:
            st.warning(response.json().get("detail"))
            return None
        return None
    except Exception as e:
        st.error(f"Error getting certificate: {e}")
        return None

def upload_content(file, token):
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (file.name, file, file.type)}
    try:
        response = httpx.post(f"{API_URL}/content/upload", files=files, headers=headers, timeout=120.0) # Chunking might take time
        if response.status_code == 200:
            return response.json()
        st.error(f"Upload failed: {response.text}")
        return None
    except Exception as e:
        st.error(f"Error uploading content: {e}")
        return None

def get_pending_content(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/content/pending", headers=headers)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching pending content: {e}")
        return []

def update_chunk(chunk_id, updates, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(f"{API_URL}/content/chunk/{chunk_id}", json=updates, headers=headers)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error updating chunk: {e}")
        return False

def verify_item(item_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(f"{API_URL}/content/verify/{item_id}", headers=headers)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error verifying item: {e}")
        return False
