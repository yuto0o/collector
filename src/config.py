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

    # Target sites for Phase 2 expansion
    TARGET_SITES = [
        {"name": "Zenn", "domain": "zenn.dev", "query": "python"},
        {"name": "Qiita", "domain": "qiita.com", "query": "python"},
        {"name": "DevelopersIO", "domain": "dev.classmethod.jp", "query": "python"},
        {"name": "note", "domain": "note.com", "query": "python 技術"},
        {"name": "Hatena Blog", "domain": "hatena.ne.jp", "query": "python 開発"},
        {"name": "Speaker Deck", "domain": "speakerdeck.com", "query": "python"},
        {"name": "Connpass", "domain": "connpass.com", "query": "python"},
        {"name": "Reddit LocalLLaMA", "domain": "reddit.com/r/LocalLLaMA", "query": ""},
        {"name": "Reddit MachineLearning", "domain": "reddit.com/r/MachineLearning", "query": ""},
        {"name": "Reddit Python", "domain": "reddit.com/r/Python", "query": ""},
        {"name": "Hacker News", "domain": "news.ycombinator.com", "query": "python"},
        {"name": "Stack Overflow Blog", "domain": "stackoverflow.blog", "query": ""},
        {"name": "Hugging Face Blog", "domain": "huggingface.co/blog", "query": ""},
        {"name": "Hugging Face Papers", "domain": "huggingface.co/papers", "query": ""},
        {"name": "arXiv AI", "domain": "arxiv.org/list/cs.AI", "query": ""},
        {"name": "OpenAI Blog", "domain": "openai.com/news", "query": ""},
        {"name": "Anthropic News", "domain": "anthropic.com/news", "query": ""},
        {"name": "Google Research", "domain": "research.google/blog", "query": ""},
        {"name": "Meta AI", "domain": "ai.meta.com/blog", "query": ""},
        {"name": "Microsoft Research", "domain": "microsoft.com/en-us/research/blog", "query": ""},
        {"name": "Towards Data Science", "domain": "towardsdatascience.com", "query": ""},
        {"name": "Medium Programming", "domain": "medium.com/topic/programming", "query": ""},
        {"name": "Substack Tech", "domain": "substack.com", "query": "tag:technology python"},
        {"name": "GitHub Trending", "domain": "github.com/trending/python", "query": ""},
        {"name": "Papers with Code", "domain": "paperswithcode.com", "query": ""},
        {"name": "Kaggle Discussions", "domain": "kaggle.com/discussions", "query": "python"},
        {"name": "Dev.to", "domain": "dev.to", "query": "python"},
        {"name": "LlamaIndex Blog", "domain": "llamaindex.ai/blog", "query": ""},
    ]


cfg = Config()
