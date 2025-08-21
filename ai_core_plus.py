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

# ===============
# 親しみやすい動的アドバイス
# ===============
def dynamic_advice(inputs: Dict[str, Any], tone: str, variant_seed: int | None = None, emoji_rich: bool = True) -> Dict[str, list[str]]:
    """ユーザーの入力・ボトルネック・予算・業種から、親しみやすい提案を動的生成。
    variant_seed が同じなら同じ提案、変えると表現をリフレッシュ。
    """
    rnd = random.Random(variant_seed)
    product = inputs.get("product","サービス")
    target = inputs.get("target","あなた")
    industry = inputs.get("industry","その他")
    budget = int(inputs.get("budget", 0) or 0)
    diag = funnel_diagnosis(inputs)
    bottleneck = diag["bottleneck"]
    
    # 絵文字セット
    emos = ["✨","💡","👍","🙌","🎯","🧪","🚀","🛠️","📈","📝"]
    def e(): return (rnd.choice(emos) + " ") if emoji_rich else ""
    
    # 口調テンプレ（親しみやすさ）
    openers = [
        f"{e()}まずはここからいきましょう！",
        f"{e()}ムリなく効かせる次の一手です。",
        f"{e()}今日サクッとやれるやつ、ピックしました。",
    ]
    because = [
        "一番のボトルネックに効くからです。",
        "コスパよく成果につながりやすいからです。",
        "迷いなく手を動かせる具体度だからです。",
    ]
    
    # ボトルネック別の推しタスク候補
    bn_map = {
        "Awareness(認知)": [
            (f"SNS固定投稿を“{product}は誰の何の悩みをどう解決？”に差し替え",
             "プロフィール→LP への導線も一緒に見直すと効果が上がります。"),
            ("検索の“悩みワード”を3つ選んで見出し案を出す",
             "『比較』『やり方』『失敗』などの語を入れるとクリックされやすいです。"),
        ],
        "Consideration(検討)": [
            ("LPのヒーロー見出しを「痛み→ベネフィット」の順でAB案を作成",
             "見出しは第一印象。数値が動きやすいです。"),
            (f"よくある質問を5つに絞って、{product}の回答を短く明文化",
             "不安を先回りで解消すると検討が前に進みます。"),
        ],
        "Conversion(成約)": [
            ("申込ボタンの文言を『無料で試す/30秒で完了』系に変更",
             "摩擦を下げるとCVRが上がります。"),
            ("フォームの必須項目を見直して1つ減らす",
             "入力負荷を下げると離脱が減ります。"),
        ],
        "Retention(継続)": [
            ("オンボ配信（価値→不安解消→締切）の3通をテンプレで用意",
             "初回体験の質がLTVに直結します。"),
            (f"『使いこなしチェックリスト』を作り、{target}に送付",
             "“できた感”が継続の原動力です。"),
        ],
        "Referral(紹介)": [
            ("紹介カードをCanvaで作成（友だち特典＋締切）",
             "紹介は信頼経由。CVRが高い獲得チャネルです。"),
            (f"導入事例を1件まとめ、{target}がシェアしやすい要約を作成",
             "“人は人で動く”。事例は最強の検討材料です。"),
        ],
    }
    # 予算帯別の一言
    if budget < 30000:
        budget_tip = "少額なので“無料〜低単価”の打ち手（検索記事/UGC/既存客DM）を厚めに。"
    elif budget < 100000:
        budget_tip = "中予算。広告は狭く深く、勝ちLP/勝ち訴求に集中投下しましょう。"
    else:
        budget_tip = "十分な予算。広告×CRMの両輪で、認知→検討→成約を繋げ切る設計が◎。"
    
    # 候補からランダムにピック
    picks = bn_map.get(bottleneck, bn_map["Consideration(検討)"])
    today = []
    head = random.choice(openers) + " " + random.choice(because)
    for (task, tip) in random.sample(picks, k=min(2, len(picks))):
        line = f"{task}｜理由：{tip}"
        today.append(humanize(f"{e()}{line}", tone))
    
    # 今週・今月の提案（軽めのロードマップ）
    week = [
        humanize(f"{e()}KPIの見える化：UTMで流入→申込まで計測できるか点検", tone),
        humanize(f"{e()}ABテスト計画：見出し・CTA・ファーストビューの3点を1週回す", tone),
    ]
    month = [
        humanize(f"{e()}検索記事3本（悩み/比較/HowTo）→内部リンクでLPに誘導", tone),
        humanize(f"{e()}勝ち投稿のテンプレ化→週2本の定常運用に落とし込む", tone),
    ]
    
    # 仕上げの一言
    closer = humanize(f"{e()}{budget_tip}", tone)
    
    # 用語のやさしい補足（最後にまとめて）
    today = [explain_terms(t, True) for t in today]
    week  = [explain_terms(t, True) for t in week]
    month = [explain_terms(t, True) for t in month]
    closer = explain_terms(closer, True)
    
    return {
        "ヘッダー": head,
        "今日やる": today,
        "今週やる": week,
        "今月やる": month,
        "ひとこと": closer,
    }

