# ai_core_plus.py
# Web情報を活用して「チャネル別コピー複数案」と「実行計画」を動的生成
# 既存アプリと互換：呼び出される関数や定数を同名で提供

from __future__ import annotations
import re
import html
import time
import random
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from collections import Counter
from urllib.parse import quote_plus, urlparse

# ============ 依存（存在しない場合も落ちないように） ============
try:
    import requests
    from bs4 import BeautifulSoup
    import feedparser
except Exception:
    requests = None
    BeautifulSoup = None
    feedparser = None

# ============ 既存互換の最低限ダミー定義 =============
# （あなたのプロジェクトに既に実装がある場合は、そちらが使われます）
INDUSTRY_WEIGHTS = {
    "美容": {"SNS": 0.4, "検索": 0.2, "広告": 0.3, "メール/LINE": 0.1},
    "飲食": {"SNS": 0.3, "検索": 0.3, "広告": 0.3, "メール/LINE": 0.1},
    "その他": {"SNS": 0.25, "検索": 0.25, "広告": 0.25, "メール/LINE": 0.25},
}
CHANNEL_TIPS = {"SNS": "画像×短文×ハッシュタグ", "検索": "意図一致の見出し", "広告": "ベネフィット先出し", "メール/LINE": "1メッセージ1CTA"}
GLOSSARY = {"CVR": "成約率（コンバージョン率）"}

def humanize(text: str, tone: str = "やさしめ") -> str:
    return text

def smartify_goal(goal: str) -> str:
    return goal.strip()

def funnel_diagnosis(inputs: Dict[str, Any]) -> Dict[str, Any]:
    scores = {
        "Awareness": inputs.get("score_awareness", 50),
        "Acquisition": inputs.get("score_consideration", 50),
        "Activation": inputs.get("score_conversion", 50),
        "Retention": inputs.get("score_retention", 50),
        "Referral": inputs.get("score_referral", 50),
    }
    bottleneck = sorted(scores.items(), key=lambda x: x[1])[0][0]
    return {"scores": scores, "bottleneck": bottleneck}

def kpi_backsolve(inputs: Dict[str, Any]):
    import pandas as pd
    # 簡易モック
    return pd.DataFrame([
        {"KPI": "クリック", "目標": 1000},
        {"KPI": "CVR", "目標": "3%"},
        {"KPI": "売上", "目標": inputs.get("goal", "—")},
    ])

def explain_terms(text: str, enabled: bool = True) -> str:
    return text

def budget_allocation(inputs: Dict[str, Any]):
    import pandas as pd
    w = INDUSTRY_WEIGHTS.get(inputs.get("industry"), INDUSTRY_WEIGHTS["その他"])
    b = max(0, int(inputs.get("budget") or 0))
    rows = [{"チャネル": ch, "推奨配分(円)": int(b * w[ch])} for ch in w]
    return pd.DataFrame(rows)

def three_horizons_actions(inputs: Dict[str, Any], tone: str, with_reason: bool = False):
    return {
        "今日やる": ["広告の否定KW見直し", "LPのCTAをファーストビューに追加"],
        "今週やる": ["FAQ/比較表の整備", "見出しABテストの設計"],
        "今月やる": ["HowTo記事3本の公開", "オンボ配信3通の設計"],
    }

def concrete_examples(inputs: Dict[str, Any], tone: str) -> Dict[str, str]:
    return {
        "SNS投稿": "例）お悩み→効果→CTA の順で短く。",
        "広告文": "例）ベネフィット先出し＋無料体験。",
        "LPヒーロー": "例）誰の/どの悩みを/どう解決 を一文で。",
        "DMテンプレ": "例）気づき→価値→次の一歩。",
        "電話トーク": "例）ヒアリング→仮説提案→日時打鍵。",
        "SNSポイント": "絵文字1〜2個/改行短め/ハッシュタグ2〜3",
        "広告ポイント": "1メッセージ1訴求/数字は1個まで",
        "LPポイント": "社会的証明は折りたたまず上部に",
        "DMポイント": "長文禁止/1スクロールで完結",
        "電話ポイント": "質問は3個まで/次回約束で締め",
    }

def build_utm(base, src, med, camp, cont):
    from urllib.parse import urlencode
    if not base: return ""
    q = {"utm_source": src, "utm_medium": med, "utm_campaign": camp, "utm_content": cont}
    sep = "&" if "?" in base else "?"
    return base + sep + urlencode(q)

