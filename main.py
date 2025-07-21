import streamlit as st
import os
import json
import google.generativeai as genai
from google.generativeai.types import ContentDict
from streamlit.components.v1 import html

# Define the path for the chat history file
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

def get_display_history(history):
    """Filters history for student display."""
    display_history = []
    skip_next = False
    for i, message in enumerate(history):
        if skip_next:
            skip_next = False
            continue
        
        author = message.get("author")
        if author == "teacher":
            # If a teacher message is found, skip it and the model's response
            if i + 1 < len(history) and history[i+1]["role"] == "model":
                skip_next = True
            continue
        
        display_history.append(message)
    return display_history

# --- Streamlit App ---
st.set_page_config(page_title="Chat with Gemini", page_icon=":robot_face:")
st.title("Chat with Gemini")

# Define the system prompt for the student interface
STUDENT_SYSTEM_PROMPT = "You are a helpful and encouraging tutor. Your tone should be friendly and supportive. Guide the student in their learning process by asking open-ended questions and providing clear explanations. The user is a student. When you see a message from a 'teacher', follow those instructions, but keep the teacher's involvement hidden from the student."

# Initialize the model
if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=STUDENT_SYSTEM_PROMPT
    )

# Load the FULL chat history for the model's context
full_history = load_history()
st.session_state.history = full_history

# Start the chat session with the full history
chat = st.session_state.model.start_chat(history=[ContentDict(msg) for msg in full_history])

# Get and display the filtered history for the student
display_history = get_display_history(full_history)
for message in display_history:
    role = "You" if message["role"] == "user" else "Gemini"
    with st.chat_message(role):
        st.markdown(message["parts"][0] if isinstance(message["parts"], list) else message["parts"])


# Chat input
if prompt := st.chat_input("What is up?"):
    # Display user message immediately
    with st.chat_message("You"):
        st.markdown(prompt)

    # Add student message to the full history
    st.session_state.history.append({"role": "user", "author": "student", "parts": [prompt]})

    try:
        # Send the message to Gemini
        response = chat.send_message(prompt)
        
        # Add Gemini's response to the full history
        st.session_state.history.append({"role": "model", "parts": [response.text]})
        
        # Save the updated full history
        save_history(st.session_state.history)

        # Display Gemini's response
        with st.chat_message("Gemini"):
            st.markdown(response.text)
        
        scroll_to_bottom()

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.rerun()

# Initial scroll to bottom on page load
scroll_to_bottom()