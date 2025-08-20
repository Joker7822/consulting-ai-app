from __future__ import annotations
from typing import Dict, Any
from .config import Benchmark

def apply_weight_patch(industry_weights: Dict[str, Dict[str, float]], industry: str, patch: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    '''
    Return a shallow-copied weights dict with multipliers applied for a given industry.
    Only awareness/consideration/conversion are affected.
    '''
    import copy
    out = copy.deepcopy(industry_weights)
    w = out.get(industry) or out.get("その他") or {}
    if not w: return out
    def clamp(x): return max(0.5, min(1.5, x))
    w["awareness"]    = clamp(w.get("awareness",1.0)    * patch.get("awareness_mult",1.0))
    w["consideration"]= clamp(w.get("consideration",1.0)* patch.get("consideration_mult",1.0))
    w["conversion"]   = clamp(w.get("conversion",1.0)   * patch.get("conversion_mult",1.0))
    out[industry] = w
    return out

def kpi_backsolve_from_benchmark(goal_cv: int, bench: Benchmark) -> Dict[str, int]:
    '''
    Compute imps/clicks/leads from explicit benchmark.
    '''
    import math
    clicks = math.ceil(goal_cv / max(bench.cvr, 1e-6))
    imps   = math.ceil(clicks / max(bench.ctr, 1e-6))
    leads  = math.ceil(clicks * bench.lead_rate)
    return {"必要CV数": goal_cv, "必要クリック数": clicks, "必要インプレッション": imps, "必要リード/開始数": leads}
