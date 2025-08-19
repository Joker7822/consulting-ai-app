import re
import math
import random
from typing import List, Dict, Any

import pandas as pd

# =========================
# テンプレ/辞書
# =========================
INDUSTRY_WEIGHTS = {
    "小売/EC":      {"awareness":1.0, "consideration":1.1, "conversion":1.2, "retention":1.0, "referral":0.9},
    "飲食":         {"awareness":1.1, "consideration":1.0, "conversion":1.2, "retention":1.1, "referral":1.0},
    "美容/サロン":  {"awareness":1.0, "consideration":1.1, "conversion":1.2, "retention":1.1, "referral":1.0},
    "教育/スクール":{"awareness":1.0, "consideration":1.2, "conversion":1.0, "retention":1.1, "referral":0.9},
    "B2Bサービス":  {"awareness":0.9, "consideration":1.2, "conversion":1.0, "retention":1.2, "referral":1.0},
    "クリニック/医療":{"awareness":0.9, "consideration":1.1, "conversion":1.2, "retention":1.1, "referral":0.9},
    "不動産":       {"awareness":0.9, "consideration":1.2, "conversion":1.0, "retention":1.0, "referral":0.8},
    "その他":       {"awareness":1.0, "consideration":1.0, "conversion":1.0, "retention":1.0, "referral":1.0},
}

CHANNEL_TIPS = {
    "SNS": ["保存率KPI/連載カルーセル", "プロフィール→LP導線を明示", "UGCの収集と二次活用"],
    "検索": ["悩みKWで記事化", "比較/ランキング型でCV導線", "内部リンク最適化"],
    "広告": ["否定KW/除外面棚卸し", "LPヒーローコピーAB", "計測の二重/未計測を点検"],
    "メール/LINE":["オンボ3通設計", "件名はベネフィット先行", "セグメント配信"],
}

GLOSSARY = {
    "CTR": "広告やリンクの表示回数に対するクリック率。Click Through Rate。",
    "CVR": "クリックから成約に至る割合。Conversion Rate。",
}

# =========================
# 言い回し調整
# =========================
def humanize(text: str, tone: str) -> str:
    if tone == "やさしめ": return "😊 " + text
    if tone == "元気に背中押し": return "🔥 " + text + " いけます！"
    return text

# =========================
# 目標のSMART化
# =========================
def smartify_goal(text: str) -> str:
    if not text: return "今週：主要CV 10 件（CTR1.5%・CVR3%・直帰率<60%）"
    m = re.search(r"(\d+)", text)
    num = m.group(1) if m else "10"
    return f"今週：主要CV {num} 件（測定：GA/広告、基準：CTR1.5%・CVR3%・直帰率<60%）"

# =========================
# ファネル診断（AARRR）
# =========================
def funnel_diagnosis(inputs: Dict[str, Any]) -> Dict[str, Any]:
    w = INDUSTRY_WEIGHTS.get(inputs.get("industry","その他"), INDUSTRY_WEIGHTS["その他"])
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
    return {"scores": scores, "bottleneck": min(scores, key=scores.get)}

# =========================
# KPI逆算（CV→クリック→Imp）
# =========================
def kpi_backsolve(inputs: Dict[str, Any]) -> pd.DataFrame:
    text = (inputs.get("goal") or "") + " " + (inputs.get("objective") or "")
    m = re.search(r"(\d+)", text)
    target_cv = int(m.group(1)) if m else 10
    ctr = 0.015; cvr = 0.03; lead_rate = 0.30
    clicks = math.ceil(target_cv / cvr)
    imps   = math.ceil(clicks / ctr)
    leads  = math.ceil(clicks * lead_rate)
    return pd.DataFrame([
        {"指標":"必要CV数","目標値":target_cv,"メモ":"goalから抽出（未指定は10）"},
        {"指標":"必要クリック数","目標値":clicks,"メモ":f"CVR {int(cvr*100)}%想定"},
        {"指標":"必要インプレッション","目標値":imps,"メモ":f"CTR {int(ctr*100)}%想定"},
        {"指標":"必要リード/開始数","目標値":leads,"メモ":f"開始率 {int(lead_rate*100)}%想定"},
    ])

