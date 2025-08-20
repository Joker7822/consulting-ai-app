# Search providers: SerpAPI (if SERPAPI_KEY is set) and a lightweight DuckDuckGo HTML fallback.
from typing import List, Dict, Any
import os

class SerpAPISearchProvider:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("SERPAPI_KEY")
        if not self.api_key:
            raise ValueError("SERPAPI_KEY is required for SerpAPISearchProvider")

    def search(self, q: str, engine: str = "google", num: int = 10) -> Dict[str, Any]:
        import requests
        params = {"api_key": self.api_key, "engine": engine, "q": q, "num": num}
        r = requests.get("https://serpapi.com/search.json", params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        results = []
        for item in (data.get("organic_results") or []):
            results.append({
                "title": item.get("title"),
                "link": item.get("link"),
                "snippet": item.get("snippet"),
                "position": item.get("position")
            })
        ads = []
        for ad in (data.get("ads") or []):
            ads.append({
                "title": ad.get("title"),
                "link": ad.get("link"),
                "displayed_link": ad.get("displayed_link"),
                "snippet": ad.get("snippet"),
            })
        return {"provider":"serpapi","query":q,"results":results,"ads":ads}


class DuckDuckGoProvider:
    '''
    Very lightweight fallback. Uses DuckDuckGo HTML endpoint.
    Note: This is a best-effort HTML parse and may break if DDG changes markup.
    Prefer SerpAPI in production.
    '''
    def __init__(self):
        pass

    def search(self, q: str, num: int = 10) -> Dict[str, Any]:
        import requests, bs4  # needs beautifulsoup4
        url = "https://duckduckgo.com/html/"
        r = requests.post(url, data={"q": q}, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        soup = bs4.BeautifulSoup(r.text, "html.parser")
        results = []
        for a in soup.select(".result__a")[:num]:
            title = a.get_text(strip=True)
            link = a.get("href")
            snippet_el = a.find_parent(class_="result__title").find_next_sibling(class_="result__snippet")
            snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
            results.append({"title": title, "link": link, "snippet": snippet})
        return {"provider":"duckduckgo","query":q,"results":results,"ads":[]}
