import os
import time
import random
from datetime import date, timedelta

import pandas as pd
import streamlit as st

# ----------------------------------
# ページ設定（スマホ向け最適化）
# ----------------------------------
st.set_page_config(
    page_title="集客コンサルAI",
    page_icon="📈",
    layout="centered",
)

# シンプルなモバイル最適化CSS
st.markdown("""
<style>
html, body, [class*="css"]  { font-size: 16px; }
.stButton>button, .stTextInput input, .stSelectbox select, .stNumberInput input, .stTextArea textarea {
  min-height: 48px; font-size: 16px;
}
.card { border: 1px solid #e8e8e8; border-radius: 12px; padding: 14px; margin: 8px 0; background: white; box-shadow: 0 1px 2px rgba(0,0,0,0.04); }
h1, h2, h3 { line-height: 1.3; }
.step { display: inline-block; padding: 4px 10px; border-radius: 999px; background: #f2f4f7; margin-right: 8px; font-size: 13px; }
.ad { border: 1px dashed #c9c9c9; border-radius: 12px; padding: 14px; margin: 8px 0; background: #fffef7; }
.small { color:#6b7280; font-size: 12px; }
@media (max-width: 480px) { html, body, [class*="css"]  { font-size: 17px; } }
</style>
""", unsafe_allow_html=True)

# ----------------------------------
# セッション初期化
# ----------------------------------
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

# ----------------------------------
# 無料/有料 判定
# ----------------------------------
def check_paid(passcode: str) -> bool:
    # デモ用：本番はStripe/Webhookで検証してください
    return passcode.strip() == os.getenv("PAID_PASSCODE", "PAID2025")

with st.sidebar:
    st.subheader("プラン")
    plan = st.radio(
        "利用プランを選択",
        options=["無料", "有料（コード入力）"],
        index=0,
        help="デモでは「PAID2025」が有料コードです。"
    )
    if plan.startswith("有料"):
        code = st.text_input("購入コード（例: PAID2025）", type="password")
        if st.button("コードを確認"):
            st.session_state.is_paid = check_paid(code)
            if st.session_state.is_paid:
                st.success("有料機能が有効になりました。")
            else:
                st.error("コードが正しくありません。")
    else:
        st.session_state.is_paid = False

    st.markdown("---")
    st.markdown("**有料でできること**")
    st.markdown("- 7日フルプラン（無料は3日まで）\n- チャネル別の詳細タスク\n- KPIと目標値の自動提案\n- UTMリンクビルダー\n- 投稿文・見出しのAI生成（オフライン簡易版）")

# ----------------------------------
# ルールベースの簡易生成器（オフライン）
# ----------------------------------
CHANNEL_TIPS = {
    "SNS(Instagram/Threads/X等)": [
        "ターゲットの関心語句でハッシュタグ調査",
        "投稿の保存率をKPIにし、カルーセル構成をテスト",
        "UGC（お客様の声）を週2本取り入れる",
    ],
    "検索(SEO/コンテンツ)": [
        "悩みベースのロングテールKWを3つ選定",
        "見出し(H2/H3)にベネフィットを必ず入れる",
        "内部リンクで回遊率を改善（2→3以上）",
    ],
    "広告(リスティング/ディスプレイ)": [
        "1日目はCPC目標を高めに設定して学習を促進",
        "LPのヒーロー見出しをABテスト（2パターン）",
        "否定KWと除外プレースメントを必ず設定",
    ],
    "メール/LINE": [
        "オンボーディング配信（3通）を用意",
        "CTAは1メール1つに絞る",
        "送信は火・木の12時/18時のどちらかでテスト",
    ],
    "オフライン(チラシ/イベント)": [
        "QRでLPへ遷移しUTMで計測",
        "近隣コラボ（相互紹介）を最低1件実施",
        "イベント後24時間以内にフォロー連絡",
    ],
}

