import os
from dotenv import load_dotenv

load_dotenv()

# LiteLLM-style model string: "<provider>/<model name>", e.g. "groq/llama-3.3-70b-versatile"
# The provider prefix is what tells LiteLLM which API to call and which *_API_KEY to read.
LLM_MODEL = os.environ.get("LLM_MODEL", "anthropic/claude-sonnet-5")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "roomline.db")
CHECKPOINT_DB_PATH = os.path.join(BASE_DIR, "checkpoints.db")
CHROMA_DIR = os.path.join(BASE_DIR, ".chroma")
HOTEL_CONFIG_PATH = os.path.join(BASE_DIR, "hotel_config.json")
