import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "roomline.db")
CHROMA_DIR = os.path.join(BASE_DIR, ".chroma")
HOTEL_CONFIG_PATH = os.path.join(BASE_DIR, "hotel_config.json")
