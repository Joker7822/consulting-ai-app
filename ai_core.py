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
GLOSSARY.update({
    "CPA": "1件の成約にかかった広告費。Cost Per Acquisition。",
    "CPC": "1クリックあたりの広告費。Cost Per Click。",
    "CPM": "1000回表示あたりの広告費。Cost Per Mille。",
    "LTV": "顧客が生涯を通じて生み出す粗利の合計。顧客生涯価値。",
    "AARRR": "認知→検討→成約→継続→紹介の成長フレーム。",
})

def explain_terms(text: str, enabled: bool = True) -> str:
    """用語集に載っている専門用語をやさしい日本語で括弧書き補足する。
    enabled=False のときは原文を返す。
    """
    if not enabled or not text:
        return text
    # 長い語から置換して誤爆を減らす
    for term in sorted(GLOSSARY.keys(), key=len, reverse=True):
        meaning = GLOSSARY[term]
        # すでに括弧が付いている場合はスキップ
        pattern = rf"\b{re.escape(term)}(?!（)"
        text = re.sub(pattern, f"{term}（{meaning}）", text)
    return text

def humanize(text: str, tone: str) -> str:
    if tone == "やさしめ": return "😊 " + text
    if tone == "元気に背中押し": return "🔥 " + text + " いけます！"
    return text

def smartify_goal(text: str) -> str:
    if not text: return "今週：主要CV 10 件（CTR1.5%・CVR3%・直帰率<60%）"
    m = re.search(r"(\d+)", text)
    num = m.group(1) if m else "10"
    return f"今週：主要CV {num} 件（測定：GA/広告、基準：CTR1.5%・CVR3%・直帰率<60%）"

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

def three_horizons_actions(inputs: Dict[str, Any], tone: str, with_reason: bool = False) -> Dict[str, List[Any]]:
    product = inputs.get("product","サービス")
    target = inputs.get("target","あなた")
    bottleneck = funnel_diagnosis(inputs)["bottleneck"]
    # タスクと理由のペア
    today_pairs = [
        ("優先度：ボトルネックは **{bottleneck}**。ここに効くタスクから着手。".format(bottleneck=bottleneck),
         "限られた時間/予算で最大の効果を出すため、最も弱い箇所を先に強化します（ボトルネック思考）。"),
        ("LPヒーロー“誰の/何の悩み/どう解決”を1スクリーンで表現",
         "訪問直後に価値が伝わると直帰率が下がり、成約率（CVR）が上がります。"),
        ("広告：否定KW/除外面を10件棚卸し",
         "無駄な表示を減らし、クリック率（CTR）と費用対効果（CPA）を改善します。"),
        ("SNS：保存率を狙う“チェックリスト投稿”を1本",
         "“保存”は後で見返されやすく、再訪や検討の深まりにつながります。"),
    ]
    week_pairs = [
        ("計測棚卸し（UTM/CV）→ {product} 申込まで可視化".format(product=product),
         "どの経路が成果につながったかを見える化し、投資判断を改善します。"),
        ("AB計画：ヒーロー見出し（痛み vs ベネフィット）を7日",
         "意思決定の要は第一印象。見出しの検証でCVRが大きく変わります。"),
        ("CRM：オンボ配信3通（価値→不安解消→締切）",
         "初回体験の質を上げ、離脱を防ぎ、継続/LTVを高めます。"),
    ]
    month_pairs = [
        ("検索：悩みKW×3の比較/HowTo記事→内部リンクでLPへ",
         "“今すぐ客”以外にも“検討層”を拾い、低コストで質の高い流入を作ります。"),
        ("勝ち投稿の量産体制（テンプレ化/UGC許諾）",
         "再現性を作って運用負荷を下げ、安定的に成果を積み上げます。"),
        ("紹介導線：{target}が配りやすい紹介カードと特典".format(target=target),
         "信頼経由の獲得はCVRが高く、広告依存を下げられます（AARRRの“Referral”）。"),
    ]
    def render(lines):
        if with_reason:
            return [humanize(f"{t}｜理由：{r}", tone) for (t,r) in lines]
        else:
            return [humanize(t, tone) for (t,_) in lines]
    return {
        "今日やる": render(today_pairs),
        "今週やる": render(week_pairs),
        "今月やる": render(month_pairs),
    }

def concrete_examples(inputs: Dict[str, Any], tone: str) -> Dict[str, str]:
    product = inputs.get("product","サービス")
    usp = inputs.get("strength","強み")
    target = inputs.get("target","あなた")
    sns = f"【保存版】{target}がやめるべき3つのムダ → {product}で“ラクに”解決｜{usp}"
    ad = f"{product}｜まずは7日お試し。{usp}。申込3分。今なら特典あり。"
    lp = f"{target}の“困った”を7日で解決。{product} — {usp}。まずは無料で体験。"
    dm = f"はじめまして！{product}への関心ありがとうございます。いま困っていることを30秒で教えてください。今日から一歩進める方法を送ります🙌"
    call = f"本日は“壁を1つ特定して次の1手を決める”がゴールです。質問3つ→結論→次の予定で5分で終わります。"
    sns_p = "“保存版”という語を入れると、ユーザーが後で見返したくなり、再訪と検討の深まりに効きます。"
    ad_p = "期限やベネフィットを明示すると迷いを減らし、クリック率（CTR）と成約率（CVR）に効きます。"
    lp_p = "1画面で“誰の/何の悩み/どう解決”を示すと直帰率が下がり、CVRが上がります。"
    dm_p = "双方向の質問を入れると返信率が上がり、関係構築のきっかけになります。"
    call_p = "目的を先に共有すると、会話がブレずに短時間で意思決定できます。"
    return {
        "SNS投稿": humanize(sns, tone),
        "SNSポイント": humanize(sns_p, tone),
        "広告文": humanize(ad, tone),
        "広告ポイント": humanize(ad_p, tone),
        "LPヒーロー": humanize(lp, tone),
        "LPポイント": humanize(lp_p, tone),
        "DMテンプレ": humanize(dm, tone),
        "DMポイント": humanize(dm_p, tone),
        "電話トーク": humanize(call, tone),
        "電話ポイント": humanize(call_p, tone),
    }

def build_utm(url: str, source="instagram", medium="social", campaign="launch", content="post") -> str:
    if not url: return ""
    join = "&" if "?" in url else "?"
    return f"{url}{join}utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}"
