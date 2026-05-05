import os
import logging
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("collector")


@dataclass
class Config:
    LLAMA_ENDPOINT: str = os.getenv("LLAMA_ENDPOINT", "http://localhost:8080")
    LLAMA_API_KEY: str = os.getenv("LLAMA_API_KEY", "")
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_ID: str = os.getenv("SLACK_CHANNEL_ID", "")
    DB_PATH: str = os.getenv("DB_PATH", "./data/collector.db")
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://searxng:8080")
    PARALLELISM: int = int(os.getenv("PARALLELISM", "10"))
    DOMAIN_PARALLEL: int = int(os.getenv("DOMAIN_PARALLEL", "1"))
    MIN_SLEEP: int = int(os.getenv("MIN_SLEEP", "5"))
    MAX_SLEEP: int = int(os.getenv("MAX_SLEEP", "15"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))


cfg = Config()