def build_utm(url: str, source="instagram", medium="social", campaign="launch", content="post") -> str:
    if not url: return ""
    join = "&" if "?" in url else "?"
    return f"{url}{join}utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}"
    # ========= ここから追記（ai_core_plus.py の末尾に貼り付け） =========
import time
import html
from collections import Counter
from urllib.parse import quote_plus, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
    import feedparser
except Exception:
    # 環境に無い場合でもアプリが落ちないように（UIで警告表示する）
    requests = None
    BeautifulSoup = None
    feedparser = None

# ---- Web収集：RSS候補の生成 ----
DEFAULT_SOURCES = [
    # 業界横断の最新ネタ（ニュース/トレンド）
    "https://news.google.com/rss/search?q={query}&hl=ja&gl=JP&ceid=JP:ja",
    # 追加のRSSをここに増やせます
]

def fetch_web_sources(query: str, extra_urls: list[str] | None = None, limit: int = 10, timeout: float = 8.0) -> list[dict]:
    """
    Web上のRSSや追加URLから候補記事のメタ情報を集める。
    返り値: [{"title":..., "url":..., "source":..., "published": ...}, ...]
    """
    results = []
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

    # 追加URL（ユーザー直指定）
    for u in (extra_urls or []):
        if u and isinstance(u, str):
            results.append({
                "title": "",
                "url": u.strip(),
                "source": urlparse(u).netloc,
                "published": "",
            })

    # 重複除去
    seen = set()
    uniq = []
    for r in results:
        if r["url"] in seen: continue
        seen.add(r["url"])
        uniq.append(r)
    return uniq[:limit]

# ---- 本文抽出＆クレンジング ----
def scrape_and_clean(url: str, timeout: float = 8.0) -> str:
    if not (requests and BeautifulSoup): 
        return ""
    try:
        res = requests.get(url, timeout=timeout, headers={"User-Agent":"Mozilla/5.0"})
        if res.status_code != 200: 
            return ""
        html_text = res.text
        soup = BeautifulSoup(html_text, "html.parser")

        # 余計な要素をドロップ
        for s in soup(["script","style","noscript","header","footer","form","nav","aside"]):
            s.decompose()

        # 記事本文っぽい要素を優先（article / main / section）
        candidate = soup.find("article") or soup.find("main") or soup.find("section") or soup.body
        text = candidate.get_text(separator="\n", strip=True) if candidate else soup.get_text("\n", strip=True)
        text = html.unescape(text)
        # ノイズ簡易除去
        lines = [ln for ln in text.splitlines() if ln and len(ln) > 8]
        text = "\n".join(lines[:800])  # 長すぎ防止
        return text
    except Exception:
        return ""