def dynamic_advice(inputs: Dict[str, Any], tone: str, variant_seed: Optional[int] = None, emoji_rich: bool = True):
    rng = random.Random(variant_seed)
    acts = three_horizons_actions(inputs, tone)
    head_opts = [
        "まずはここからいきましょう！一番のボトルネックに効きます。",
        "今日サクッと進められる2つ、ピックしました。",
        "ムリなく効かせる次の一手です。"
    ]
    closer_opts = [
        "無理なく“今日できる2つ”から積み上げましょう。",
        "迷ったら、ボトルネックに効く打ち手を最優先で。",
        "成果が出たらテンプレ化して再現性を作りましょう。"
    ]
    return {
        "ヘッダー": rng.choice(head_opts),
        "今日やる": acts.get("今日やる", []),
        "今週やる": acts.get("今週やる", []),
        "今月やる": acts.get("今月やる", []),
        "ひとこと": rng.choice(closer_opts),
    }

# ============ Web収集ユーティリティ ============

DEFAULT_SOURCES = [
    "https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja",
]

def fetch_web_sources(query: str, extra_urls: Optional[List[str]] = None, limit: int = 10, timeout: float = 8.0) -> List[Dict[str, str]]:
    results: List[Dict[str, str]] = []
    if not (requests and feedparser):
        return results
    q = quote_plus(query)
    feeds = [u.format(query=q) for u in DEFAULT_SOURCES]
    try:
        for feed_url in feeds:
            d = feedparser.parse(feed_url)
            for e in d.entries[: limit]:
                url = getattr(e, "link", None)
                if not url: continue
                results.append({
                    "title": getattr(e, "title", "").strip(),
                    "url": url,
                    "source": urlparse(url).netloc,
                    "published": getattr(e, "published", "") or getattr(e, "updated", ""),
                })
    except Exception:
        pass
    for u in (extra_urls or []):
        if u and isinstance(u, str):
            results.append({"title": "", "url": u.strip(), "source": urlparse(u).netloc, "published": ""})
    # de-dup
    uniq, seen = [], set()
    for r in results:
        if r["url"] in seen: continue
        seen.add(r["url"]); uniq.append(r)
    return uniq[:limit]

def scrape_and_clean(url: str, timeout: float = 8.0) -> str:
    if not (requests and BeautifulSoup): 
        return ""
    try:
        res = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        if res.status_code != 200: 
            return ""
        soup = BeautifulSoup(res.text, "html.parser")
        for s in soup(["script","style","noscript","header","footer","form","nav","aside"]):
            s.decompose()
        cand = soup.find("article") or soup.find("main") or soup.find("section") or soup.body
        text = cand.get_text("\n", strip=True) if cand else soup.get_text("\n", strip=True)
        text = html.unescape(text)
        lines = [ln for ln in text.splitlines() if ln and len(ln) > 8]
        return "\n".join(lines[:800])
    except Exception:
        return ""

def extract_keypoints(texts: List[str], top_k: int = 20) -> List[str]:
    tokens: List[str] = []
    for t in texts:
        t = t.replace("\u3000"," ").replace("　"," ")
        t = re.sub(r"[^\wぁ-んァ-ヶ一-龠\- ]+", " ", t)
        words = [w for w in t.split() if len(w) >= 2]
        tokens.extend(words)
    bigrams = [" ".join(tokens[i:i+2]) for i in range(len(tokens)-1)]
    trigrams = [" ".join(tokens[i:i+3]) for i in range(len(tokens)-2)]
    counts = Counter(tokens + bigrams + trigrams)
    stop = set(["こと","ため","よう","する","して","です","ます","これ","それ","ここ","もの","あり","ない"])
    scored = [(k,v) for (k,v) in counts.items() if k not in stop and not re.fullmatch(r"\d+", k)]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [p for (p,_) in scored[: top_k]]

# ============ チャネル別コピー（Web活用・強化版） ============

def _tone(text: str, tone: str) -> str:
    if tone == "ビジネス": 
        return text.replace("！","。").replace("🔥","").replace("✨","").replace("💡","")
    if tone == "ユーモラス":
        return text + " 🤣"
    return text

