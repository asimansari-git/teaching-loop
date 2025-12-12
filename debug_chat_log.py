import asyncio
import os
import traceback
from dotenv import load_dotenv
from backend import chat_service, database

load_dotenv()

async def test():
    with open("debug_error.log", "w") as f:
        try:
            f.write("Starting Test...\n")
            print("Starting Test...")
            
            # Test DB Read
            db = database.get_mongo_db()
            f.write(f"DB Name: {db.name}\n")
            logs = db.chat_logs.find_one()
            f.write("Read successful.\n")
            
            # Test Chat Gen (Writer)
            f.write("Testing Generation...\n")
            response = await chat_service.generate_response(
                username="debug_user",
                prompt="test",
                subject="general"
            )
            f.write(f"Response: {response}\n")
            
        except Exception as e:
            f.write("ERROR OCCURRED:\n")
            f.write(str(e))
            f.write("\n")
            traceback.print_exc(file=f)

if __name__ == "__main__":
    asyncio.run(test())
