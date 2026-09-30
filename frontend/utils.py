import httpx
import streamlit as st
import os
import base64
import json

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

def decode_jwt_payload(token: str) -> dict:
    """Safely decodes claims payload from a JWT token without external cryptography dependencies."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return {}
        payload_b64 = parts[1]
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload_bytes = base64.urlsafe_b64decode(padded)
        return json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return {}

def handle_api_response(response: httpx.Response) -> bool:
    """
    Checks response status. If 401 Unauthorized, notifies user and provides re-login trigger.
    Returns True if valid (not 401), False otherwise.
    """
    if response.status_code == 401:
        st.error("⚠️ Your session has expired. Please sign in again.")
        if st.button("🔑 Go to Login", key=f"relogin_{response.url.path}"):
            logout()
        return False
    return True

def logout():
    """Clears session state and redirects to landing page."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.switch_page("app.py")

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
        if not handle_api_response(response):
            return None
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
        if not handle_api_response(response):
            return []
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
        if not handle_api_response(response):
            return []
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
            timeout=60.0
        )
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json().get("response")
        return None
    except Exception as e:
        st.error(f"Chat error: {e}")
        return None

def get_students(token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/reports/students", headers=headers)
        if not handle_api_response(response):
            return []
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
        if not handle_api_response(response):
            return []
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching student sessions: {e}")
        return []

def generate_report(student_id, session_id, subject, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/reports/generate",
            json={"student_id": student_id, "session_id": session_id, "subject": subject},
            headers=headers,
            timeout=60.0
        )
        if not handle_api_response(response):
            return None
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
        if not handle_api_response(response):
            return []
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
        if not handle_api_response(response):
            return []
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
            json={"name": subject_name, "topics": []},
            headers=headers
        )
        if not handle_api_response(response):
            return None
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
            json={"session_id": session_id, "plan_content": {}},
            headers=headers,
            timeout=30.0
        )
        if not handle_api_response(response):
            return None
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
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json()
        detail = response.json().get("detail", response.text) if response.headers.get("content-type", "").startswith("application/json") else response.text
        st.error(f"Failed to generate quiz ({response.status_code}): {detail}")
        return None
    except Exception as e:
        st.error(f"Error generating quiz: {e}")
        return None

def submit_quiz(quiz_id_or_data, user_answers, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        payload = {"user_answers": user_answers}
        if isinstance(quiz_id_or_data, int) or (isinstance(quiz_id_or_data, str) and str(quiz_id_or_data).isdigit()):
            payload["quiz_id"] = int(quiz_id_or_data)
        elif isinstance(quiz_id_or_data, dict):
            payload["quiz_id"] = quiz_id_or_data.get("db_id") or quiz_id_or_data.get("id")
            payload["quiz_data"] = quiz_id_or_data

        response = httpx.post(
            f"{API_URL}/chat/quiz/submit",
            json=payload,
            headers=headers,
            timeout=30.0
        )
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json()
        detail = response.json().get("detail", response.text) if response.headers.get("content-type", "").startswith("application/json") else response.text
        st.error(f"Failed to submit quiz ({response.status_code}): {detail}")
        return None
    except Exception as e:
        st.error(f"Error submitting quiz: {e}")
        return None

def get_certificate(session_id, subject, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(
            f"{API_URL}/reports/certificate",
            json={"session_id": session_id, "subject": subject, "student_id": 0, "content": ""},
            headers=headers,
            timeout=60.0
        )
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json().get("content")
        elif response.status_code in [400, 403]:
            detail = response.json().get("detail", "Certificate requirements not met.")
            st.warning(f"⚠️ {detail}")
            return None
        return None
    except Exception as e:
        st.error(f"Error getting certificate: {e}")
        return None

def upload_content(file, token):
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (file.name, file, file.type)}
    try:
        response = httpx.post(f"{API_URL}/content/upload", files=files, headers=headers, timeout=120.0)
        if not handle_api_response(response):
            return None
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
        if not handle_api_response(response):
            return []
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
        if not handle_api_response(response):
            return False
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error updating chunk: {e}")
        return False

def verify_item(item_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(f"{API_URL}/content/verify/{item_id}", headers=headers)
        if not handle_api_response(response):
            return False
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error verifying item: {e}")
        return False

def generate_textbook_article(session_id, topic_override, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        payload = {"session_id": session_id}
        if topic_override:
            payload["topic_override"] = topic_override
        response = httpx.post(f"{API_URL}/chat/textbook/generate", json=payload, headers=headers, timeout=60.0)
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error generating textbook article: {e}")
        return None

def get_socratic_hint(session_id, question, article_text, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        payload = {"session_id": session_id, "question": question, "article_text": article_text}
        response = httpx.post(f"{API_URL}/chat/textbook/socratic-hint", json=payload, headers=headers, timeout=60.0)
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error locating socratic hint: {e}")
        return None

def save_highlight(session_id, element_id, quoted_text, question, tag, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        payload = {
            "element_id": element_id,
            "quoted_text": quoted_text,
            "question": question,
            "tag": tag
        }
        response = httpx.post(f"{API_URL}/chat/{session_id}/highlight", json=payload, headers=headers, timeout=30.0)
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error saving highlight: {e}")
        return None

def get_highlights(session_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/chat/{session_id}/highlights", headers=headers, timeout=30.0)
        if not handle_api_response(response):
            return []
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching highlights: {e}")
        return []

def compile_review_sheet(session_id, highlights, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        payload = {"session_id": session_id, "highlights": highlights}
        response = httpx.post(f"{API_URL}/reports/review-sheet", json=payload, headers=headers, timeout=60.0)
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error compiling review sheet: {e}")
        return None

def get_micro_credential(session_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.get(f"{API_URL}/reports/micro-credential/{session_id}", headers=headers, timeout=30.0)
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error fetching micro-credential: {e}")
        return None

def generate_refresher_quiz(session_id, token):
    headers = {"Authorization": f"Bearer {token}"}
    try:
        response = httpx.post(f"{API_URL}/chat/quiz/refresher", json={"session_id": session_id}, headers=headers, timeout=60.0)
        if not handle_api_response(response):
            return None
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        st.error(f"Error generating refresher quiz: {e}")
        return None
