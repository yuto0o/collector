import requests
import json

def test_searxng(domain, kw):
    url = "http://searxng:8080/search"
    params = {
        "q": f"site:{domain} {kw}",
        "format": "json"
    }
    print(f"Testing {domain} with '{kw}'...")
    try:
        resp = requests.get(url, params=params, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        print(f"  -> Found {len(results)} results.")
        for r in results[:2]:
            print(f"     - {r.get('title')} ({r.get('url')})")
    except Exception as e:
        print(f"  -> Error: {e}")

if __name__ == "__main__":
    # Test a few tricky domains
    test_searxng("huggingface.co", "Python")
    test_searxng("arxiv.org", "Machine Learning")
    test_searxng("openai.com", "LLM")
