import os
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
st.set_page_config(page_title="集客コンサルAI Pro", page_icon="📈", layout="centered")
st.markdown("""
<style>
html, body, [class*="css"]  { font-size: 16px; }
.stButton>button, .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
  min-height: 48px; font-size: 16px;
}
.card { border: 1px solid #e8e8e8; border-radius: 12px; padding: 14px; margin: 8px 0; background: white; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
.kpi { background:#f8fafc; border:1px solid #e2e8f0; border-radius:12px; padding:12px; }
.small { color:#6b7280; font-size:12px; }
.step { display:inline-block; padding:4px 10px; border-radius:999px; background:#f2f4f7; margin-right:8px; font-size:13px; }
.ad { border:1px dashed #c9c9c9; border-radius:12px; padding:14px; margin:8px 0; background:#fffef7; }
@media (max-width: 480px) { html, body, [class*="css"]  { font-size: 17px; } }
</style>
""", unsafe_allow_html=True)

# =========================
# セッション初期化
# =========================
if "page" not in st.session_state:
    st.session_state.page = "input"   # "input" -> "ad" -> "result"
if "inputs" not in st.session_state:
    st.session_state.inputs = {}
if "is_paid" not in st.session_state:
    st.session_state.is_paid = False
if "ad_started_at" not in st.session_state:
    st.session_state.ad_started_at = None

def goto(page_name: str):
    st.session_state.page = page_name
    st.rerun()

# =========================
# プラン（無料/有料）
# =========================
def check_paid(passcode: str) -> bool:
    # 本番はStripe等で検証
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

    st.markdown("---")
    st.markdown("**有料で解放**")
    st.markdown("- 7日フルプラン（無料は3日）\n- 予算配分の細分化（チャネル×目的）\n- LP改善チェックリスト（30項目）\n- 実験ロードマップ（優先度/工数）\n- 投稿案バリエーション（角度×CTA）")

# =========================
# 業種テンプレ（重み/係数）
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
    "SNS": [
        "保存率をKPIに設定し、連載形式のカルーセル化",
        "投稿→プロフィール→LPの導線を明示（矢印/絵文字）",
        "UGCの収集と二次活用（許諾必須）",
    ],
    "検索": [
        "悩みベースのロングテールKWで記事化",
        "比較/ランキング型コンテンツでCVまで導線設計",
        "内部リンク最適化で回遊率UP",
    ],
    "広告": [
        "否定KW/除外プレースメントの定期棚卸し",
        "LPのヒーローコピーABテスト（痛み→解決→根拠）",
        "コンバージョンAPI等の計測整備",
    ],
    "メール/LINE":[
        "オンボ配信で価値体験を3通で設計",
        "件名はベネフィット先行＋絵文字1つまで",
        "セグメント配信で頻度を最適化",
    ],
}