# ---- キーフレーズ抽出（低コスト） ----
def extract_keypoints(texts: list[str], top_k: int = 20) -> list[str]:
    """
    ざっくり頻出フレーズを抽出（bigram/trigram + 名詞らしき語）
    依存少なめ・ロバスト性重視
    """
    tokens = []
    for t in texts:
        t = t.replace("\u3000"," ").replace("　"," ")
        # シンプルに記号類を空白化
        t = re.sub(r"[^\wぁ-んァ-ヶ一-龠\- ]+", " ", t)
        words = [w for w in t.split() if len(w) >= 2]
        tokens.extend(words)

    # bigram, trigram
    bigrams = [" ".join(tokens[i:i+2]) for i in range(len(tokens)-1)]
    trigrams = [" ".join(tokens[i:i+3]) for i in range(len(tokens)-2)]
    counts = Counter(tokens + bigrams + trigrams)

    # ストップワード簡易
    stop = set(["こと","ため","よう","する","して","です","ます","これ","それ","ここ","もの","あり","ない"])
    scored = [(k,v) for (k,v) in counts.items() if k not in stop and not re.fullmatch(r"\d+", k)]
    scored.sort(key=lambda x: x[1], reverse=True)
    phrases = [p for (p,_) in scored[: top_k]]
    return phrases

# ---- チャネル別コピー生成（複数案） ----
def compose_channel_copies(product: str, industry: str, keypoints: list[str], tone: str = "カジュアル", n: int = 5) -> dict:
    """
    keypoints を元に、SNS/広告/メール/LPでそのまま使えるコピーを複数案生成
    """
    def T(s: str) -> str:
        if tone == "ビジネス":
            s = s.replace("！","。").replace("🔥","").replace("✨","").replace("💡","")
        elif tone == "ユーモラス":
            s = s + " 🤣"
        return s

    def pick(k: int) -> list[str]:
        # キーフレーズから多様性重視で拝借
        base = keypoints[: max(8, k*3)]
        rng = random.Random(len(" ".join(keypoints)))
        outs = []
        for i in range(k):
            pts = rng.sample(base, min(3, len(base))) if base else []
            outs.append(pts)
        return outs

    outs = {
        "SNS/Twitter(X)": [],
        "SNS/Instagram": [],
        "SNS/LinkedIn": [],
        "広告/Google": [],
        "広告/Meta": [],
        "メール/件名": [],
        "メール/本文": [],
        "LP/ヒーロー": [],
    }

    # SNS
    for pts in pick(n):
        outs["SNS/Twitter(X)"].append(T(f"【{product}】いま話題のポイント → " + " / ".join(pts) + "｜詳しくはリンクへ 🔗"))
    for pts in pick(n):
        outs["SNS/Instagram"].append(T(f"📸 {product} の推しどころ → " + "・".join(pts) + "｜保存して後で見返すのが吉 ✨"))
    for pts in pick(n):
        outs["SNS/LinkedIn"].append(T(f"{industry}の最新トレンドから抽出：{', '.join(pts)}。{product} がどう効くかを短く共有します。"))

    # 広告
    for pts in pick(n):
        outs["広告/Google"].append(T(f"{product}｜" + "・".join(pts) + "。まずは無料で体験。"))
    for pts in pick(n):
        outs["広告/Meta"].append(T(f"{product} を試す理由 → " + " / ".join(pts) + "。申込は30秒 ⏱"))

    # メール
    for pts in pick(n):
        outs["メール/件名"].append(f"{product}で成果が動いた要因：{', '.join(pts)}")
    for pts in pick(n):
        outs["メール/本文"].append(T(
            f"{product}にご関心ありがとうございます。\n"
            f"今回は「{', '.join(pts)}」の観点から、すぐ使えるヒントを2分でご紹介します。\n"
            f"→ 詳細はリンク先へ。"
        ))

    # LP
    for pts in pick(n):
        outs["LP/ヒーロー"].append(
            f"{product} — {industry}の今に効く。{pts[0] if pts else 'いま必要な一手'}を、最短で体験。"
        )
    return outs