def generate_7day_plan(inputs: dict, days: int = 7) -> list:
    industry = inputs.get("industry", "汎用")
    goal = inputs.get("goal", "")
    objective = inputs.get("objective", "")
    budget = inputs.get("budget", 0)
    channels = inputs.get("channels", [])
    target = inputs.get("target", "")
    region = inputs.get("region", "")
    strength = inputs.get("strength", "")
    weakness = inputs.get("weakness", "")

    themes = [
        "戦略設計とKPI設定",
        "ターゲットと価値提案の明確化",
        "チャネル設計とコンテンツ設計",
        "制作・初期投入",
        "配信/公開・初期学習",
        "計測・改善・ABテスト",
        "伸ばす施策の強化と次週の布石",
    ]

    plan = []
    start = date.today()
    for i in range(days):
        d = start + timedelta(days=i)
        day_channels = channels if channels else ["SNS(Instagram/Threads/X等)"]
        channel_tip_lines = []
        for ch in day_channels[:3]:
            tips = CHANNEL_TIPS.get(ch, CHANNEL_TIPS["SNS(Instagram/Threads/X等)"])
            sample = random.sample(tips, k=min(2, len(tips)))
            channel_tip_lines.append(f"【{ch}】" + " / ".join(sample))

        tasks = [
            f"業種: {industry}｜地域: {region}｜ターゲット: {target}",
            f"ゴール: {goal}｜目的: {objective}｜予算目安: {budget}円/週",
            f"強み: {strength}｜弱み: {weakness}",
            *channel_tip_lines
        ]

        kpi = []
        if "広告" in "".join(day_channels):
            kpi.append("CTR 1.5% / CVR 3% を初期目標")
        if "SNS" in "".join(day_channels):
            kpi.append("保存率 5% / プロフィール遷移率 1.5%")
        if "検索" in "".join(day_channels):
            kpi.append("直帰率 < 60% / 平均滞在時間 > 1:20")

        plan.append({
            "day": f"{i+1}日目 ({d.strftime('%-m/%-d') if hasattr(d, 'strftime') else d.strftime('%m/%d')})",
            "theme": themes[i] if i < len(themes) else "最適化の継続",
            "tasks": tasks,
            "kpi": kpi or ["KPI: 目標指標を1つに絞って追う"],
        })
    return plan

def simple_copy_suggestions(inputs: dict, n: int = 5) -> list:
    product = inputs.get("product", "サービス")
    target = inputs.get("target", "あなた")
    usp = inputs.get("strength", "強み")
    cta = "今すぐチェック"
    templates = [
        f"{target}の悩み、{product}で解決。{usp}。{cta}！",
        f"{product}、はじめるなら今。まずは無料で体験。",
        f"たった7日で変化を実感。{product}のはじめ方ガイド公開中。",
        f"【期間限定】{product}の先着特典あり。詳細はプロフィールへ。",
        f"{usp}の理由、投稿で詳しく解説。保存して後で読む↑",
    ]
    return templates[:n]

def build_utm(url: str, source="instagram", medium="social", campaign="launch", content="post") -> str:
    if not url:
        return ""
    join = "&" if "?" in url else "?"
    return f"{url}{join}utm_source={source}&utm_medium={medium}&utm_campaign={campaign}&utm_content={content}"

# ----------------------------------
# UI: ヘッダー
# ----------------------------------
st.title("📈 集客コンサルAI")
st.caption("目標と状況を入れるだけで、7日間のアクションプランを自動作成。")

# ----------------------------------
# 入力フォーム（Step 1）
# ----------------------------------
def render_input():
    st.markdown('<span class="step">STEP 1</span> 基本情報を入力', unsafe_allow_html=True)
    with st.form("brief"):
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                industry = st.selectbox("業種", ["小売/EC", "飲食", "美容/サロン", "教育/スクール", "B2Bサービス", "クリニック/医療", "不動産", "その他"], index=0)
                region = st.text_input("地域（例：東京・オンライン）")
                budget = st.number_input("週予算（円）", min_value=0, step=1000, value=20000)
                target = st.text_input("主なターゲット（例：20代女性・ママ）")
            with col2:
                product = st.text_input("商品/サービス名（例：○○体験プラン）")
                goal = st.text_input("目標（例：週あたり予約10件・売上30万円）")
                objective = st.text_area("目的（背景/課題）", height=100,
                                         placeholder="例：新店舗の認知拡大。既存客の再来店促進。")
                channels = st.multiselect(
                    "活用チャネル（3つまで推奨）",
                    list(CHANNEL_TIPS.keys()),
                    default=["SNS(Instagram/Threads/X等)"]
                )
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown('<div class="card">', unsafe_allow_html=True)
            col3, col4 = st.columns(2)
            with col3:
                strength = st.text_area("強み（USP）", height=80, placeholder="例：口コミ評価4.8／即日対応 など")
            with col4:
                weakness = st.text_area("弱み/制約", height=80, placeholder="例：人手が少ない／広告費を大きく使えない など")
            st.markdown('</div>', unsafe_allow_html=True)

        submit = st.form_submit_button("診断する ▶")
        if submit:
            st.session_state.inputs = {
                "industry": industry,
                "region": region,
                "budget": budget,
                "target": target,
                "product": product,
                "goal": goal,
                "objective": objective,
                "channels": channels,
                "strength": strength,
                "weakness": weakness,
            }
            st.session_state.ad_started_at = time.time()
            goto("ad")

