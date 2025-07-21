
import streamlit as st
import os
import google.generativeai as genai
from google.generativeai.types import ContentDict
from streamlit.components.v1 import html
from pymongo import MongoClient, ASCENDING
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

# --- Database Setup ---
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    st.error("MONGO_URI not found in environment variables. Please set it in your .env file.")
    st.stop()

client = MongoClient(MONGO_URI)
db = client.teaching_loop_db
collection = db.chat_history

# Create a timestamp index if it doesn't exist
collection.create_index([("timestamp", ASCENDING)])


# --- Auto-scrolling script ---
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

# Load API key from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure the generative AI model
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("Google API key not found. Please set the GOOGLE_API_KEY environment variable.")
else:
    genai.configure(api_key=api_key)

# --- Chat History Functions ---
def load_history():
    """Loads chat history from MongoDB."""
    return list(collection.find().sort("timestamp", ASCENDING))

def save_message(message):
    """Saves a single message to MongoDB."""
    collection.insert_one(message)

def get_model_history(history):
    """Prepares history for the model, enriching the role."""
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
st.set_page_config(page_title="Teacher Interface", page_icon=":teacher:")
st.title("Teacher Interface")

with st.sidebar:
    st.header("Controls")
    if st.button("Close Application"):
        st.info("You can now close this browser tab.")
        st.stop()

TEACHER_SYSTEM_PROMPT = "You are an expert assistant for a teacher. The user is a teacher reviewing a student's chat history. When asked, provide concise summaries, identify learning gaps, or suggest next steps. Your tone should be professional and analytical. When you receive instructions, confirm you will follow them and then wait for the student to continue the conversation."

if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=TEACHER_SYSTEM_PROMPT
    )

full_history = load_history()
model_history = get_model_history(full_history)
chat = st.session_state.model.start_chat(history=model_history)

for message in full_history:
    author = message.get("author", "model")
    
    if author == "student":
        role_display, avatar = "Student", "🧑‍🎓"
    elif author == "teacher":
        role_display, avatar = "You (Teacher)", "🧑‍🏫"
    else:
        role_display, avatar = "Gemini", "🤖"

    with st.chat_message(name=role_display, avatar=avatar):
        st.markdown(message["parts"][0])

if prompt := st.chat_input("Instruct the AI or continue the conversation..."):
    user_message = {
        "role": "user", 
        "author": "teacher", 
        "parts": [prompt],
        "timestamp": datetime.now(timezone.utc)
    }
    save_message(user_message)

    try:
        response = chat.send_message(prompt)
        
        model_message = {
            "role": "model",
            "parts": [response.text],
            "timestamp": datetime.now(timezone.utc)
        }
        save_message(model_message)
        
        st.rerun()

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.rerun()

scroll_to_bottom()