# ---- メイン：Web収集→生成をまとめて呼び出す ----
def web_research_to_copies(query: str, product: str, industry: str,
                           extra_urls: list[str] | None = None,
                           max_items: int = 10,
                           tone: str = "カジュアル") -> dict:
    """
    1) ソース収集 2) 本文抽出 3) キーフレーズ抽出 4) チャネル別コピー生成
    返り値: {"sources":[{title,url,source,published,text}], "keypoints":[...], "copies":{...}}
    """
    items = fetch_web_sources(query, extra_urls=extra_urls, limit=max_items)
    texts = []
    enriched = []
    for it in items:
        txt = scrape_and_clean(it["url"])
        if not txt: 
            continue
        it2 = dict(it)
        it2["text"] = txt
        enriched.append(it2)
        texts.append(txt)
        # 軽量なので早戻りは不要

    keypoints = extract_keypoints(texts, top_k=20) if texts else []
    copies = compose_channel_copies(product=product, industry=industry, keypoints=keypoints, tone=tone, n=5)
    return {"sources": enriched, "keypoints": keypoints, "copies": copies}
# ========= 追記ここまで =========
# ========= Web→実行計画 生成ユーティリティ =========
from dataclasses import dataclass

@dataclass
class ActionItem:
    title: str
    why: str
    steps: list
    kpi: str
    target: str
    resources: list  # [{"title":..., "url":...}]
    effort: str      # 例: "30分 / 0円"
    risks: str
    mitigation: str

def _shorten(txt: str, n: int = 120) -> str:
    return (txt[:n] + "…") if len(txt) > n else txt

