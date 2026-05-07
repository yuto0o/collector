import requests
import time
from src.search import fetch_from_index_page
from src.config import cfg

def test_idx(name, url, domain):
    print(f"Testing Index: {name} ({url})...")
    count = fetch_from_index_page(url, domain, limit=5)
    print(f"  -> Discovered: {count}")

if __name__ == "__main__":
    # Test problematic domains from logs
    test_idx("HuggingFace Blog", "https://huggingface.co/blog", "huggingface.co")
    test_idx("OpenAI Index", "https://openai.com/news/", "openai.com")
    test_idx("arXiv Recent", "https://arxiv.org/list/cs.AI/recent", "arxiv.org")
    test_idx("Meta AI Blog", "https://ai.meta.com/blog/", "ai.meta.com")
