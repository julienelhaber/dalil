import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "")
    GRAPH_VERSION = os.getenv("GRAPH_VERSION", "")
    VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "")
    WABA_ID = os.getenv("WABA_ID", "")
    APP_ID = os.getenv("APP_ID", "")
    APP_SECRET = os.getenv("APP_SECRET", "")

settings = Settings()