# =========================
# 診断ロジック
# =========================
def funnel_diagnosis(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """AARRRの現状スコアとボトルネック特定"""
    industry = inputs.get("industry", "その他")
    w = INDUSTRY_WEIGHTS.get(industry, INDUSTRY_WEIGHTS["その他"])

    # ベーススコア（0-100）: 回答から簡易推定（無回答は50）
    def s(key, default=50): 
        return int(inputs.get(key, default)) if isinstance(inputs.get(key), (int, float)) else default

    # 自己評価（0-100）を受ける
    awareness     = min(100, max(0, s("score_awareness", 50))) * w["awareness"]
    consideration = min(100, max(0, s("score_consideration", 50))) * w["consideration"]
    conversion    = min(100, max(0, s("score_conversion", 50))) * w["conversion"]
    retention     = min(100, max(0, s("score_retention", 50))) * w["retention"]
    referral      = min(100, max(0, s("score_referral", 50))) * w["referral"]

    scores = {
        "Awareness(認知)": round(awareness,1),
        "Consideration(検討)": round(consideration,1),
        "Conversion(成約)": round(conversion,1),
        "Retention(継続)": round(retention,1),
        "Referral(紹介)": round(referral,1),
    }
    # 最低スコア=ボトルネック
    bottleneck = min(scores, key=scores.get)
    return {"scores": scores, "bottleneck": bottleneck}

def budget_allocation(inputs: Dict[str, Any]) -> pd.DataFrame:
    """目的とチャネル適合度から予算を自動配分"""
    budget = max(0, int(inputs.get("budget", 0)))
    channels = inputs.get("channels", ["SNS", "検索", "広告", "メール/LINE"])[:4]
    goal = (inputs.get("goal") or "") + (inputs.get("objective") or "")
    # 目的に応じた重み（例）
    weights = {}
    for ch in channels:
        if ch == "広告":
            w = 1.4 if any(k in goal for k in ["予約","CV","申込","売上"]) else 1.0
        elif ch == "検索":
            w = 1.3 if any(k in goal for k in ["資料","比較","検討","検索"]) else 1.0
        elif ch == "SNS":
            w = 1.2 if any(k in goal for k in ["認知","フォロ","保存","拡散"]) else 1.0
        elif ch == "メール/LINE":
            w = 1.2 if any(k in goal for k in ["再来店","リピート","継続","LTV"]) else 1.0
        else:
            w = 1.0
        weights[ch] = w
    total_w = sum(weights.values()) or 1
    rows = []
    for ch in channels:
        amount = round(budget * (weights[ch]/total_w))
        rows.append({"チャネル": ch, "推奨配分(円/週)": amount, "戦術ヒント": " / ".join(random.sample(CHANNEL_TIPS.get(ch.split("(")[0], ["基本を徹底"]), k= min(2, len(CHANNEL_TIPS.get(ch.split("(")[0], ["基本を徹底"])))) )})
    return pd.DataFrame(rows)

def kpi_backsolve(inputs: Dict[str, Any]) -> pd.DataFrame:
    """目標から逆算して主要KPIを算出（簡易モデル）"""
    # 入力例：週の目標CV数や売上をgoalから推測（数字抽出できなければ10CV仮置き）
    goal_text = (inputs.get("goal") or "") + " " + (inputs.get("objective") or "")
    # 数字抽出（最初の整数）
    import re
    m = re.search(r"(\d+)", goal_text)
    target_cv = int(m.group(1)) if m else 10

    # 係数（平均的初期値）: imp→click→lead→cv
    ctr = 0.015
    cvr = 0.03
    lead_rate = 0.30  # LPでのリード化や予約入力開始率など

    clicks_needed = math.ceil(target_cv / cvr)
    imps_needed   = math.ceil(clicks_needed / ctr)
    leads_needed  = math.ceil(clicks_needed * lead_rate)

    rows = [
        {"指標": "必要CV数", "目標値": target_cv, "メモ": "goalから抽出（未指定は10を仮置き）"},
        {"指標": "必要クリック数", "目標値": clicks_needed, "メモ": f"CVR {int(cvr*100)}%想定"},
        {"指標": "必要インプレッション", "目標値": imps_needed, "メモ": f"CTR {int(ctr*100)}%想定"},
        {"指標": "必要リード/開始数", "目標値": leads_needed, "メモ": f"開始率 {int(lead_rate*100)}%想定"},
    ]
    return pd.DataFrame(rows)

def experiment_roadmap(inputs: Dict[str, Any], is_paid: bool) -> pd.DataFrame:
    """実験テーマを優先度付け（インパクト×実行容易性）"""
    theme_pool = [
        {"実験": "LPヒーロー見出し AB", "領域": "LP/コピー", "impact": 4, "ease": 4},
        {"実験": "申込フォーム項目削減", "領域": "CVR",   "impact": 5, "ease": 3},
        {"実験": "否定KW/除外面 最適化", "領域": "広告",  "impact": 4, "ease": 5},
        {"実験": "保存率を狙うカルーセル", "領域": "SNS",  "impact": 3, "ease": 4},
        {"実験": "比較記事の追加作成",   "領域": "SEO",  "impact": 4, "ease": 2},
        {"実験": "オンボ配信3通構築",    "領域": "CRM",  "impact": 3, "ease": 4},
        {"実験": "価格訴求LPの別軸作成", "領域": "LP/オファー","impact":5,"ease":2},
    ]
    df = pd.DataFrame(theme_pool)
    df["優先度スコア"] = df["impact"]*0.65 + df["ease"]*0.35
    df = df.sort_values("優先度スコア", ascending=False)
    return df.head(10 if is_paid else 5)

def lp_checklist(is_paid: bool) -> List[str]:
    base = [
        "ヒーロー：痛み→解決→根拠の順に1スクリーンで提示",
        "一次CTAはファーストビューで視認可能（対比色）",
        "社会的証明（レビュー/受賞/導入社数）を上部に配置",
        "フォーム項目は最小限（氏名/メール/電話のどれかに絞る）",
        "モバイルロード3秒以内（画像圧縮/CSS最適化）",
        "UTM計測＆CVイベントの二重計測防止",
        "FAQは“購入直前の不安”に直接回答",
        "料金表は“おすすめ”強調と返金/保証の明文化",
        "比較表：自社/他社/放置の3択で優位点を明確化",
        "CTA直前に“ベネフィット要約＋納得材料”を再提示",
    ]
    pro = [
        "E-E-A-T（実体/経歴/実績/透明性）の証跡リンク",
        "ヒートマップで折返し位置・離脱点を可視化",
        "セクション毎の1次KPIを定義（スクロール率/クリック率）",
        "CTA近辺の摩擦語（不安ワード）を除去",
        "モバイル親指リーチに合わせたCTA配置",
        "レビューは具体性（数値/期間/状況）を強制フォーマット化",
        "フォームのインラインバリデーション＆オートフィル最適化",
        "離脱時オファー（ディレイ/頻度上限）",
        "“今やる理由”の設計（締め切り/希少性/時限特典）",
        "LCP/CLS/INPのコアウェブバイタル基準を満たす",
        "Thank youページでの次動線（紹介/共有/予約追いアクション）",
        "問い合わせと予約のCTAを分離（用途別導線）",
        "多言語化時は通貨/単位/証跡のローカライズ",
        "入力補助（住所/日程）で体感スピードUP",
            ]
    return base + (pro if is_paid else [])

def seven_day_plan(inputs: Dict[str, Any], is_paid: bool) -> List[Dict[str, Any]]:
    """より具体的な7日アクション（担当/所要/成果物まで）"""
    start = date.today()
    channels = inputs.get("channels", ["SNS","検索","広告","メール/LINE"])
    product = inputs.get("product","サービス")
    goal = inputs.get("goal","目標未設定")
    tasks_bank = [
        {"title":"ペルソナ再定義＋メッセ軸3本", "owner":"マーケ", "hrs":2, "deliverable":"メッセージブリーフ"},
        {"title":"LPファーストビュー草案", "owner":"デザイナ", "hrs":3, "deliverable":"ヒーロー案×2"},
        {"title":"広告アカウント棚卸し", "owner":"広告運用", "hrs":2, "deliverable":"除外/否定KWリスト"},
        {"title":"比較/悩み記事構成作成", "owner":"編集", "hrs":2, "deliverable":"見出し案"},
        {"title":"SNSカルーセル2本作成", "owner":"SNS担当", "hrs":3, "deliverable":"投稿データ"},
        {"title":"オンボ配信3通ドラフト", "owner":"CRM", "hrs":3, "deliverable":"メール案×3"},
        {"title":"計測タグ/イベント確認", "owner":"エンジニア", "hrs":2, "deliverable":"計測チェック表"},
        {"title":"ABテスト設計", "owner":"PM", "hrs":2, "deliverable":"実験計画書"},
    ]
    plan = []
    themes = [
        "戦略とKPIの確定","メッセージ＆LP初稿","チャネル初期投入",
        "広告学習立ち上げ","CRM整備＆再来動線","分析/AB開始","勝ち筋の強化"
    ]
    for i in range(7):
        d = start + timedelta(days=i)
        day_tasks = random.sample(tasks_bank, k=4 if is_paid else 3)
        plan.append({
            "day": f"{i+1}日目 ({d.month}/{d.day})｜{themes[i]}",
            "goal_context": f"今週の到達目標例：{goal}",
            "tasks": [f"{t['title']}（{t['owner']}・{t['hrs']}h）→成果物：{t['deliverable']}" for t in day_tasks],
            "kpi_hint": [
                "当日の主要KPI：LP直帰率/フォーム到達率/保存率 のいずれか1つだけ追う",
                "定性メモを必ず残す（“気づき”が次の実験の種）",
            ],
        })
    return plan[:7 if is_paid else 3]

def copy_ideas(inputs: Dict[str, Any], is_paid: bool) -> List[str]:
    product = inputs.get("product","サービス")
    usp = inputs.get("strength","強み")
    target = inputs.get("target","あなた")
    angles = [
        f"痛みの顕在化：{target}が放置すると起きる損失→{product}で即回避",
        f"3ステップで完了：{product}の導入手順と{usp}の仕組み",
        f"ビフォー/アフター：7日でこう変わる（実例/数値）",
        f"比較：他手段/他社とくらべて“ここが違う”",
        f"反論処理：“高い/難しい/時間ない”に回答 → CTA",
    ]
    ideas = [f"{i+1}. {a}｜CTA: 今すぐチェック" for i,a in enumerate(angles)]
    return ideas if is_paid else ideas[:3]

def build_utm(url: str, source="instagram", medium="social", campaign="launch", content="post") -> str:
    if not url: return ""
    join = "&" if "?" in url else "?"
    return f"{url}{join}utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}"

# =========================
# ヘッダー
# =========================
st.title("📈 集客コンサルAI Pro")
st.caption("数値前提で診断→具体的アクションとKPI逆算まで。")

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
                goal = st.text_input("数値目標（例：週予約20件/売上30万円）")
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
            st.session_state.ad_started_at = time.time()
            goto("ad")

# =========================
# 広告インタースティシャル
# =========================
def render_ad():
    if not st.session_state.inputs: goto("input")
    st.markdown('<span class="step">STEP 2</span> お知らせ（スポンサー）', unsafe_allow_html=True)
    st.markdown("結果の準備中…スポンサーからのお知らせをご覧ください。")
    ads = [
        {"title": "📣 SNS運用テンプレ100選", "desc": "今すぐ使える投稿ネタ集（無料）", "cta": "ダウンロード"},
        {"title": "🎯 小予算でも効く広告講座", "desc": "1日30分で学べる実践講座", "cta": "詳細を見る"},
        {"title": "🧰 無料KPIダッシュボード", "desc": "スプレッドシートで簡単管理", "cta": "テンプレ入手"},
    ]
    random.shuffle(ads)
    for ad in ads:
        st.markdown(f"""<div class="ad"><h4>{ad["title"]}</h4><p>{ad["desc"]}</p></div>""", unsafe_allow_html=True)

    # カウントダウンと自動遷移（JSフォールバック込み）
    min_view = 3
    if st.session_state.ad_started_at is None: st.session_state.ad_started_at = time.time()
    elapsed = int(time.time() - st.session_state.ad_started_at)
    remain = max(0, min_view - elapsed)
    st.info(f"結果へ自動的に移動します… {remain} 秒")
    if hasattr(st, "autorefresh"): st.autorefresh(interval=500, limit=20, key="ad_refresh_key")
    st.markdown("""<script>setTimeout(function(){ if (window && window.location) { window.location.reload(); } }, 500);</script>""", unsafe_allow_html=True)
    colA, colB = st.columns(2)
    with colA: st.button("スポンサーをもう一つ見る 🔁")
    with colB:
        if st.button("広告を閉じて結果へ ▶", disabled=remain>0):
            goto("result")
    if remain <= 0: goto("result")

# =========================
# 結果画面
# =========================
def render_result():
    if not st.session_state.inputs: goto("input")
    inputs = st.session_state.inputs
    is_paid = st.session_state.is_paid

    # 概要
    st.markdown('<span class="step">STEP 3</span> 診断結果とアクション', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔎 サマリー")
    st.write(f"- **業種**: {inputs.get('industry')}｜**地域**: {inputs.get('region')}")
    st.write(f"- **商品/サービス**: {inputs.get('product')}｜**ターゲット**: {inputs.get('target')}")
    st.write(f"- **目標**: {inputs.get('goal')}｜**週予算**: {inputs.get('budget')}円｜**チャネル**: {', '.join(inputs.get('channels') or [])}")
    st.write(f"- **強み/弱み**: {inputs.get('strength')} / {inputs.get('weakness')}")
    st.markdown('</div>', unsafe_allow_html=True)

    # 1) ファネル診断
    diag = funnel_diagnosis(inputs)
    st.markdown("### 1) ファネル診断（AARRR）")
    score_df = pd.DataFrame([diag["scores"]]).T.reset_index()
    score_df.columns = ["ファネル", "スコア(0-100)"]
    st.dataframe(score_df, hide_index=True, use_container_width=True)
    st.info(f"ボトルネック：**{diag['bottleneck']}**")

    # 2) KPI逆算
    st.markdown("### 2) KPI逆算（ゴールからのバックキャスト）")
    kpi_df = kpi_backsolve(inputs)
    st.dataframe(kpi_df, hide_index=True, use_container_width=True)

    # 3) 予算配分
    st.markdown("### 3) 週予算の推奨配分")
    alloc_df = budget_allocation(inputs)
    st.dataframe(alloc_df, hide_index=True, use_container_width=True)

    # 4) 7日アクションプラン
    st.markdown("### 4) 7日アクションプラン")
    plan = seven_day_plan(inputs, is_paid=is_paid)
    for d in plan:
        st.markdown(f"**{d['day']}** — {d['goal_context']}")
        for t in d["tasks"]:
            st.write("- " + t)
        st.markdown('<div class="kpi">💡 '+ " / ".join(d["kpi_hint"]) + "</div>", unsafe_allow_html=True)

    # CSV出力（プラン）
    plan_df = pd.DataFrame([{
        "day": d["day"], "goal": d["goal_context"], 
        "tasks": " | ".join(d["tasks"]),
        "hints": " / ".join(d["kpi_hint"])
    } for d in plan])
    st.download_button("📥 7日プランをCSVでダウンロード", plan_df.to_csv(index=False).encode("utf-8-sig"), "7day_plan.csv", "text/csv")

    # 5) 実験ロードマップ
    st.markdown("### 5) 実験ロードマップ（優先度順）")
    exp_df = experiment_roadmap(inputs, is_paid=is_paid)
    st.dataframe(exp_df, hide_index=True, use_container_width=True)

    # 6) 投稿アイデア（有料で拡張）
    st.markdown("### 6) 投稿アイデア（角度×CTA）")
    for line in copy_ideas(inputs, is_paid):
        st.write(line)

    # 7) LPチェックリスト
    st.markdown("### 7) LP改善チェックリスト")
    for i, item in enumerate(lp_checklist(is_paid), 1):
        st.write(f"{i}. {item}")

    # UTMビルダー（おまけ）
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