# =========================
# 予算配分（目的×チャネル）
# =========================
def budget_allocation(inputs: Dict[str, Any]) -> pd.DataFrame:
    budget = max(0, int(inputs.get("budget", 0)))
    channels = inputs.get("channels", ["SNS","検索","広告","メール/LINE"])[:4]
    goal = (inputs.get("goal") or "") + (inputs.get("objective") or "")
    weights = {}
    for ch in channels:
        if ch == "広告": w = 1.5 if any(k in goal for k in ["予約","CV","申込","売上"]) else 1.1
        elif ch == "検索": w = 1.4 if any(k in goal for k in ["資料","比較","検討","検索"]) else 1.1
        elif ch == "SNS": w = 1.2 if any(k in goal for k in ["認知","フォロ","保存","拡散"]) else 1.0
        elif ch == "メール/LINE": w = 1.3 if any(k in goal for k in ["再来店","リピート","継続","LTV"]) else 1.0
        else: w = 1.0
        weights[ch] = w
    total_w = sum(weights.values()) or 1
    rows = []
    for ch in channels:
        amount = round(budget * (weights[ch]/total_w))
        tips = " / ".join(random.sample(CHANNEL_TIPS.get(ch.split("(")[0], ["基本を徹底"]), k=min(2, len(CHANNEL_TIPS.get(ch.split("(")[0], ["基本を徹底"])))))
        rows.append({"チャネル": ch, "推奨配分(円/週)": amount, "戦術ヒント": tips})
    return pd.DataFrame(rows)

# =========================
# 今日/今週/今月アクション
# =========================
def three_horizons_actions(inputs: Dict[str, Any], tone: str) -> Dict[str, List[str]]:
    product = inputs.get("product","サービス")
    target = inputs.get("target","あなた")
    bottleneck = funnel_diagnosis(inputs)["bottleneck"]
    today = [
        humanize(f"優先度：ボトルネックは **{bottleneck}**。ここに効くタスクから着手。", tone),
        humanize("LPヒーロー“誰の/何の悩み/どう解決”を1スクリーンで表現", tone),
        humanize("広告：否定KW/除外面を10件棚卸し", tone),
        humanize("SNS：保存率を狙う“チェックリスト投稿”を1本", tone),
    ]
    this_week = [
        humanize(f"計測棚卸し（UTM/CV）→ {product} 申込まで可視化", tone),
        humanize("AB計画：ヒーロー見出し（痛み vs ベネフィット）を7日", tone),
        humanize("CRM：オンボ配信3通（価値→不安解消→締切）", tone),
    ]
    this_month = [
        humanize("検索：悩みKW×3の比較/HowTo記事→内部リンクでLPへ", tone),
        humanize("勝ち投稿の量産体制（テンプレ化/UGC許諾）", tone),
        humanize(f"紹介導線：{target}が配りやすい紹介カードと特典", tone),
    ]
    return {"今日やる": today, "今週やる": this_week, "今月やる": this_month}

# =========================
# 具体例テンプレ（SNS/広告/LP/DM/電話）
# =========================
def concrete_examples(inputs: Dict[str, Any], tone: str) -> Dict[str, str]:
    product = inputs.get("product","サービス")
    usp = inputs.get("strength","強み")
    target = inputs.get("target","あなた")
    sns = f"【保存版】{target}がやめるべき3つのムダ → {product}で“ラクに”解決｜{usp}"
    ad = f"{product}｜まずは7日お試し。{usp}。申込3分。今なら特典あり。"
    lp = f"{target}の“困った”を7日で解決。{product} — {usp}。まずは無料で体験。"
    dm = f"はじめまして！{product}への関心ありがとうございます。いま困っていることを30秒で教えてください。今日から一歩進める方法を送ります🙌"
    call = f"本日は“壁を1つ特定して次の1手を決める”がゴールです。質問3つ→結論→次の予定で5分で終わります。"
    return {"SNS投稿": humanize(sns, tone), "広告文": humanize(ad, tone), "LPヒーロー": humanize(lp, tone), "DMテンプレ": humanize(dm, tone), "電話トーク": humanize(call, tone)}

# =========================
# UTMビルダー
# =========================
def build_utm(url: str, source="instagram", medium="social", campaign="launch", content="post") -> str:
    if not url: return ""
    join = "&" if "?" in url else "?"
    return f"{url}{join}utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}"
