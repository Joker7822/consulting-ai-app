import streamlit as st
import random, time

# =============== ヘルパー関数 ===============
def goto(page):
    st.session_state.page = page
    st.rerun()

# =============== アドバイス生成 ===============
def generate_consulting(inputs, tone="やさしめ"):
    goal = inputs.get("goal","")
    target = inputs.get("target","")
    budget = inputs.get("budget","")
    channel = inputs.get("channel","")

    # SMART変換例
    smart_goal = f"「{goal}」をSMART形式にすると → 具体的に『今月{target}向けに◯件の反応を獲得』と定義すると明確です。"

    # ペルソナ
    persona = f"{target}の典型像を描きましょう。悩み・欲求を言語化すると訴求しやすいです。"

    # KPI逆算
    kpi = f"例えば10件CVが欲しいなら、クリック率1%・CVR2%で想定すると {10/(0.01*0.02):,.0f} imp が必要。"

    # アクションプラン
    today = f"今日やる: {channel}アカウントを見直し、1投稿アップ"
    week = f"今週やる: 競合リサーチ3件、広告セット2パターンを試す"
    month = f"今月やる: 予算{budget}円を週単位で配分し、成果を振り返る"

    advice = f"""
## 🎯 SMART目標
{smart_goal}

## 👤 ペルソナ
{persona}

## 📊 KPI逆算
{kpi}

## 🪜 アクションプラン
- {today}
- {week}
- {month}

## 📝 テンプレ例
- SNS投稿見出し: 「知らなきゃ損！{target}必見の◯◯」
- 広告文: 「たった7日で成果、{target}向け無料ガイド」
- LPチェック: ファーストビューに「ベネフィット＋CTA」必須

---
語り口: {tone}
"""
    return advice

# =============== 広告画面 ===============
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
        st.session_state.ad_started_at = time.time()
    elapsed = int(time.time() - st.session_state.ad_started_at)
    remain = max(0, min_view - elapsed)
    st.info(f"結果表示まで {remain} 秒…")

    if remain <= 0:
        goto("result")
    else:
        st.markdown("<script>setTimeout(function(){window.location.reload();}, 1000);</script>", unsafe_allow_html=True)

# =============== 結果画面 ===============
def render_result():
    if not st.session_state.inputs:
        goto("input")

    st.subheader("あなたへのコンサルティング提案")
    advice = generate_consulting(st.session_state.inputs, tone=st.session_state.get("tone","やさしめ"))
    st.markdown(advice)

    if st.session_state.menu == "有料":
        st.markdown("### 🔒 有料限定チェックリスト")
        st.write("- ファネル別の数値目安")
        st.write("- LP改善30項目リスト")
        st.write("- 広告×SNSクロスマーケ戦略")

    if st.button("最初に戻る"):
        st.session_state.page="input"; st.session_state.inputs={}; st.session_state.ad_started_at=None; st.rerun()

# =============== 入力画面 ===============
def render_input():
    st.title("集客コンサルAI")
    st.write("目標・ターゲットなどを入力すると、7日アクションプランを提案します。")

    goal = st.text_input("目標", placeholder="例: 新規顧客を増やしたい")
    target = st.text_input("ターゲット", placeholder="例: 30代女性")
    budget = st.text_input("予算（円）", placeholder="例: 50000")
    channel = st.selectbox("主要チャネル", ["Instagram","TikTok","Google広告","LP","その他"])
    tone = st.selectbox("アドバイスの口調", ["やさしめ","ビジネス","元気"])

    menu = st.radio("メニュー", ["無料","有料"])
    if menu=="有料":
        code = st.text_input("コードを入力してください（例: PAID2025）")
        if code=="PAID2025":
            st.session_state.menu="有料"
        else:
            st.session_state.menu="無料"
    else:
        st.session_state.menu="無料"

    if st.button("診断スタート ▶"):
        st.session_state.inputs={"goal":goal,"target":target,"budget":budget,"channel":channel}
        st.session_state.tone=tone
        st.session_state.ad_started_at=None
        goto("ad")

# =============== ページ遷移 ===============
if "page" not in st.session_state: st.session_state.page="input"
if "inputs" not in st.session_state: st.session_state.inputs={}
if "menu" not in st.session_state: st.session_state.menu="無料"
if "ad_started_at" not in st.session_state: st.session_state.ad_started_at=None

if st.session_state.page=="input": render_input()
elif st.session_state.page=="ad": render_ad()
elif st.session_state.page=="result": render_result()