def web_research_to_plan(query: str, product: str, industry: str,
                         extra_urls: list[str] | None = None,
                         max_items: int = 8,
                         tone: str = "カジュアル") -> dict:
    """
    Webから情報収集→キーポイント抽出(web_research_to_copies を再利用)
    → '今日/今週/今月' の実行計画オブジェクトに落とす
    """
    # 既存の収集器を使う（未実装の環境でも例外で落ちないようガード）
    try:
        res = web_research_to_copies(
            query=query, product=product, industry=industry,
            extra_urls=extra_urls, max_items=max_items, tone=tone
        )
    except Exception:
        res = {"sources": [], "keypoints": [], "copies": {}}

    sources = res.get("sources", [])
    keypoints = res.get("keypoints", [])

    # 1) “何をやるか”を言い切る（keypointsを用途別に割付）
    focus = keypoints[:6] if keypoints else []
    f1 = focus[0] if len(focus) > 0 else "訴求の明確化"
    f2 = focus[1] if len(focus) > 1 else "第一印象（ヒーロー）改善"
    f3 = focus[2] if len(focus) > 2 else "CTA/摩擦の低減"
    f4 = focus[3] if len(focus) > 3 else "検討素材（FAQ/比較表）の充実"
    f5 = focus[4] if len(focus) > 4 else "ABテスト設計"
    f6 = focus[5] if len(focus) > 5 else "CRM/継続導線"

    # 2) 情報源→要点の“なぜ（WHY）”
    why_text = "最新の記事/事例で頻出の論点に基づく優先順位。ボトルネックに直結しやすい順に並べています。"
    srcs = [{"title": _shorten(s.get("title") or s.get("url") or ""), "url": s.get("url")} for s in sources][:5]

    # 3) アクション（今日/今週/今月）
    today = [
        ActionItem(
            title=f"LPのヒーローで『誰の/どの悩み/どう解決』を一画面で言い切る（{f2}）",
            why="第一印象の改善はCVRに直結（直帰率の改善が見込める）。",
            steps=[
                "ヒーロー見出し：痛み→ベネフィットの順で2案作成",
                "サブ：社会的証明（レビュー・導入実績）をひとこと追加",
                "CTA：『無料で試す/30秒で完了』系を配置（ファーストビュー内）",
            ],
            kpi="CVR（成約率）/ 直帰率",
            target="CVR +20% / 直帰率 -10pt（7日で観測）",
            resources=srcs,
            effort="45分 / 0円",
            risks="ヒーローに情報過多で視線が散る",
            mitigation="文字量を抑えて1メッセージ1CTAに統一"
        ),
        ActionItem(
            title=f"広告の否定KW/除外面を10件棚卸し（{f3}）",
            why="ムダクリックを減らしCPAを改善。クリック品質を先に上げる。",
            steps=[
                "検索語句レポートを出力→不適合語を抽出",
                "除外リストに登録→入札調整/配信面の見直し",
                "CTR・CPCの変化とCVRを1日単位で確認",
            ],
            kpi="CTR / CPC / CPA",
            target="CTR +10% / CPC -10% / CPA -15%（1週で評価）",
            resources=srcs,
            effort="30分 / 0円",
            risks="配信量が落ちる",
            mitigation="完全一致の拡張/入札調整でボリュームを確保"
        ),
    ]

    week = [
        ActionItem(
            title=f"ABテスト計画：見出し/CTA/ファーストビュー（{f5}）",
            why="テスト可能な差分で意思決定を早めるため。",
            steps=[
                "仮説→差分→評価指標→停止基準を1枚に定義",
                "見出し2案・CTA2案・ヒーロー画像2案で2×2比較",
                "UTMで各案を識別→日次で指標をロギング",
            ],
            kpi="CVR / CTR / スクロール率",
            target="勝ち案CVR +15%以上で採用",
            resources=srcs,
            effort="2〜3時間 / 0〜数千円",
            risks="母数不足で有意差が出ない",
            mitigation="大きめ差分→期間を7〜14日に延長"
        ),
        ActionItem(
            title=f"検討素材の整備：FAQ×5 & 比較表×1（{f4}）",
            why="不安解消が検討前進のボトルネックになりやすいため。",
            steps=[
                "問合せ/口コミから質問TOP5を抽出→100文字以内で回答",
                "競合2社との比較表（○/△/×）を作成",
                "内部リンク：関連導線からFAQ/比較へ誘導",
            ],
            kpi="資料DL/滞在時間/セッションあたりPV",
            target="資料DL +20% / 滞在 +15%",
            resources=srcs,
            effort="1.5時間 / 0円",
            risks="“比較優位”の表現が曖昧",
            mitigation="定量項目（価格/サポート/保証）で差分を明示"
        ),
    ]

    month = [
        ActionItem(
            title=f"検索集客：悩み/比較/HowTo記事×3本（{f1}）",
            why="“今すぐ客”だけでなく検討層を拾って低CPOで流入を増やす。",
            steps=[
                "キーワードを3つ選定→検索意図を見出しに写経",
                "本文は結論先出し+箇条書き→LPへ内部リンク",
                "リッチスニペット（FAQ/HowTo）をマークアップ",
            ],
            kpi="自然検索セッション / 入口CVR",
            target="+30% / 入口CVR +0.3pt（30日）",
            resources=srcs,
            effort="4〜6時間 / 0円",
            risks="インデックス遅延・重複コンテンツ",
            mitigation="Fetch as Google/構造化データ/カニバ確認"
        ),
        ActionItem(
            title=f"CRM：オンボ配信3通（価値→不安解消→締切）（{f6}）",
            why="初回体験の質はLTVに直結。離脱を抑制し継続へ繋ぐ。",
            steps=[
                "価値提示（成功体験と導入事例）",
                "不安解消（返金/サポート/実装手順）",
                "締切（特典/期限）と次の行動を1つだけ",
            ],
            kpi="開封率 / クリック率 / 継続率",
            target="開封 +5pt / クリック +2pt / 継続 +3pt",
            resources=srcs,
            effort="2時間 / 0円",
            risks="過度な訴求でスパム判定",
            mitigation="配信頻度を週1〜2に調整/オプト明記"
        ),
    ]

    return {
        "why": why_text,
        "sources": srcs,
        "today": today,
        "week": week,
        "month": month,
    }
