#!/usr/bin/env python3
# Command-line interface for web_consult_ai
import argparse, json
from typing import Any, Dict
from .services import consult

def main():
    p = argparse.ArgumentParser(description="Web-connected consulting assistant")
    p.add_argument("--industry", default="その他")
    p.add_argument("--channel", default="広告")
    p.add_argument("--goal", default="今週：主要CV 10 件")
    p.add_argument("--objective", default="")
    p.add_argument("--keywords", nargs="*", default=[])
    p.add_argument("--scores", nargs=5, type=int, metavar=("AWARE","CONSIDER","CONVERT","RETAIN","REFERRAL"))
    p.add_argument("--tone", default="やさしめ")
    p.add_argument("--out", default="report.json")
    args = p.parse_args()

    inputs: Dict[str, Any] = {
        "industry": args.industry,
        "channel": args.channel,
        "goal": args.goal,
        "objective": args.objective,
        "keywords": args.keywords,
        "tone": args.tone,
    }
    if args.scores:
        a,b,c,d,e = args.scores
        inputs.update({
            "score_awareness": a,
            "score_consideration": b,
            "score_conversion": c,
            "score_retention": d,
            "score_referral": e,
        })
    report = consult(inputs)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
