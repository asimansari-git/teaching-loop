import asyncio
import os
from dotenv import load_dotenv
from backend import chat_service, database

load_dotenv()

async def test():
    print("Testing MongoDB Connection...")
    try:
        db = database.get_mongo_db()
        print(f"Connected to: {db.name}")
        # Test Read
        logs = db.chat_logs.find_one()
        print("Read successful.")
    except Exception as e:
        print(f"MongoDB Error: {e}")
        return

    print("\nTesting Gemini API and Write...")
    try:
        response = await chat_service.generate_response(
            username="debug_user",
            prompt="Hello, this is a test.",
            subject="debug"
        )
        print(f"Gemini Response: {response}")
    except Exception as e:
        print(f"Chat Service Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
