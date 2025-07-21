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

# --- Streamlit App ---
st.set_page_config(page_title="Teacher Interface", page_icon=":teacher:")
st.title("Teacher Interface")

# Define the system prompt for the teacher interface
TEACHER_SYSTEM_PROMPT = "You are an expert assistant for a teacher. The user is a teacher reviewing a student's chat history. When asked, provide concise summaries, identify learning gaps, or suggest next steps. Your tone should be professional and analytical. When you receive instructions, confirm you will follow them and then wait for the student to continue the conversation."

# Initialize the model
if "model" not in st.session_state:
    st.session_state.model = genai.GenerativeModel(
        'gemini-2.0-flash',
        system_instruction=TEACHER_SYSTEM_PROMPT
    )

# Load the FULL shared chat history
full_history = load_history()
st.session_state.history = full_history

# Start the chat session with the full history
chat = st.session_state.model.start_chat(history=[ContentDict(msg) for msg in full_history])

# Display the entire, unfiltered history
for message in full_history:
    author = message.get("author", "model") # Default to model for AI responses
    
    if author == "student":
        role_display = "Student"
        avatar = "🧑‍🎓"
    elif author == "teacher":
        role_display = "You (Teacher)"
        avatar = "🧑‍🏫"
    else: # Gemini
        role_display = "Gemini"
        avatar = "🤖"

    with st.chat_message(name=role_display, avatar=avatar):
        st.markdown(message["parts"][0] if isinstance(message["parts"], list) else message["parts"])

# Chat input for the teacher
if prompt := st.chat_input("Instruct the AI or continue the conversation..."):
    # Display teacher's message immediately
    with st.chat_message(name="You (Teacher)", avatar="🧑‍🏫"):
        st.markdown(prompt)

    # Add teacher message to the full history
    st.session_state.history.append({"role": "user", "author": "teacher", "parts": [prompt]})

    try:
        # Send the message to Gemini
        response = chat.send_message(prompt)
        
        # Add Gemini's response to the full history
        st.session_state.history.append({"role": "model", "parts": [response.text]})
        
        # Save the updated full history
        save_history(st.session_state.history)

        # Display Gemini's response
        with st.chat_message(name="Gemini", avatar="🤖"):
            st.markdown(response.text)
        
        scroll_to_bottom()
        st.rerun() # Rerun to display the new messages in the history log correctly

    except Exception as e:
        st.error(f"An error occurred: {e}")
        st.rerun()

# Initial scroll to bottom on page load
scroll_to_bottom()