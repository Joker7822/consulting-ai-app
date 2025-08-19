import os
import re
import math
import time
import random
from datetime import date, timedelta
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

# =========================
# ページ設定（スマホ向け）
# =========================
st.set_page_config(page_title="集客コンサルAI Pro+ (Stable)", page_icon="🤝", layout="centered")
st.markdown("""
<style>
html, body, [class*="css"]  { font-size: 16px; }
.stButton>button, .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
  min-height: 48px; font-size: 16px;
}
.card { border: 1px solid #e5e7eb; border-radius: 12px; padding: 14px; margin: 8px 0; background: white; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.kpi { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:12px; }
.small { color:#6b7280; font-size:12px; }
.step { display:inline-block; padding:4px 10px; border-radius:999px; background:#f2f4f7; margin-right:8px; font-size:13px; }
.ad { border:1px dashed #c9c9c9; border-radius:12px; padding:14px; margin:8px 0; background:#fffef7; }
</style>
""", unsafe_allow_html=True)

# =========================
# セッション初期化
# =========================
def ensure_session():
    st.session_state.setdefault("page", "input")   # "input" -> "ad" -> "result"
    st.session_state.setdefault("inputs", {})
    st.session_state.setdefault("is_paid", False)
    st.session_state.setdefault("ad_started_at", None)
    st.session_state.setdefault("tone", "やさしめ")

ensure_session()

def goto(page_name: str):
    st.session_state.page = page_name
    st.rerun()

# =========================
# プラン（無料/有料）
# =========================
def check_paid(passcode: str) -> bool:
    return passcode.strip() == os.getenv("PAID_PASSCODE", "PAID2025")

with st.sidebar:
    st.subheader("プラン")
    plan = st.radio("利用プラン", ["無料", "有料（コード入力）"], index=0)
    if plan.startswith("有料"):
        code = st.text_input("購入コード（例: PAID2025）", type="password")
        if st.button("コードを確認"):
            st.session_state.is_paid = check_paid(code)
            st.success("有料機能が有効です。") if st.session_state.is_paid else st.error("コードが正しくありません。")
    else:
        st.session_state.is_paid = False

    tone = st.selectbox("アドバイスの口調", ["やさしめ", "ビジネス標準", "元気に背中押し"], index=0)
    st.session_state["tone"] = tone

    st.markdown("---")
    st.markdown("**有料で解放**")
    st.markdown("- 7日フルプラン（無料は3日）\n- SMART目標の自動整形\n- 予算配分（目的×チャネル）詳細\n- LP改善チェックリスト拡張（30項目）\n- 実験ロードマップ（優先度/工数/仮説）\n- 具体例：投稿/広告/LP/DM/電話トーク")

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

def humanize(text: str, tone: str) -> str:
    if tone == "やさしめ": return "😊 " + text
    if tone == "元気に背中押し": return "🔥 " + text + " いけます！"
    return text

# =========================
# ロジック
# =========================
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

def build_utm(url: str, source="instagram", medium="social", campaign="launch", content="post") -> str:
    if not url: return ""
    join = "&" if "?" in url else "?"
    return f"{url}{join}utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}"

# =========================
# ヘッダー
# =========================
st.title("🤝 集客コンサルAI Pro+ (Stable)")
st.caption("やさしく、でも本格派。数値→計画→実行まで伴走します。")

# =========================
# 入力フォーム
# =========================
def render_input():
    st.markdown('<span class="step">STEP 1</span> ブリーフ入力', unsafe_allow_html=True)
    with st.form("brief"):
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                industry = st.selectbox("業種", list(INDUSTRY_WEIGHTS.keys()), index=0)
                region = st.text_input("地域（例：東京・オンライン）")
                budget = st.number_input("週予算（円）", min_value=0, step=1000, value=50000)
                target = st.text_input("主ターゲット（例：20代女性/個人事業主）")
                product = st.text_input("商品/サービス名（例：○○体験プラン）")
            with col2:
                goal = st.text_input("目標（例：週予約20件/売上30万円）")
                objective = st.text_area("目的/背景", height=80, placeholder="例：新店舗の立ち上げ/既存客の再来促進")
                channels = st.multiselect("活用チャネル（最大4）", ["SNS","検索","広告","メール/LINE"], default=["SNS","広告"])
                strength = st.text_area("強み（USP）", height=70, placeholder="例：即日対応/レビュー4.8/返金保証")
                weakness = st.text_area("弱み/制約", height=70, placeholder="例：人手不足/在庫制約/高単価")
            st.markdown('</div>', unsafe_allow_html=True)

        with st.expander("任意：現状自己評価（0〜100）"):
            c1, c2, c3 = st.columns(3)
            score_awareness = c1.slider("認知(Awareness)", 0, 100, 50)
            score_consideration = c2.slider("検討(Consideration)", 0, 100, 50)
            score_conversion = c3.slider("成約(Conversion)", 0, 100, 50)
            c4, c5 = st.columns(2)
            score_retention = c4.slider("継続(Retention)", 0, 100, 50)
            score_referral = c5.slider("紹介(Referral)", 0, 100, 50)

        submitted = st.form_submit_button("診断する ▶")
        if submitted:
            st.session_state.inputs = {
                "industry": industry, "region": region, "budget": budget, "target": target,
                "product": product, "goal": goal, "objective": objective, "channels": channels,
                "strength": strength, "weakness": weakness,
                "score_awareness": score_awareness, "score_consideration": score_consideration,
                "score_conversion": score_conversion, "score_retention": score_retention,
                "score_referral": score_referral,
            }
            st.session_state.ad_started_at = None
            goto("ad")

