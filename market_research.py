from __future__ import annotations
from typing import List, Dict, Any
import os

from .providers import PytrendsProvider, DummyTrendsProvider, SerpAPISearchProvider, DuckDuckGoProvider
from .config import ResearchConfig, Benchmark, DEFAULT_BENCHMARKS

class MarketResearch:
    def __init__(self, cfg: ResearchConfig | None = None):
        self.cfg = cfg or ResearchConfig()
        # Trends provider (optional dependency)
        try:
            self.trends = PytrendsProvider()
            self.trends_name = "pytrends"
        except Exception:
            self.trends = DummyTrendsProvider()
            self.trends_name = "dummy"
        # Search provider
        serp_key = os.environ.get("SERPAPI_KEY")
        if serp_key:
            self.search = SerpAPISearchProvider(serp_key)
            self.search_name = "serpapi"
        else:
            self.search = DuckDuckGoProvider()
            self.search_name = "duckduckgo"

    # -------- External data ----------
    def get_trends(self, keywords: List[str] | None = None) -> Dict[str, Any]:
        kw = keywords or self.cfg.keywords or []
        return self.trends.get_interest(kw, geo=self.cfg.geo, days=self.cfg.trend_days)

    def get_competitor_snippets(self, query: str, num: int = 10) -> Dict[str, Any]:
        return self.search.search(query, num=num)

    def get_benchmarks(self, industry: str | None = None, channel: str | None = None) -> Benchmark:
        ind = industry or self.cfg.industry
        ch = channel or self.cfg.channel
        raw = DEFAULT_BENCHMARKS.get(ind, {}).get(ch, {})
        return Benchmark(**{**Benchmark().__dict__, **raw})

    # -------- Simple adapters ----------
    @staticmethod
    def trends_to_weight_patch(trends: Dict[str, Any]) -> Dict[str, float]:
        '''
        Convert trend momentum to multipliers for awareness/consideration etc.
        Very conservative: clamp within +-20%.
        '''
        if not trends or "data" not in trends or not trends["data"]:
            return {}
        avgs = [v["avg"] for v in trends["data"].values() if "avg" in v]
        latest = [v["latest"] for v in trends["data"].values() if "latest" in v]
        if not avgs or not latest:
            return {}
        ratio = (sum(latest)/len(latest)) / (sum(avgs)/len(avgs) + 1e-9)
        mult = max(0.8, min(1.2, ratio))
        return {
            "awareness_mult": mult,
            "consideration_mult": (mult*0.9 + 0.1),
            "conversion_mult": (mult*0.85 + 0.15),
            "retention_mult": 1.0,
            "referral_mult": 1.0,
        }

    @staticmethod
    def normalize_ads(serp: Dict[str, Any]) -> list[Dict[str, str]]:
        ads = serp.get("ads") or []
        if ads:
            return ads
        res = serp.get("results") or []
        out = []
        for r in res[:5]:
            out.append({"title": r.get("title",""), "link": r.get("link",""), "snippet": r.get("snippet","")})
        return out
