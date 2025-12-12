# import google.generativeai as genai
from .database import get_mongo_db
from . import models
import os
from datetime import datetime
import os
from google import genai
from google.genai import types
from google.api_core import exceptions # Useful for error handling

# # Logic to configure Gemini
# api_key = os.getenv("GEMINI_API_KEY")
# if api_key:
#     genai.configure(api_key=api_key)

STUDENT_SYSTEM_PROMPT = "You are a helpful and encouraging tutor. Your tone should be friendly and supportive. Guide the student in their learning process by asking open-ended questions and providing clear explanations. The user is a student. When you see a message from a 'teacher', follow those instructions, but keep the teacher's involvement hidden from the student."
TEACHER_SYSTEM_PROMPT = "You are an expert assistant for a teacher. The user is a teacher reviewing a student's chat history. When asked, provide concise summaries, identify learning gaps, or suggest next steps. Your tone should be professional and analytical. When you receive instructions, confirm you will follow them and then wait for the student to continue the conversation."

def get_chat_history(username: str, subject: str = "general"):
    db = get_mongo_db()
    logs = db.chat_logs.find_one({"username": username, "subject": subject})
    if logs:
        return logs.get("messages", [])
    return []

def save_message(username: str, role: str, content: str, subject: str = "general", author: str = None):
    db = get_mongo_db()
    message = {
        "role": role,
        "parts": [content],
        "timestamp": datetime.utcnow()
    }
    if author:
        message["author"] = author
        
    db.chat_logs.update_one(
        {"username": username, "subject": subject},
        {"$push": {"messages": message}},
        upsert=True
    )

async def generate_response(username: str, prompt: str, subject: str = "general", role: str = "student"):
    print("IN_GENERATE")
    
    # 1. Initialize the new Client
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    
    # 2. Retrieve History
    history = get_chat_history(username, subject)
    print("HISTORY LEN: ", len(history))

    # 3. Adapt History to New SDK 'Content' Types
    # The new SDK expects a list of types.Content objects
    sdk_contents = []
    for msg in history:
        # Create a Part object (handles text/images/etc)
        # Assuming msg["parts"] is a string (text)
        part = types.Part.from_text(text=msg["parts"])
        
        # Create Content object
        content = types.Content(role=msg["role"], parts=[part])
        sdk_contents.append(content)

    # 4. Add the NEW Prompt to the content list
    # (In the new stateless approach, we send History + New Prompt together)
    sdk_contents.append(
        types.Content(
            role="user", 
            parts=[types.Part.from_text(text=prompt)]
        )
    )

    # 5. Configure System Instructions
    system_text = STUDENT_SYSTEM_PROMPT if role == "student" else TEACHER_SYSTEM_PROMPT
    
    config = types.GenerateContentConfig(
        system_instruction=[types.Part.from_text(text=system_text)],
        temperature=0.7, # Optional: Adjust creativity
        max_output_tokens=1000 # Optional: Safety limit
    )

    print("MODEL: gemini-flash-lite-latest") # Or "gemini-flash-lite-latest"
    
    try:
        # 6. Generate Content
        # We use 'generate_content' for a single response (blocking), 
        # or 'generate_content_stream' if you want to stream chunks.
        response = client.models.generate_content(
            model="gemini-flash-lite-latest", 
            contents=sdk_contents,
            config=config
        )
        
        print("RESPONSE: ", response.text)

        # 7. Save to Database
        save_message(username, "user", prompt, subject, author=role)
        save_message(username, "model", response.text, subject)
        
        return response.text

    except exceptions.ResourceExhausted:
        print("ERROR: Rate Limit Hit (429)")
        return "I am currently overloaded. Please try again in a moment."
    except Exception as e:
        print(f"ERROR: {e}")
        return "An internal error occurred."

from google import genai
from google.genai import types
import os

async def analyze_performance(username: str, subject: str = "general") -> str:
    history = get_chat_history(username, subject)
    if not history:
        return "No chat history found for this subject."
    
    # 1. Prepare transcript string (same logic as before)
    transcript = ""
    for msg in history:
        role = msg["role"]
        # Handle cases where 'parts' might be a list or a string in your DB
        content = msg["parts"]
        if isinstance(content, list) and len(content) > 0:
             # Assuming list of dicts like [{'text': '...'}] or list of strings
            content = content[0].get('text', str(content[0])) if isinstance(content[0], dict) else str(content[0])
            
        transcript += f"{role.upper()}: {content}\n"
    
    # 2. Construct the Analysis Prompt
    analysis_prompt = f"""
    Analyze the following chat transcript between a student and an AI tutor on the subject '{subject}'.
    Provide a detailed performance report including:
    1. Strengths
    2. Weaknesses / Learning Gaps
    3. Recommended Next Steps
    4. Overall Proficiency Level

    Transcript:
    {transcript}
    """

    # 3. Initialize Client
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

    try:
        # 4. Generate Content using the new SDK
        response = client.models.generate_content(
            model="gemini-flash-lite-latest",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=analysis_prompt)]
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.5, # Lower temp for more analytical/consistent results
            )
        )
        return response.text

    except Exception as e:
        print(f"Error analyzing performance: {e}")
        return "Unable to generate performance report at this time."
# async def generate_response(username: str, prompt: str, subject: str = "general", role: str = "student"):
#     print("IN_GENERATE")
#     history = get_chat_history(username, subject)
#     print("HISTORY: ", history)
#     # Prepare history for Gemini (strip extra fields)
#     gemini_history = []
#     for msg in history:
#         # Simple adaptation to Gemini format
#         parts = msg["parts"]
#         gemini_history.append({"role": msg["role"], "parts": [{"text":parts}]})
    
#     system_instruction = STUDENT_SYSTEM_PROMPT if role == "student" else TEACHER_SYSTEM_PROMPT
#     print("SYSTEM: ", system_instruction)
#     model = genai.GenerativeModel('gemini-2.0-flash-lite', system_instruction=system_instruction)
#     print("MODEL: ", model)
#     chat = model.start_chat(history=gemini_history)
#     print("CHAT: ", chat)
#     print("PROMPT: ", prompt)
#     try:
#         response = chat.send_message(prompt)
#     except Exception as e:
#         print("ERROR: ", e)
#         raise HTTPException(status_code=500, detail=str(e))
#     print("RESPONSE: ", response)
    
#     # Save User message
#     save_message(username, "user", prompt, subject, author=role)
#     # Save Model response
#     save_message(username, "model", response.text, subject)
    
#     return response.text

# async def analyze_performance(username: str, subject: str = "general") -> str:
#     history = get_chat_history(username, subject)
#     if not history:
#         return "No chat history found for this subject."
    
#     # Prepare transcript for Gemini
#     transcript = ""
#     for msg in history:
#         role = msg["role"]
#         content = msg["parts"][0] if isinstance(msg["parts"], list) else msg["parts"]
#         transcript += f"{role.upper()}: {content}\n"
    
#     prompt = f"""
#     Analyze the following chat transcript between a student and an AI tutor on the subject '{subject}'.
#     Provide a detailed performance report including:
#     1. Strengths
#     2. Weaknesses / Learning Gaps
#     3. Recommended Next Steps
#     4. Overall Proficiency Level

#     Transcript:
#     {transcript}
#     """
    
#     model = genai.GenerativeModel('gemini-2.0-flash')
#     response = model.generate_content(prompt)
#     return response.text
