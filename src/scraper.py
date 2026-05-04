import requests
from bs4 import BeautifulSoup


def scrape_zenn(url: str) -> dict:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "lxml")
    # Zenn article main content
    main = soup.find("main") or soup
    # Remove scripts and nav
    for tag in main.find_all(["script", "style", "nav", "aside"]):
        tag.decompose()
    paragraphs = [
        p.get_text(strip=True) for p in main.find_all(["p", "h1", "h2", "h3", "li"])
    ]
    text = "\n\n".join([p for p in paragraphs if p])
    title_tag = soup.find("meta", attrs={"property": "og:title"})
    title = (
        title_tag["content"] if title_tag else soup.title.string if soup.title else ""
    )
    return {"title": title, "text": text}
