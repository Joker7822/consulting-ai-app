from __future__ import annotations
from typing import Dict, Any
import re

from .market_research import MarketResearch
from .adapters import apply_weight_patch, kpi_backsolve_from_benchmark
from . import ai_core

def _extract_target_cv(text: str) -> int:
    m = re.search(r"(\d+)", text or "")
    return int(m.group(1)) if m else 10

def consult(inputs: Dict[str, Any]) -> Dict[str, Any]:
    '''
    Orchestrate: research -> patch weights/kpi -> run ai_core -> return report dict.
    '''
    mr = MarketResearch()

    industry = inputs.get("industry","その他")
    keywords = inputs.get("keywords") or []
    channel  = inputs.get("channel","広告")
    goal     = inputs.get("goal","今週：主要CV 10 件")
    objective= inputs.get("objective","")

    trends = mr.get_trends(keywords)
    weights_patch = mr.trends_to_weight_patch(trends)

    # Patch ai_core.INDUSTRY_WEIGHTS at runtime (non-destructive copy for this run)
    patched_weights = apply_weight_patch(ai_core.INDUSTRY_WEIGHTS, industry, weights_patch)

    # Recompute diagnosis using patched weights (to avoid editing ai_core.py)
    def _diagnose():
        w = patched_weights.get(industry, ai_core.INDUSTRY_WEIGHTS.get("その他"))
        def s(k, d=50):
            try: return max(0, min(100, int(inputs.get(k, d))))
            except: return d
        scores = {
            "Awareness(認知)": round(s("score_awareness",50)*w["awareness"],1),
            "Consideration(検討)": round(s("score_consideration",50)*w["consideration"],1),
            "Conversion(成約)": round(s("score_conversion",50)*w["conversion"],1),
            "Retention(継続)": round(s("score_retention",50)*w["retention"],1),
            "Referral(紹介)": round(s("score_referral",50)*w["referral"],1),
        }
        return {"scores": scores, "bottleneck": min(scores, key=scores.get), "weights_used": w, "weights_patch": weights_patch}

    diagnosis = _diagnose()

    # KPI from benchmarks
    bench = mr.get_benchmarks(industry, channel)
    target_cv = _extract_target_cv(goal + " " + objective)
    kpi = kpi_backsolve_from_benchmark(target_cv, bench)

    # Concrete actions & examples from ai_core
    actions = ai_core.three_horizons_actions(inputs, tone=inputs.get("tone","やさしめ"))
    examples = ai_core.concrete_examples(inputs, tone=inputs.get("tone","やさしめ"))

    # Competitor creative ideas
    serp = mr.get_competitor_snippets(" ".join(keywords or [industry, "サービス", "比較"]))
    ads  = mr.normalize_ads(serp)

    return {
        "research": {
            "trends_provider": mr.trends_name,
            "search_provider": mr.search_name,
            "trends": trends,
            "ads_samples": ads,
            "benchmarks": bench.__dict__,
        },
        "diagnosis": diagnosis,
        "kpi": kpi,
        "actions": actions,
        "examples": examples,
        "inputs": inputs
    }
