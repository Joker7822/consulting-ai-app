# Trends providers: Pytrends (if available) with a safe Dummy fallback.
from typing import List, Dict, Any

class DummyTrendsProvider:
    '''
    Fallback provider: returns simple synthetic trend signals so the pipeline
    keeps working even without external APIs or libraries installed.
    '''
    def __init__(self):
        pass

    def get_interest(self, keywords: List[str], geo: str = "JP", days: int = 90) -> Dict[str, Any]:
        base = 50
        out = {}
        for i,k in enumerate(keywords or ["マーケティング"]):
            slope = (i+1) * 0.2
            series = [max(0, min(100, int(base + slope*(t - days/2)))) for t in range(days)]
            out[k] = {"series": series, "avg": sum(series)/len(series), "latest": series[-1]}
        return {"provider": "dummy", "geo": geo, "window_days": days, "keywords": keywords, "data": out}


class PytrendsProvider:
    '''
    Google Trends via pytrends. Optional dependency; if pytrends is missing,
    you should fall back to DummyTrendsProvider upstream.
    '''
    def __init__(self, tz: int = 540):
        from pytrends.request import TrendReq  # type: ignore
        self.pytrends = TrendReq(hl="ja-JP", tz=tz)

    def get_interest(self, keywords: List[str], geo: str = "JP", days: int = 90) -> Dict[str, Any]:
        import pandas as pd
        if not keywords:
            keywords = ["マーケティング"]
        self.pytrends.build_payload(keywords, timeframe=f"now {days}-d", geo=geo)
        df = self.pytrends.interest_over_time()
        if df is None or df.empty:
            return {"provider": "pytrends", "geo": geo, "window_days": days, "keywords": keywords, "data": {}}
        out = {}
        for k in keywords:
            series = df[k].fillna(0).astype(int).tolist()
            out[k] = {"series": series, "avg": float(df[k].mean()), "latest": int(df[k].iloc[-1])}
        return {"provider": "pytrends", "geo": geo, "window_days": days, "keywords": keywords, "data": out}
