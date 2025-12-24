import sys
sys.path.insert(0, 'd:\\Apps\\LifeOS')
import asyncio
from tools.calendar_tool import CalendarTool

async def test_calendar():
    print("Initializing CalendarTool...")
    tool = CalendarTool()
    
    print("Attempting to authenticate...")
    success = tool._authenticate()
    
    if success:
        print("✅ Authentication successful!")
        events = await tool.execute("get_upcoming_events", {"days": 1})
        print(f"Result: {events}")
    else:
        print("❌ Authentication FAILED.")
        print(f"Token path: {tool.token_path} (Exists: {tool.token_path.exists()})")
        print(f"Creds path: {tool.credentials_path} (Exists: {tool.credentials_path.exists()})")
        
        # Try to print why
        if tool.token_path.exists():
            try:
                from google.oauth2.credentials import Credentials
                creds = Credentials.from_authorized_user_file(str(tool.token_path), tool.token_path.parent / "credentials.json")
                print(f"Creds valid? {creds.valid}")
                print(f"Creds expired? {creds.expired}")
            except Exception as e:
                print(f"Error loading token: {e}")

if __name__ == "__main__":
    asyncio.run(test_calendar())
