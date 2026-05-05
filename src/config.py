import os
import logging
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
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

    # Target sites for Phase 2 expansion (Safe sites only)
    TARGET_SITES = [
        {"name": "Zenn", "domain": "zenn.dev", "keywords": ["Python", "LLM", "機械学習"]},
        {"name": "Qiita", "domain": "qiita.com", "keywords": ["Python", "LLM", "機械学習"]},
        {"name": "DevelopersIO", "domain": "dev.classmethod.jp", "keywords": ["Python", "LLM", "機械学習"]},
        {"name": "note", "domain": "note.com", "keywords": ["Python", "LLM", "機械学習"]},
        {"name": "Hatena Blog", "domain": "hatena.ne.jp", "keywords": ["Python", "LLM", "機械学習"]},
        {"name": "Speaker Deck", "domain": "speakerdeck.com", "keywords": ["Python", "LLM", "機械学習"]},
        {"name": "Connpass", "domain": "connpass.com", "keywords": ["Python", "LLM", "機械学習"]},
        {"name": "Hugging Face Blog", "domain": "huggingface.co/blog", "keywords": ["Python", "LLM", "Machine Learning"]},
        {"name": "Hugging Face Papers", "domain": "huggingface.co/papers", "keywords": [""]},
        {"name": "arXiv AI", "domain": "arxiv.org/list/cs.AI", "keywords": [""]},
        {"name": "OpenAI Blog", "domain": "openai.com/news", "keywords": [""]},
        {"name": "Anthropic News", "domain": "anthropic.com/news", "keywords": [""]},
        {"name": "Google Research", "domain": "research.google/blog", "keywords": [""]},
        {"name": "Meta AI", "domain": "ai.meta.com/blog", "keywords": [""]},
        {"name": "Microsoft Research", "domain": "microsoft.com/en-us/research/blog", "keywords": [""]},
        {"name": "Towards Data Science", "domain": "towardsdatascience.com", "keywords": ["Python", "LLM", "Machine Learning"]},
        {"name": "LlamaIndex Blog", "domain": "llamaindex.ai/blog", "keywords": [""]},
    ]

    # Safety: Domain-specific rate limits (min_sleep, max_sleep)
    DOMAIN_RATE_LIMIT = {
        "qiita.com": (5, 10),
        "zenn.dev": (5, 10),
        "others": (10, 15)
    }

    # User-Agents representing the bot (minor rotation)
    USER_AGENTS = [
        "TechCollectorBot/1.0 (contact: youxiangzhongcun955@gmail.com)",
        "TechCollectorBot/1.1 (contact: youxiangzhongcun955@gmail.com)",
        "TechCollectorBot/1.2 (contact: youxiangzhongcun955@gmail.com)"
    ]

    # Global timeout for all requests
    GLOBAL_TIMEOUT = 10
    
    # Recrawl TTL in seconds (3 days)
    RECRAWL_TTL = 86400 * 3


cfg = Config()
