import streamlit as st
import os
import json
import google.generativeai as genai
from streamlit.components.v1 import html
from dotenv import load_dotenv

# --- Initial Setup ---
load_dotenv()

# Configure the generative AI model
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    st.error("GEMINI_API_KEY not found. Please set it in your .env file.")
    st.stop()
genai.configure(api_key=api_key)

# Define the path for the chat history file
CHAT_HISTORY_FILE = "chat_history.json"

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
    """Loads chat history from a JSON file."""
    if os.path.exists(CHAT_HISTORY_FILE):
        with open(CHAT_HISTORY_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_history(history):
    """Saves the entire chat history to a JSON file."""
    with open(CHAT_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

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
st.set_page_config(page_title="Director Interface", page_icon=":detective:")
st.title("Director Interface")

with st.sidebar:
    st.header("Controls")
    if st.button("Close Application"):
        st.info("You can now close this browser tab.")
        st.stop()

# --- Model and History Initialization (on every run for sync) ---
model = genai.GenerativeModel(
    'gemini-2.0-flash',
    system_instruction="You are an AI assistant speaking with a director. The director is observing a conversation you are having with a user. Your job is to follow the director's instructions, provide summaries, and analyze the user's conversation when asked. Your tone should be that of a helpful, professional colleague. When the director gives an instruction, confirm you will follow it and then wait for the primary user to continue the conversation."
)

history = load_history()
chat = model.start_chat(history=get_model_history(history))

# --- Display Chat History ---
for message in history:
    author = message.get("author", "model")
    
    if author == "user":
        role_display, avatar = "User", "🧑‍💻"
    elif author == "director":
        role_display, avatar = "You (Director)", "🕵️"
    else:
        role_display, avatar = "Gemini", "🤖"

    with st.chat_message(name=role_display, avatar=avatar):
        st.markdown(message["parts"][0])

# --- Handle User Input ---
if prompt := st.chat_input("Instruct the AI or continue the conversation..."):
    user_message = {
        "role": "user", 
        "author": "director", 
        "parts": [prompt]
    }
    history.append(user_message)

    try:
        response = chat.send_message(prompt)
        
        model_message = {
            "role": "model",
            "parts": [response.text]
        }
        history.append(model_message)
        
        save_history(history)
        st.rerun()

    except Exception as e:
        st.error(f"An error occurred: {e}")

scroll_to_bottom()