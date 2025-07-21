
import streamlit as st
import os
import json
import google.generativeai as genai
from google.generativeai.types import ContentDict
from streamlit.components.v1 import html

# Define the path for the shared chat history file
CHAT_HISTORY_FILE = "chat_history.json"

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
    """Loads chat history, preserving the author field."""
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(history):
    """Saves chat history, including the author field."""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def get_model_history(history):
    """Strips the 'author' key from the history for the model."""
    model_history = []
    for msg in history:
        if msg["role"] == "user":
            model_msg = {"role": msg["role"], "parts": [msg["author"] + ": "] + msg["parts"]}
        else:
            model_msg = {"role": msg["role"], "parts": msg["parts"]}
        model_history.append(model_msg)
    return model_history

# --- Streamlit App ---
st.set_page_config(page_title="Teacher Interface", page_icon=":teacher:")
st.title("Teacher Interface")

TEACHER_SYSTEM_PROMPT = "You are an expert assistant for a teacher. The user is a teacher reviewing a student's chat history. When asked, provide concise summaries, identify learning gaps, or suggest next steps. Your tone should be professional and analytical. When you receive instructions, confirm you will follow them and then wait for the student to continue the conversation."

if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=TEACHER_SYSTEM_PROMPT
    )

full_history = load_history()
st.session_state.history = full_history

# Start chat with a CLEAN history (no 'author' field)
model_history = get_model_history(full_history)
chat = st.session_state.model.start_chat(history=model_history)

# Display the entire, unfiltered history
for message in full_history:
    author = message.get("author", "model")
    
    if author == "student":
        role_display, avatar = "Student", "🧑‍🎓"
    elif author == "teacher":
        role_display, avatar = "You (Teacher)", "🧑‍🏫"
    else:
        role_display, avatar = "Gemini", "🤖"

    with st.chat_message(name=role_display, avatar=avatar):
        st.markdown(message["parts"][0] if isinstance(message["parts"], list) else message["parts"])

if prompt := st.chat_input("Instruct the AI or continue the conversation..."):
    st.session_state.history.append({"role": "user", "author": "teacher", "parts": [prompt]})

    try:
        response = chat.send_message(prompt)
        st.session_state.history.append({"role": "model", "parts": [response.text]})
        save_history(st.session_state.history)
        st.rerun()

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.rerun()

scroll_to_bottom()