# =========================
# 広告インタースティシャル（安定版）
# =========================
def render_ad():
    if not st.session_state.inputs: goto("input")

    st.markdown('<span class="step">STEP 2</span> お知らせ（スポンサー）', unsafe_allow_html=True)
    st.markdown("結果の準備中…スポンサーからのお知らせをご覧ください。")

    ads = [
        {"title": "📣 SNS運用テンプレ100選", "desc": "今すぐ使える投稿ネタ集（無料）"},
        {"title": "🎯 小予算でも効く広告講座", "desc": "1日30分で学べる実践講座"},
        {"title": "🧰 無料KPIダッシュボード", "desc": "スプレッドシートで簡単管理"},
    ]
    random.shuffle(ads)
    for ad in ads:
        st.markdown(f"""<div class="ad"><strong>{ad["title"]}</strong><div>{ad["desc"]}</div></div>""", unsafe_allow_html=True)

    # --- 安定カウントダウン: st.autorefresh を使用 ---
    min_view = 3  # 秒
    if st.session_state.ad_started_at is None:
        st.session_state.ad_started_at = int(time.time())

    elapsed = int(time.time() - st.session_state.ad_started_at)
    remain = max(0, min_view - elapsed)
    st.info(f"結果へ自動的に移動します… {remain} 秒")

    # 1秒ごとに再描画。remain回まで自動更新。
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=1000, limit=remain, key="ad_timer_key")
    else:
        # ごく古いStreamlit用フォールバック（軽め）
        st.markdown("""<script>setTimeout(function(){ if (window && window.location) window.location.reload(); }, 1000);</script>""", unsafe_allow_html=True)

    # 手動スキップボタン（3秒後に自動で押下されるのと同等）
    btn_disabled = remain > 0
    if st.button("広告を閉じて結果へ ▶", disabled=btn_disabled):
        goto("result")

    # 自動遷移条件
    if remain <= 0:
        goto("result")

# =========================
# 結果画面
# =========================
def render_result():
    if not st.session_state.inputs: goto("input")
    inputs = st.session_state.inputs
    tone = st.session_state.get("tone", "やさしめ")
    is_paid = st.session_state.is_paid

    st.markdown('<span class="step">STEP 3</span> あなたへの具体提案', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔎 サマリー")
    st.write(f"- **業種**: {inputs.get('industry')}｜**地域**: {inputs.get('region')}")
    st.write(f"- **商品/サービス**: {inputs.get('product')}｜**ターゲット**: {inputs.get('target')}")
    st.write(f"- **目標**: {smartify_goal(inputs.get('goal',''))}")
    st.write(f"- **週予算**: {inputs.get('budget')}円｜**チャネル**: {', '.join(inputs.get('channels') or [])}")
    st.write(f"- **強み/弱み**: {inputs.get('strength')} / {inputs.get('weakness')}")
    st.markdown('</div>', unsafe_allow_html=True)

    diag = funnel_diagnosis(inputs)
    st.markdown("### ファネル診断（AARRR）")
    df_scores = pd.DataFrame([diag["scores"]]).T.reset_index()
    df_scores.columns = ["ファネル", "スコア(0-100)"]
    st.dataframe(df_scores, hide_index=True, use_container_width=True)
    st.info(humanize(f"ボトルネック：**{diag['bottleneck']}**。ここに効くタスクからやりましょう。", tone))

    st.markdown("### KPI逆算（ゴールからバックキャスト）")
    kpi_df = kpi_backsolve(inputs)
    st.dataframe(kpi_df, hide_index=True, use_container_width=True)

    st.markdown("### 週予算の推奨配分")
    alloc_df = budget_allocation(inputs)
    st.dataframe(alloc_df, hide_index=True, use_container_width=True)

    st.markdown("### 今日/今週/今月の3段階アクション")
    acts = three_horizons_actions(inputs, tone)
    for h in ["今日やる", "今週やる", "今月やる"]:
        st.markdown(f"**{h}**")
        for line in acts[h]:
            st.write("- " + line)

    st.markdown("### 具体例（コピーテンプレ/トーク）")
    ex = concrete_examples(inputs, tone)
    st.write(f"**SNS投稿例**：{ex['SNS投稿']}")
    st.write(f"**広告文例**：{ex['広告文']}")
    st.write(f"**LPヒーロー案**：{ex['LPヒーロー']}")
    with st.expander("DMテンプレ / 電話トーク"):
        st.write("**DMテンプレ**：", ex["DMテンプレ"])
        st.write("**電話トーク**：", ex["電話トーク"])

    # ダウンロード（アクションCSV）
    rows = []
    for h in acts:
        for line in acts[h]:
            rows.append({"期間": h, "タスク": line})
    plan_df = pd.DataFrame(rows)
    st.download_button("📥 アクション計画（CSV）", plan_df.to_csv(index=False).encode("utf-8-sig"), "actions.csv", "text/csv")

    # UTMビルダー
    with st.expander("UTMリンクビルダー"):
        base = st.text_input("ベースURL", value="https://example.com/landing")
        c1, c2, c3, c4 = st.columns(4)
        with c1: src = st.text_input("utm_source", value="instagram")
        with c2: med = st.text_input("utm_medium", value="social")
        with c3: camp = st.text_input("utm_campaign", value="launch")
        with c4: cont = st.text_input("utm_content", value="post")
        utm = build_utm(base, src, med, camp, cont)
        if utm: st.code(utm, language="text")

    if st.button("◀ 入力に戻る"):
        goto("input")

# =========================
# 画面遷移
# =========================
if st.session_state.page == "input":
    render_input()
elif st.session_state.page == "ad":
    render_ad()
else:
    render_result()

st.markdown("---")
st.markdown('<p class="small">※ 本ツールは簡易コンサル支援です。数値は初期目安であり、結果を保証するものではありません。</p>', unsafe_allow_html=True)