# ----------------------------------
# 広告インタースティシャル（Step 2）
# ----------------------------------
def render_ad():
    # 入力ガード
    if not st.session_state.inputs:
        goto("input")

    st.markdown('<span class="step">STEP 2</span> お知らせ（スポンサー）', unsafe_allow_html=True)
    st.markdown("結果の準備中…以下のスポンサーからのお知らせをご覧ください。")

    ads = [
        {"title": "📣 SNS運用テンプレ100選", "desc": "今すぐ使える投稿ネタ集（無料）", "cta": "ダウンロード"},
        {"title": "🎯 小予算でも効く広告講座", "desc": "1日30分で学べる実践講座", "cta": "詳細を見る"},
        {"title": "🧰 無料KPIダッシュボード", "desc": "スプレッドシートで簡単管理", "cta": "テンプレ入手"},
    ]
    random.shuffle(ads)
    for ad in ads:
        with st.container():
            st.markdown('<div class="ad">', unsafe_allow_html=True)
            st.subheader(ad["title"])
            st.write(ad["desc"])
            st.button(f"{ad['cta']} →", key=f"ad_{ad['title']}_{random.randint(1,9999)}")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- カウントダウンと安全な自動遷移 ---
    min_view = 3  # 秒
    if st.session_state.ad_started_at is None:
        st.session_state.ad_started_at = time.time()

    elapsed = int(time.time() - st.session_state.ad_started_at)
    remain = max(0, min_view - elapsed)

    st.info(f"結果へ自動的に移動します… {remain} 秒")

    # 一定間隔で画面を再描画（ブロッキング無し）
    if hasattr(st, "autorefresh"):
        st.autorefresh(interval=500, limit=20, key="ad_refresh_key")  # 0.5秒ごとに再描画

    colA, colB = st.columns(2)
    with colA:
        st.button("スポンサーをもう一つ見る 🔁")
    with colB:
        disabled = remain > 0
        if st.button("広告を閉じて結果へ ▶", disabled=disabled):
            goto("result")

    # 自動遷移（最小表示時間を過ぎたら）
    if remain <= 0:
        goto("result")

# ----------------------------------
# 結果（Step 3）
# ----------------------------------
def render_result():
    if not st.session_state.inputs:
        goto("input")

    st.markdown('<span class="step">STEP 3</span> 7日間アクションプラン', unsafe_allow_html=True)

    inputs = st.session_state.inputs
    is_paid = st.session_state.is_paid

    days = 7 if is_paid else 3
    plan = generate_7day_plan(inputs, days=7)  # フル生成
    visible_plan = plan[:days]

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔎 診断サマリー")
    st.write(f"- **業種**: {inputs.get('industry')}｜**地域**: {inputs.get('region')}")
    st.write(f"- **商品/サービス**: {inputs.get('product')}｜**ターゲット**: {inputs.get('target')}")
    st.write(f"- **目標**: {inputs.get('goal')}｜**週予算**: {inputs.get('budget')}円")
    st.write(f"- **活用チャネル**: {', '.join(inputs.get('channels') or ['未選択'])}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("📅 7日間プラン（無料は3日分）")
    for day in visible_plan:
        with st.container():
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"### {day['day']}｜{day['theme']}")
            st.markdown("**タスク**")
            for t in day["tasks"]:
                st.write("- " + t)
            st.markdown("**推奨KPI（初期目安）**")
            for k in day["kpi"]:
                st.write("- " + k)
            st.markdown('</div>', unsafe_allow_html=True)

    df = pd.DataFrame([
        {"day": d["day"], "theme": d["theme"], "tasks": " / ".join(d["tasks"]), "kpi": " / ".join(d["kpi"])}
        for d in visible_plan
    ])
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("CSVでダウンロード", data=csv, file_name="7day_plan.csv", mime="text/csv")

    if is_paid:
        st.markdown("## ⭐ 有料機能")
        with st.expander("AI投稿文/見出しサジェスト（簡易）"):
            copies = simple_copy_suggestions(inputs, n=5)
            for i, c in enumerate(copies, 1):
                st.write(f"{i}. {c}")

        with st.expander("UTMリンクビルダー"):
            base = st.text_input("ベースURL（例：https://example.com/landing）", value="https://example.com/landing")
            col1, col2, col3, col4 = st.columns(4)
            with col1: src = st.text_input("utm_source", value="instagram")
            with col2: med = st.text_input("utm_medium", value="social")
            with col3: camp = st.text_input("utm_campaign", value="launch")
            with col4: cont = st.text_input("utm_content", value="post")
            utm = build_utm(base, src, med, camp, cont)
            if utm:
                st.code(utm, language="text")

        with st.expander("チャネル別 詳細ToDo（深掘り）"):
            for ch in inputs.get("channels", []):
                st.markdown(f"**{ch}**")
                for tip in CHANNEL_TIPS.get(ch, []):
                    st.write("- " + tip)
    else:
        st.info("残りの4日間と詳細は有料プランでご利用いただけます。サイドバーから有料コードを有効化してください。")

    if st.button("◀ 入力に戻る"):
        goto("input")

# ----------------------------------
# 画面遷移
# ----------------------------------
if st.session_state.page == "input":
    render_input()
elif st.session_state.page == "ad":
    render_ad()
else:
    render_result()

st.markdown("---")
st.markdown('<p class="small">※ 本ツールはデモです。KPIや施策は一般的な初期目安であり、結果を保証するものではありません。</p>', unsafe_allow_html=True)