def web_enabled_channel_copies(product: str, industry: str, keypoints: List[str], web_titles: List[str], tone: str = "カジュアル", n: int = 5) -> Dict[str, List[str]]:
    rng = random.Random("".join(keypoints) + product + industry)
    candidates = [w for w in (keypoints + web_titles) if w]
    if not candidates:
        candidates = [f"{industry} トレンド", f"{product} 口コミ", "無料体験", "導入事例"]
    copies = {
        "SNS/Twitter(X)": [],
        "SNS/Instagram": [],
        "SNS/LinkedIn": [],
        "広告/Google": [],
        "広告/Meta": [],
        "メール/件名": [],
        "メール/本文": [],
        "LP/ヒーロー": [],
    }
    for _ in range(n):
        sample = rng.sample(candidates, min(3, len(candidates)))
        copies["SNS/Twitter(X)"].append(_tone(f"【{product}】注目トピック → " + " / ".join(sample) + "｜詳しくはリンクへ 🔗", tone))
    for _ in range(n):
        sample = rng.sample(candidates, min(4, len(candidates)))
        copies["SNS/Instagram"].append(_tone(f"📸 {product} の推しポイント： " + " ・ ".join(sample) + "｜保存して後で見返す ✨", tone))
    for _ in range(n):
        sample = rng.sample(candidates, min(3, len(candidates)))
        copies["SNS/LinkedIn"].append(_tone(f"{industry}の最新論点：{', '.join(sample)}。{product} が提供できる価値を短く共有します。", tone))
    for _ in range(n):
        sample = rng.sample(candidates, min(2, len(candidates)))
        copies["広告/Google"].append(_tone(f"{product}｜" + "・".join(sample) + "。まずは無料で体験。", tone))
    for _ in range(n):
        sample = rng.sample(candidates, min(2, len(candidates)))
        copies["広告/Meta"].append(_tone(f"{product} を試す理由 → " + " / ".join(sample) + "。申込は30秒 ⏱", tone))
    for _ in range(n):
        sample = rng.sample(candidates, min(3, len(candidates)))
        copies["メール/件名"].append(f"{product}で成果が動いた要因：{', '.join(sample)}")
    for _ in range(n):
        sample = rng.sample(candidates, min(3, len(candidates)))
        copies["メール/本文"].append(_tone(
            f"{product}にご関心ありがとうございます。\n"
            f"今回は「{', '.join(sample)}」の観点から、すぐ使えるヒントを2分でご紹介します。\n"
            f"→ 詳細はリンク先へ。", tone
        ))
    for _ in range(n):
        sample = rng.sample(candidates, min(2, len(candidates)))
        copies["LP/ヒーロー"].append(f"{product} — {industry}のいまに効く。{sample[0] if sample else '今必要な一手'}を最短で体験。")
    return copies

# ============ メイン：Web → コピー生成 ============

def web_research_to_copies(query: str, product: str, industry: str,
                           extra_urls: Optional[List[str]] = None,
                           max_items: int = 10,
                           tone: str = "カジュアル") -> Dict[str, Any]:
    items = fetch_web_sources(query, extra_urls=extra_urls, limit=max_items)
    texts, enriched = [], []
    for it in items:
        txt = scrape_and_clean(it["url"])
        if not txt: 
            continue
        it2 = dict(it); it2["text"] = txt
        enriched.append(it2); texts.append(txt)
    keypoints = extract_keypoints(texts, top_k=20) if texts else []
    web_titles = [s["title"] for s in enriched if s.get("title")]
    copies = web_enabled_channel_copies(product=product, industry=industry, keypoints=keypoints, web_titles=web_titles, tone=tone, n=5)
    return {"sources": enriched, "keypoints": keypoints, "copies": copies}

# ============ 実行計画：Web → Plan（What/How/Action） ============

@dataclass
class ActionItem:
    title: str
    why: str
    steps: List[str]
    kpi: str
    target: str
    resources: List[Dict[str, str]]
    effort: str
    risks: str
    mitigation: str

def _shorten(txt: str, n: int = 120) -> str:
    return (txt[:n] + "…") if len(txt) > n else txt

