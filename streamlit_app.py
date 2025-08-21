# streamlit_app.py

import os
import time
import random
from typing import List, Dict, Any

import pandas as pd
import streamlit as st

# =========================================================
# モジュール読込（ai_core_plus → 失敗なら ai_core に自動フォールバック）
# =========================================================
try:
    from ai_core_plus import (
        INDUSTRY_WEIGHTS, CHANNEL_TIPS, GLOSSARY,
        humanize, smartify_goal, funnel_diagnosis, kpi_backsolve, explain_terms,
        budget_allocation, three_horizons_actions, concrete_examples, build_utm, dynamic_advice
    )
    USING_PLUS = True
except ModuleNotFoundError:
    from ai_core import (
        INDUSTRY_WEIGHTS, CHANNEL_TIPS, GLOSSARY,
        humanize, smartify_goal, funnel_diagnosis, kpi_backsolve,
        budget_allocation, three_horizons_actions, concrete_examples, build_utm
    )
    USING_PLUS = False

    # 互換：explain_terms が無ければ素通し
    def explain_terms(text: str, enabled: bool = True) -> str:
        return text

    # 互換：dynamic_advice が無ければ three_horizons_actions を利用した簡易版
    def dynamic_advice(inputs: Dict[str, Any], tone: str, variant_seed: int | None = None, emoji_rich: bool = True):
        rng = random.Random(variant_seed)
        has_with_reason = "with_reason" in three_horizons_actions.__code__.co_varnames
        acts = three_horizons_actions(inputs, tone, with_reason=True) if has_with_reason else three_horizons_actions(inputs, tone)
        head_opts = [
            "まずはここからいきましょう！一番のボトルネックに効く所です。",
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

# 実行計画ジェネレーター（What/How/Action）
try:
    from ai_core_plus import web_research_to_plan  # type: ignore
    HAS_PLAN = True
except Exception:
    HAS_PLAN = False
    def web_research_to_plan(*args, **kwargs) -> dict:
        return {"why": "", "sources": [], "today": [], "week": [], "month": []}

# チャネル別コピー（Web情報→コピー生成）
try:
    from ai_core_plus import web_research_to_copies  # type: ignore
    HAS_COPIES = True
except Exception:
    HAS_COPIES = False
    def web_research_to_copies(*args, **kwargs) -> dict:
        return {"sources": [], "keypoints": [], "copies": {}}

# three_horizons_actions が with_reason に対応していない場合に備えるヘルパー
def th_actions_safe(inputs: Dict[str, Any], tone: str, with_reason: bool = False):
    if "with_reason" in three_horizons_actions.__code__.co_varnames:
        return three_horizons_actions(inputs, tone, with_reason=with_reason)
    else:
        return three_horizons_actions(inputs, tone)

# =========================
# ページ設定（スマホ向け）
# =========================
st.set_page_config(page_title="集客コンサルAI Pro+", page_icon="🤝", layout="centered")
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
.badge { display:inline-block; padding:2px 8px; border-radius:999px; background:#eef2ff; color:#3730a3; font-size:12px; margin-left:8px; }
.copybox textarea { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }
</style>
""", unsafe_allow_html=True)

# =========================
# セッション初期化
# =========================
def ensure_session():
    st.session_state.setdefault("page", "input")   # input -> ad -> result
    st.session_state.setdefault("inputs", {})
    st.session_state.setdefault("is_paid", False)
    st.session_state.setdefault("ad_started_at", None)
    st.session_state.setdefault("tone", "やさしめ")
    st.session_state.setdefault("variant_seed", 0)
    st.session_state.setdefault("explain_terms", True)
    st.session_state.setdefault("friendly", True)
    st.session_state.setdefault("emoji_rich", True)

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

    st.session_state["explain_terms"] = st.checkbox("専門用語に解説を付ける", value=st.session_state["explain_terms"])
    st.session_state["friendly"] = st.checkbox("親しみやすさブースト", value=st.session_state["friendly"])
    st.session_state["emoji_rich"] = st.checkbox("絵文字ちょい多め", value=st.session_state["emoji_rich"])

# =========================
# ヘッダー
# =========================
st.title("🤝 集客コンサルAI Pro+")
cap = "やさしく、でも本格派。数値→計画→実行まで伴走します。"
if USING_PLUS:
    cap += ' <span class="badge">plus</span>'
st.caption(cap, unsafe_allow_html=True)

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
# 広告インタースティシャル（“確実に進む”安定版）
# =========================
def render_ad():
    if not st.session_state.inputs:
        goto("input")

    st.markdown('<span class="step">STEP 2</span> お知らせ（スポンサー）', unsafe_allow_html=True)
    st.markdown("結果の準備中…スポンサーからのお知らせをご覧ください。")

    ads = [
        {"title": "📣 SNS運用テンプレ100選", "desc": "今すぐ使える投稿ネタ集（無料）"},
        {"title": "🎯 小予算でも効く広告講座", "desc": "1日30分で学べる実践講座"},
        {"title": "🧰 無料KPIダッシュボード", "desc": "スプレッドシートで簡単管理"},
    ]
    random.shuffle(ads)
    for ad in ads:
        st.markdown(
            f"""<div class="ad"><strong>{ad["title"]}</strong><div>{ad["desc"]}</div></div>""",
            unsafe_allow_html=True
        )

    min_view = 3  # 秒
    if st.session_state.ad_started_at is None:
        st.session_state.ad_started_at = int(time.time())
        st.info(f"結果へ自動的に移動します… {min_view} 秒")
        st.rerun()

    elapsed = int(time.time() - st.session_state.ad_started_at)
    remain = max(0, min_view - elapsed)
    st.info(f"結果へ自動的に移動します… {remain} 秒")

    if st.button("広告を閉じて結果へ ▶", disabled=remain > 0):
        goto("result")

    if remain <= 0:
        goto("result")
    else:
        time.sleep(1)
        st.rerun()

# =========================
# チャネル別コピー生成（Web情報ベース）
# =========================
def render_channel_copies_section(inputs):
    st.markdown("### ✍️ チャネル別コピー（Web情報→そのまま使える複数案）")
    st.caption("最新のWeb記事から要点を抽出し、SNS/広告/メール/LPのコピーを5案ずつ自動生成します。")

    if not HAS_COPIES:
        st.info("コピー生成エンジンが見つかりません。`ai_core_plus.py` に `web_research_to_copies` を追加してください。")
        return

    with st.expander("検索条件（任意で調整）", expanded=True):
        default_query = f"{inputs.get('industry','')} {inputs.get('product','')}".strip()
        web_query = st.text_input("検索クエリ", value=default_query, key="copy_query")
        max_items = st.slider("最大取得件数", min_value=3, max_value=20, value=8, step=1, key="copy_max_items")
        extra_urls_str = st.text_area("追加で読み込みたいURL（改行区切り）", height=80, key="copy_extra_urls")
        tone_choice = st.selectbox("トーン", ["カジュアル","ビジネス","ユーモラス"], index=0, key="copy_tone")
        go = st.button("Webから収集→コピーを作る ▶", key="copy_go")

    if not go:
        return

    with st.spinner("Webから情報収集→コピー生成中..."):
        res = web_research_to_copies(
            query=web_query or default_query,
            product=inputs.get("product","サービス"),
            industry=inputs.get("industry","その他"),
            extra_urls=[u.strip() for u in (extra_urls_str.splitlines() if extra_urls_str else []) if u.strip()],
            max_items=max_items,
            tone=tone_choice
        )

    sources = res.get("sources", [])
    keypoints = res.get("keypoints", [])
    copies = res.get("copies", {})

    # 参照情報
    if sources:
        st.caption("参照情報（抜粋）：" + " / ".join(
            [f"[{s.get('title') or s.get('url')}]({s.get('url')})" for s in sources if s.get("url")]
        ))

    # キーポイントをタグ風に
    if keypoints:
        st.write("**抽出キーポイント（上位）**")
        cols = st.columns(6)
        for i, kp in enumerate(keypoints[:18]):
            with cols[i % 6]:
                st.markdown(f"<div class='badge' style='display:inline-block;margin:4px 0;'>{kp}</div>", unsafe_allow_html=True)

    # チャネルごとに5案表示＋選択保存
    st.markdown("---")
    st.write("**コピー一覧（各チャネル5案）**")
    selected_rows = []

    order = [
        "SNS/Twitter(X)", "SNS/Instagram", "SNS/LinkedIn",
        "広告/Google", "広告/Meta",
        "メール/件名", "メール/本文",
        "LP/ヒーロー",
    ]
    for ch in order:
        arr = copies.get(ch, [])
        if not arr:
            continue
        st.markdown(f"#### {ch}")
        for idx, text in enumerate(arr, start=1):
            with st.container():
                st.text_area(f"{ch} #{idx}", text, height=80, key=f"copy_{ch}_{idx}")
                c1, c2 = st.columns([1,6])
                with c1:
                    keep = st.checkbox("保存", key=f"save_{ch}_{idx}")
                with c2:
                    st.caption("※ 編集してから保存もOKです。")
                if keep:
                    selected_rows.append({"チャネル": ch, "案番号": idx, "コピー": st.session_state.get(f"copy_{ch}_{idx}", text)})

    # 保存・エクスポート
    st.markdown("---")
    if selected_rows:
        df = pd.DataFrame(selected_rows)
        st.dataframe(df, hide_index=True, use_container_width=True)
        st.download_button(
            "📥 選択したコピーをCSVで保存",
            df.to_csv(index=False).encode("utf-8-sig"),
            file_name="channel_copies.csv",
            mime="text/csv",
        )
    else:
        st.info("保存するコピーをチェックすると、ここに一覧とCSVダウンロードが出ます。")

# =========================
# 結果画面
# =========================
def render_result():
    if not st.session_state.inputs:
        goto("input")
    inputs = st.session_state.inputs
    tone = st.session_state.get("tone", "やさしめ")

    st.markdown('<span class="step">STEP 3</span> あなたへの具体提案', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔎 サマリー")
    st.write(f"- **業種**: {inputs.get('industry')}｜**地域**: {inputs.get('region')}")
    st.write(f"- **商品/サービス**: {inputs.get('product')}｜**ターゲット**: {inputs.get('target')}")
    st.write(f"- **目標**: {smartify_goal(inputs.get('goal',''))}")
    st.write(f"- **週予算**: {inputs.get('budget')}円｜**チャネル**: {', '.join(inputs.get('channels') or [])}")
    st.write(f"- **強み/弱み**: {inputs.get('strength')} / {inputs.get('weakness')}")
    st.markdown('</div>', unsafe_allow_html=True)

    # ========== Web情報 → 実行計画（What/How/Action を言い切る） ==========
    st.markdown("### ✅ Web情報をもとに『何を/どうやるか/どう測るか』を自動設計")
    if not HAS_PLAN:
        st.info("実行計画ジェネレーターが見つかりません。`ai_core_plus.py` に `web_research_to_plan` を追加してください。")
    else:
        with st.expander("検索条件（任意で調整）", expanded=True):
            default_query = f"{inputs.get('industry','')} {inputs.get('product','')}".strip()
            web_query = st.text_input("検索クエリ", value=default_query)
            max_items = st.slider("最大取得件数", min_value=3, max_value=20, value=8, step=1)
            extra_urls_str = st.text_area("追加で読み込みたいURL（改行区切り）", height=80, placeholder="")
            tone_choice = st.selectbox("トーン", ["カジュアル","ビジネス","ユーモラス"], index=0)
            plan_go = st.button("Webから収集→実行計画を作る ▶")

        if plan_go:
            with st.spinner("Webから情報収集→計画に落とし込み中..."):
                plan = web_research_to_plan(
                    query=web_query or default_query,
                    product=inputs.get("product","サービス"),
                    industry=inputs.get("industry","その他"),
                    extra_urls=[u.strip() for u in (extra_urls_str.splitlines() if extra_urls_str else []) if u.strip()],
                    max_items=max_items,
                    tone=tone_choice
                )

            # 情報源の表示
            if plan["sources"]:
                st.caption("参照情報（抜粋）：" + " / ".join(
                    [f"[{s.get('title','source')}]({s.get('url')})" for s in plan["sources"] if s.get("url")]
                ))

            def render_bucket(title, items):
                st.markdown(f"#### {title}")
                if not items:
                    st.write("- （該当なし）")
                    return
                for i, it in enumerate(items, start=1):
                    with st.container():
                        st.markdown(f"**{i}. {getattr(it, 'title', '')}**")
                        st.caption(f"なぜ：{getattr(it, 'why', '')}")
                        st.write("**やること（手順）**")
                        for step in getattr(it, "steps", []):
                            st.write("- " + step)
                        st.write(f"**KPI**：{getattr(it, 'kpi', '')}｜**目標**：{getattr(it, 'target', '')}｜**工数/コスト**：{getattr(it, 'effort', '')}")
                        with st.expander("リスクと手当て"):
                            st.write(f"- リスク：{getattr(it, 'risks', '')}")
                            st.write(f"- 手当て：{getattr(it, 'mitigation', '')}")
                        # コピペ用
                        src_urls = ", ".join([s.get("url") for s in plan["sources"] if s.get("url")])
                        txt = f"""{getattr(it, 'title', '')}
- WHY: {getattr(it, 'why', '')}
- STEPS: {", ".join(getattr(it, "steps", []))}
- KPI: {getattr(it, 'kpi', '')} / 目標: {getattr(it, 'target', '')}
- 工数/コスト: {getattr(it, 'effort', '')}
- 参考: {src_urls}"""
                        st.text_area("コピペ用", txt, height=120, key=f"plan_copy_{title}_{i}")

            render_bucket("今日やる（即効2〜3件）", plan.get("today", []))
            render_bucket("今週やる（積み上げ2件）", plan.get("week", []))
            render_bucket("今月やる（基盤2件）", plan.get("month", []))

    # --- チャネル別コピー生成（Web情報ベース） ---
    render_channel_copies_section(inputs)

    # ファネル診断
    diag = funnel_diagnosis(inputs)
    st.markdown("### ファネル診断（AARRR）")
    df_scores = pd.DataFrame([diag["scores"]]).T.reset_index()
    df_scores.columns = ["ファネル", "スコア(0-100)"]
    st.dataframe(df_scores, hide_index=True, use_container_width=True)
    st.info(humanize(f"ボトルネック：**{diag['bottleneck']}**。ここに効くタスクからやりましょう。", tone))

    # 親しみやすいダイナミック提案
    st.markdown("### 親しみやすいダイナミック提案")
    c1, c2 = st.columns([4,1])
    with c1:
        st.caption("※ ボトルネック・予算・業種を踏まえ、表現を毎回少し変えてご提案します。")
    with c2:
        if st.button("別の言い方で見る 🔄"):
            st.session_state['variant_seed'] += 1
            st.rerun()
    adv = dynamic_advice(
        inputs, tone,
        variant_seed=st.session_state.get('variant_seed',0),
        emoji_rich=st.session_state.get('emoji_rich', True)
    )
    st.info(adv["ヘッダー"])
    st.markdown("**今日やる（すぐ終わる2つ）**")
    for line in adv["今日やる"]:
        st.write("- " + explain_terms(line, st.session_state.get("explain_terms", True)))
    st.markdown("**今週やる**")
    for line in adv["今週やる"]:
        st.write("- " + explain_terms(line, st.session_state.get("explain_terms", True)))
    st.markdown("**今月やる**")
    for line in adv["今月やる"]:
        st.write("- " + explain_terms(line, st.session_state.get("explain_terms", True)))
    st.success(explain_terms(adv["ひとこと"], st.session_state.get("explain_terms", True)))

    # 3段階アクション（理由付き対応に自動フォールバック）
    st.markdown("### 今日/今週/今月の3段階アクション")
    acts = th_actions_safe(inputs, tone, with_reason=True)
    for h in ["今日やる", "今週やる", "今月やる"]:
        st.markdown(f"**{h}**")
        for line in acts.get(h, []):
            st.write("- " + explain_terms(line, st.session_state.get("explain_terms", True)))

    # 具体例（コピーテンプレ/トーク）
    st.markdown("### 具体例（コピーテンプレ/トーク）")
    ex = concrete_examples(inputs, tone)
    def getkey(d, k, default=""):
        return d[k] if k in d else default
    st.write("**SNS投稿例**：", explain_terms(getkey(ex, "SNS投稿", ""), st.session_state.get("explain_terms", True)))
    if getkey(ex, "SNSポイント"): st.caption(getkey(ex, "SNSポイント"))
    st.write("**広告文例**：", explain_terms(getkey(ex, "広告文", ""), st.session_state.get("explain_terms", True)))
    if getkey(ex, "広告ポイント"): st.caption(getkey(ex, "広告ポイント"))
    st.write("**LPヒーロー案**：", explain_terms(getkey(ex, "LPヒーロー", ""), st.session_state.get("explain_terms", True)))
    if getkey(ex, "LPポイント"): st.caption(getkey(ex, "LPポイント"))
    with st.expander("DMテンプレ / 電話トーク"):
        st.write("**DMテンプレ**：", explain_terms(getkey(ex, "DMテンプレ", ""), st.session_state.get("explain_terms", True)))
        if getkey(ex, "DMポイント"): st.caption(getkey(ex, "DMポイント"))
        st.write("**電話トーク**：", explain_terms(
