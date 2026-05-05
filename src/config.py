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
    LLAMA_MODEL: str = os.getenv("LLAMA_MODEL", "local-model")
    SLACK_BOT_TOKEN: str = os.getenv("SLACK_BOT_TOKEN", "")
    SLACK_CHANNEL_ID: str = os.getenv("SLACK_CHANNEL_ID", "")
    DB_PATH: str = os.getenv("DB_PATH", "./data/collector.db")
    SEARXNG_URL: str = os.getenv("SEARXNG_URL", "http://searxng:8080")
    PARALLELISM: int = int(os.getenv("PARALLELISM", "10"))
    DOMAIN_PARALLEL: int = int(os.getenv("DOMAIN_PARALLEL", "1"))
    MIN_SLEEP: int = int(os.getenv("MIN_SLEEP", "5"))
    MAX_SLEEP: int = int(os.getenv("MAX_SLEEP", "15"))
    LLM_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "120"))

    # Target sites (Simplified domains for better search hits)
    TARGET_SITES = [
        {
            "name": "Zenn", 
            "domain": "zenn.dev", 
            "keywords": ["Python", "LLM", "機械学習"],
            "index_urls": ["https://zenn.dev/topics/ai", "https://zenn.dev/topics/python"]
        },
        {
            "name": "Qiita", 
            "domain": "qiita.com", 
            "keywords": ["Python", "LLM", "機械学習"],
            "index_urls": ["https://qiita.com/tags/python", "https://qiita.com/tags/llm"]
        },
        {
            "name": "DevelopersIO", 
            "domain": "dev.classmethod.jp", 
            "keywords": ["Python", "LLM", "機械学習"],
            "index_urls": ["https://dev.classmethod.jp/"]
        },
        {
            "name": "note", 
            "domain": "note.com", 
            "keywords": ["Python", "LLM", "機械学習"]
        },
        {
            "name": "Hatena Blog", 
            "domain": "hatena.ne.jp", 
            "keywords": ["Python", "LLM", "機械学習"],
            "index_urls": ["https://developer.hatenastaff.com/"]
        },
        {
            "name": "Speaker Deck", 
            "domain": "speakerdeck.com", 
            "keywords": ["Python", "LLM", "機械学習"]
        },
        {
            "name": "Connpass", 
            "domain": "connpass.com", 
            "keywords": ["Python", "LLM", "機械学習"]
        },
        {
            "name": "Hugging Face", 
            "domain": "huggingface.co", 
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://huggingface.co/blog", "https://huggingface.co/papers"]
        },
        {
            "name": "arXiv", 
            "domain": "arxiv.org", 
            "keywords": ["Python LLM", "Machine Learning"],
            "index_urls": ["https://arxiv.org/list/cs.AI/recent", "https://arxiv.org/list/cs.CL/recent"]
        },
        {
            "name": "OpenAI", 
            "domain": "openai.com", 
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://openai.com/news/", "https://openai.com/index/research/"]
        },
        {
            "name": "Anthropic", 
            "domain": "anthropic.com", 
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://www.anthropic.com/news"]
        },
        {
            "name": "Google Research", 
            "domain": "research.google", 
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://research.google/blog/"]
        },
        {
            "name": "Meta AI", 
            "domain": "ai.meta.com", 
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://ai.meta.com/blog/", "https://engineering.fb.com/"]
        },
        {
            "name": "Microsoft Research", 
            "domain": "microsoft.com", 
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://www.microsoft.com/en-us/research/blog/"]
        },
        {
            "name": "Towards Data Science", 
            "domain": "towardsdatascience.com", 
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://towardsdatascience.com/"]
        },
        {
            "name": "LlamaIndex Blog", 
            "domain": "llamaindex.ai", 
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://www.llamaindex.ai/blog"]
        },
        {
            "name": "LangChain Blog",
            "domain": "langchain.dev",
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://blog.langchain.dev/"]
        },
        {
            "name": "Papers with Code",
            "domain": "paperswithcode.com",
            "keywords": ["Python", "LLM", "Machine Learning"],
            "index_urls": ["https://paperswithcode.com/latest"]
        }
    ]

    # Safety: Domain-specific rate limits (min_sleep, max_sleep)
    DOMAIN_RATE_LIMIT = {
        "qiita.com": (5, 10),
        "zenn.dev": (5, 10),
        "others": (10, 15)
    }

    # Global timeout for all requests
    GLOBAL_TIMEOUT = 10
    
    # Recrawl TTL in seconds (3 days)
    RECRAWL_TTL = 86400 * 3

    # Bot contact email
    BOT_EMAIL: str = os.getenv("BOT_EMAIL", "your_email@example.com")

    @property
    def USER_AGENTS(self):
        """Construct User-Agents dynamically from BOT_EMAIL."""
        return [
            f"TechCollectorBot/1.0 (contact: {self.BOT_EMAIL})",
            f"TechCollectorBot/1.1 (contact: {self.BOT_EMAIL})",
            f"TechCollectorBot/1.2 (contact: {self.BOT_EMAIL})"
        ]


cfg = Config()
