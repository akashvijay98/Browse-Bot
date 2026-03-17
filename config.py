import os
from dotenv import load_dotenv
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, ".env")

# Load it!
load_dotenv(dotenv_path=env_path)

# Set your active provider here: "gemini", "ollama", or "openai"
ACTIVE_PROVIDER = "gemini" 

MODEL_CONFIGS = {
    "gemini": {
        "model_name": "gemini-2.5-flash",
        "api_key": os.getenv("GOOGLE_API_KEY"),
    },
    "ollama": {
        "model_name": "qwen3.5:9b", # or qwen3.5:9b
        "base_url": "http://localhost:11434",
        "num_ctx": 32768
    }
}

# Twilio Settings
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = "whatsapp:+14155238886"