def web_research_to_plan(query: str, product: str, industry: str,
                         extra_urls: Optional[List[str]] = None,
                         max_items: int = 8,
                         tone: str = "カジュアル") -> Dict[str, Any]:
    try:
        res = web_research_to_copies(query=query, product=product, industry=industry,
                                     extra_urls=extra_urls, max_items=max_items, tone=tone)
    except Exception:
        res = {"sources": [], "keypoints": [], "copies": {}}

    sources = res.get("sources", [])
    keypoints = res.get("keypoints", [])
    focus = keypoints[:6] if keypoints else []
    f1 = focus[0] if len(focus) > 0 else "訴求の明確化"
    f2 = focus[1] if len(focus) > 1 else "第一印象（ヒーロー）改善"
    f3 = focus[2] if len(focus) > 2 else "CTA/摩擦の低減"
    f4 = focus[3] if len(focus) > 3 else "検討素材（FAQ/比較表）の充実"
    f5 = focus[4] if len(focus) > 4 else "ABテスト設計"
    f6 = focus[5] if len(focus) > 5 else "CRM/継続導線"

    why_text = "最新の記事/事例で頻出の論点に基づく優先順位。ボトルネックに直結しやすい順です。"
    srcs = [{"title": _shorten(s.get("title") or s.get("url") or ""), "url": s.get("url")} for s in sources][:5]

    today = [
        ActionItem(
            title=f"LPのヒーローで『誰の/どの悩み/どう解決』を一画面で言い切る（{f2}）",
            why="第一印象の改善はCVRに直結（直帰の改善が見込める）",
            steps=["見出し：痛み→ベネフィットの順で2案", "サブ：社会的証明を1行", "CTA：『無料で試す/30秒で完了』を上部に"],
            kpi="CVR / 直帰率",
            target="CVR +20% / 直帰率 -10pt（7日）",
            resources=srcs, effort="45分 / 0円",
            risks="情報過多で視線が散る", mitigation="1メッセージ1CTAに統一"
        ),
        ActionItem(
            title=f"広告の否定KW/除外面を10件棚卸し（{f3}）",
            why="ムダクリックを減らしCPAを改善",
            steps=["検索語句レポートから不適合語抽出", "除外登録→入札/配信面調整", "CTR・CPC・CVRを日次で確認"],
            kpi="CTR / CPC / CPA",
            target="CTR +10% / CPC -10% / CPA -15%（1週）",
            resources=srcs, effort="30分 / 0円",
            risks="配信量が落ちる", mitigation="一致の拡張/入札調整でボリューム確保"
        ),
    ]

    week = [
        ActionItem(
            title=f"ABテスト計画：見出し/CTA/ファーストビュー（{f5}）",
            why="テスト可能な差分で意思決定を早める",
            steps=["仮説→差分→KPI→停止基準を定義", "見出し2/CTA2/ヒーロー2で2×2比較", "UTMで各案識別→日次ロギング"],
            kpi="CVR / CTR / スクロール率",
            target="勝ち案CVR +15%以上で採用",
            resources=srcs, effort="2〜3時間 / 0〜数千円",
            risks="母数不足で有意差が出ない", mitigation="差分を大きく/期間を7〜14日に延長"
        ),
        ActionItem(
            title=f"検討素材の整備：FAQ×5 & 比較表×1（{f4}）",
            why="不安解消が検討前進のボトルネック",
            steps=["問い合わせ/口コミから質問TOP5→100字回答", "競合2社との比較表（○/△/×）", "関連導線から内部リンク"],
            kpi="資料DL / 滞在時間 / PV/Session",
            target="DL +20% / 滞在 +15%",
            resources=srcs, effort="1.5時間 / 0円",
            risks="比較優位の表現が曖昧", mitigation="価格/サポート/保証など定量項目で差分明示"
        ),
    ]

    month = [
        ActionItem(
            title=f"検索集客：悩み/比較/HowTo記事×3本（{f1}）",
            why="“今すぐ客”以外の検討層を拾い低CPOで流入増",
            steps=["KW3つ選定→検索意図を見出しに写経", "本文は結論先出し＋箇条書き→LPへ内部リンク", "構造化データでリッチ化"],
            kpi="自然検索セッション / 入口CVR",
            target="+30% / +0.3pt（30日）",
            resources=srcs, effort="4〜6時間 / 0円",
            risks="インデックス遅延・重複", mitigation="Fetch as Google/構造化/カニバ確認"
        ),
        ActionItem(
            title=f"CRM：オンボ配信3通（価値→不安解消→締切）（{f6}）",
            why="初回体験の質はLTVに直結、離脱抑制と継続へ",
            steps=["価値提示（成功体験/導入事例）", "不安解消（返金/サポート/手順）", "締切（特典/期限）で1アクションへ誘導"],
            kpi="開封率 / クリック率 / 継続率",
            target="開封 +5pt / クリック +2pt / 継続 +3pt",
            resources=srcs, effort="2時間 / 0円",
            risks="過度な訴求でスパム判定", mitigation="頻度週1〜2/オプト明記"
        ),
    ]

    return {"why": why_text, "sources": srcs, "today": today, "week": week, "month": month}
