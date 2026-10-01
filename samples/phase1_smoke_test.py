import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

api_key = os.getenv("GROQ_API_KEY", "")
model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

print("phase1_setup_ok")
print(f"groq_api_key_present={bool(api_key and api_key != 'your_groq_key_here')}")
print(f"model={model}")
