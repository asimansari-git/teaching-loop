import streamlit as st
import os
import google.generativeai as genai
from streamlit.components.v1 import html
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timezone
from dotenv import load_dotenv

# --- Initial Setup ---
load_dotenv()

# Configure the generative AI model
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY not found. Please set it in your .env file.")
    st.stop()
genai.configure(api_key=api_key)

# --- Database Setup ---
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    st.error("MONGO_URI not found. Please set it in your .env file.")
    st.stop()

@st.cache_resource
def get_mongo_client():
    return MongoClient(MONGO_URI)

@st.cache_resource
def get_chat_collection():
    client = get_mongo_client()
    db = client.teaching_loop_db
    collection = db.chat_history
    collection.create_index([("timestamp", ASCENDING)])
    return collection

collection = get_chat_collection()

# --- Helper Functions ---
def scroll_to_bottom():
    js = """
    <script>
        function scroll(self) {
            var body = self.parent.document.body;
            var chatContainer = body.querySelector('.main');
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        scroll(window);
    </script>
    """
    html(js, height=0)

def load_history():
    return list(collection.find().sort("timestamp", ASCENDING))

def save_message(message):
    collection.insert_one(message)

def get_display_history(history):
    display_history = []
    skip_next = False
    for i, message in enumerate(history):
        if skip_next:
            skip_next = False
            continue
        author = message.get("author")
        if author == "teacher":
            if i + 1 < len(history) and history[i+1]["role"] == "model":
                skip_next = True
            continue
        display_history.append(message)
    return display_history

def get_model_history(history):
    model_history = []
    for msg in history:
        role = msg["role"]
        if role == "user":
            parts = [f"{msg.get('author', 'user')}: {msg['parts'][0]}"] + msg['parts'][1:]
        else:
            parts = msg['parts']
        model_history.append({"role": role, "parts": parts})
    return model_history

# --- Streamlit App ---
st.set_page_config(page_title="Chat with Gemini", page_icon=":robot_face:")
st.title("Chat with Gemini")

with st.sidebar:
    st.header("Controls")
    if st.button("Close Application"):
        st.info("You can now close this browser tab.")
        st.stop()

# --- Session State Initialization ---
if "history" not in st.session_state:
    st.session_state.history = load_history()

if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction="You are a helpful and encouraging tutor. Your tone should be friendly and supportive. Guide the student in their learning process by asking open-ended questions and providing clear explanations. The user is a student. When you see a message from a 'teacher', follow those instructions, but keep the teacher's involvement hidden from the student."
    )

if "chat" not in st.session_state:
    model_history = get_model_history(st.session_state.history)
    st.session_state.chat = st.session_state.model.start_chat(history=model_history)


# --- Display Chat History ---
display_history = get_display_history(st.session_state.history)
for message in display_history:
    role = "You" if message["role"] == "user" else "Gemini"
    with st.chat_message(role):
        st.markdown(message["parts"][0])

# --- Handle User Input ---
if prompt := st.chat_input("What is up?"):
    with st.chat_message("You"):
        st.markdown(prompt)

    user_message = {
        "role": "user", 
        "author": "student", 
        "parts": [prompt],
        "timestamp": datetime.now(timezone.utc)
    }
    
    try:
        # Use the stateful chat session
        response = st.session_state.chat.send_message(prompt)
        
        model_message = {
            "role": "model",
            "parts": [response.text],
            "timestamp": datetime.now(timezone.utc)
        }
        
        # Save only the new messages
        save_message(user_message)
        save_message(model_message)

        # Update in-memory history
        st.session_state.history.append(user_message)
        st.session_state.history.append(model_message)

        with st.chat_message("Gemini"):
            st.markdown(response.text)
        
        scroll_to_bottom()

    except Exception as e:
        st.error(f"An error occurred: {e}")

scroll_to_bottom()