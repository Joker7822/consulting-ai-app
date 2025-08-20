from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class ResearchConfig:
    geo: str = "JP"
    trend_days: int = 90
    industry: str = "その他"
    keywords: Optional[List[str]] = None
    channel: str = "広告"  # 検索/SNS/広告/メール/LINE など

@dataclass
class Benchmark:
    ctr: float = 0.015
    cvr: float = 0.03
    lead_rate: float = 0.30

DEFAULT_BENCHMARKS = {
    "飲食": {"検索":{"ctr":0.02,"cvr":0.025,"lead_rate":0.25}, "広告":{"ctr":0.01,"cvr":0.03,"lead_rate":0.35}},
    "小売/EC": {"検索":{"ctr":0.03,"cvr":0.02,"lead_rate":0.20}, "広告":{"ctr":0.012,"cvr":0.028,"lead_rate":0.30}},
    "B2Bサービス": {"検索":{"ctr":0.015,"cvr":0.02,"lead_rate":0.40}, "広告":{"ctr":0.008,"cvr":0.03,"lead_rate":0.45}},
}
