import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

MODEL_NAME = "gemini-2.5-flash"

if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in .env")

if not TAVILY_API_KEY:
    raise ValueError("TAVILY_API_KEY not found in .env")