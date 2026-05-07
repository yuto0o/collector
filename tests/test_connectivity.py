import requests
from src.config import cfg, logger

def test_connection(name, url):
    logger.info(f"Testing connection to {name} at {url}")
    try:
        if "search" in url:
             # try search endpoint for searxng
             resp = requests.get(url.rstrip("/") + "/search?q=test&format=json", timeout=5)
        elif "8081" in url or "v1" in url:
             # try common openai compatible endpoints for llm
             base = url.rstrip("/")
             logger.info(f"Checking LLM base {base}")
             try:
                 resp = requests.get(f"{base}/v1/models", timeout=5)
                 if resp.status_code == 200:
                     logger.info(f"LLM /v1/models is OK")
                 else:
                     logger.warning(f"LLM /v1/models returned {resp.status_code}")
                     resp = requests.get(f"{base}/models", timeout=5)
             except Exception as e:
                 logger.warning(f"LLM check failed: {e}")
                 resp = None
        else:
             resp = requests.get(url, timeout=5)
        logger.info(f"Response from {name}: {resp.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to {name}: {e}")
        return False

if __name__ == "__main__":
    test_connection("SearXNG", cfg.SEARXNG_URL)
    test_connection("Scrapling", cfg.SCRAPLING_URL)
    test_connection("LLM", cfg.LLAMA_ENDPOINT)
