import requests
from bs4 import BeautifulSoup
import re
from collections import Counter

STOPWORDS = set("""
a an the and or but if then else when while for to of in on at by with from as is are was were be been being this that those these it its their your our we you i me my mine ours yours his her hers him them they he she what which who whom whose how why where
""".split())

class EnhancedScraper:
    def __init__(self, timeout: int = 20, user_agent: str = "InternalLinkBot/1.0 (+https://example.com/bot)"):
        self.timeout = timeout
        self.headers = {"User-Agent": user_agent}

    def fetch_html(self, url: str) -> str:
        r = requests.get(url, headers=self.headers, timeout=self.timeout)
        r.raise_for_status()
        return r.text

    def extract_text_and_headings(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["nav","footer","header","script","style","noscript","iframe"]):
            tag.extract()
        headings = []
        for hx in ["h1","h2","h3"]:
            for h in soup.find_all(hx):
                t = h.get_text(separator=" ", strip=True)
                if t:
                    headings.append(t)
        text = soup.get_text(separator=" ", strip=True)
        return text, headings

    def keyword_candidates(self, text: str, top_k: int = 15):
        tokens = re.findall(r"[A-Za-z0-9][A-Za-z0-9\-\s]{1,60}", text)
        words = []
        for t in tokens:
            for w in t.lower().split():
                if w not in STOPWORDS and len(w) > 2:
                    words.append(w)
        freq = Counter(words)
        return [w for w, _ in freq.most_common(top_k)]

    def fetch_page_data(self, url: str):
        try:
            html = self.fetch_html(url)
            text, headings = self.extract_text_and_headings(html)
            keywords = self.keyword_candidates(text, top_k=20)
            return {"text": text, "headings": headings, "keywords": keywords}
        except Exception:
            return {"text": "", "headings": [], "keywords": []}
