# app.py
import streamlit as st
import time
import random
from ai_engine import generate_consulting

# --- ページ設定 ---
st.set_page_config(page_title="AI集客コンサル", page_icon="📈", layout="centered")

if "page" not in st.session_state:
    st.session_state.page = "input"
if "inputs" not in st.session_state:
    st.session_state.inputs = None
if "ad_started_at" not in st.session_state:
    st.session_state.ad_started_at = None

def goto(page: str):
    st.session_state.page = page
    st.rerun()

# --- 各ページ描画 ---
def render_input():
    st.title("📊 集客コンサルAI")
    st.write("目標・ターゲット・予算を入力してください")

    with st.form("input_form"):
        goal = st.text_input("目標（例: 売上を伸ばしたい）")
        target = st.text_input("ターゲット（例: 20代女性）")
        budget = st.number_input("予算（円）", min_value=0, step=1000)
        submitted = st.form_submit_button("診断する ▶")

    if submitted:
        st.session_state.inputs = {"goal": goal, "target": target, "budget": budget}
        goto("ad")

def render_ad():
    if not st.session_state.inputs:
        goto("input")

    st.subheader("スポンサーからのお知らせ")
    ads = [
        {"title": "📣 SNS運用テンプレ100選", "desc": "今すぐ使える投稿ネタ集（無料）"},
        {"title": "🎯 小予算でも効く広告講座", "desc": "1日30分で学べる実践講座"},
        {"title": "🧰 無料KPIダッシュボード", "desc": "スプレッドシートで簡単管理"},
    ]
    random.shuffle(ads)
    for ad in ads:
        st.markdown(f"### {ad['title']}\n{ad['desc']}")

    min_view = 3
    if st.session_state.ad_started_at is None:
        st.session_state.ad_started_at = int(time.time())

    elapsed = int(time.time() - st.session_state.ad_started_at)
    remain = max(0, min_view - elapsed)

    if remain > 0:
        st.info(f"結果へ自動的に移動します… {remain} 秒")
        st.experimental_autorefresh(interval=1000, key="ad_timer")
    else:
        st.session_state.ad_started_at = None
        goto("result")

def render_result():
    if not st.session_state.inputs:
        goto("input")

    st.title("📈 あなたの集客アクションプラン")

    inputs = st.session_state.inputs
    advice = generate_consulting(inputs["goal"], inputs["target"], inputs["budget"])

    st.markdown(advice)

    if st.button("🔄 もう一度診断する"):
        st.session_state.inputs = None
        goto("input")

# --- ルーティング ---
if st.session_state.page == "input":
    render_input()
elif st.session_state.page == "ad":
    render_ad()
elif st.session_state.page == "result":
    render_result()
