# streamlit_app.py
# -*- coding: utf-8 -*-
"""
集客コンサルAI（Stripe課金・会員化・ユーザー保存・動画広告・裏コマンド・**LLM搭載**）

このアプリは以下を満たします：
- 日本語UI：業種/目標/予算/地域/ペルソナで 7日間アクションプラン自動生成
- 入力 → **動画広告**（インタースティシャル）→ 結果 の3ステップ
- **無料/PRO（有料）**の差別化（PROは詳細チェックやAB設計など拡張）
- **Stripe Checkout** で決済 → 返却URLで検証し PRO 付与
- **Supabase** で会員化（ログイン/サインアップ）＆プラン保存
- **裏コマンド**：特定ボタンの**連続7タップ**で **7日間だけPRO解放**（ゲストはセッションのみ）
- **LLM搭載**：OpenAI（可）で“AIが考えた”プランを生成。失敗時は規則ベースに自動フォールバック。

【設定】.streamlit/secrets.toml に以下を定義してください：

[secrets]
# Stripe
STRIPE_SECRET_KEY = "sk_live_... または sk_test_..."
STRIPE_PUBLISHABLE_KEY = "pk_live_... または pk_test_..."
STRIPE_PRICE_ID = "price_..."
STRIPE_DOMAIN = "https://あなたのドメイン"      # 例: https://your-app.streamlit.app
STRIPE_SUCCESS_PATH = "/?paid=1"
STRIPE_CANCEL_PATH = "/?canceled=1"

# Supabase
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_ANON_KEY = "public anon key"

# LLM（任意：設定すればAI生成が有効に）
OPENAI_API_KEY = "sk-..."                     # OpenAI を使う場合
OPENAI_MODEL = "gpt-4o-mini"                  # 例
USE_LLM = true                                 # false で無効

# デモ用バックドア（本番は無効化推奨）
PRO_UNLOCK_CODE = "PRO-2025"

【Supabase 側の用意】/【Stripe 側の用意】はソース先頭コメント参照。
"""

# streamlit_app.py
# 集客コンサルAI（Persona Builder + LLM/ルールベース生成）
# - ペルソナは“かんたん作成”で構造化入力
# - 7日間プランは LLM（OpenAI）優先、失敗時はルールベースへ自動フォールバック
# - LLM有効化は .streamlit/secrets.toml に OPENAI_API_KEY を設定し、USE_LLM=true

from __future__ import annotations
import time, random, json
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import streamlit as st
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# ====== 設定 ======
st.set_page_config(page_title="集客AIコンサル", page_icon="📈", layout="centered")

JST = timezone(timedelta(hours=9))
def now_jst(): return datetime.now(tz=JST)

USE_LLM = bool(st.secrets.get("USE_LLM", False)) and st.secrets.get("OPENAI_API_KEY") is not None
OPENAI_MODEL = st.secrets.get("OPENAI_MODEL", "gpt-4o-mini")

# ====== スタイル ======
st.markdown("""
<style>
:root { --radius: 16px; }
.block-container { padding-top: 1rem; padding-bottom: 4.5rem; }
.card { border: 1px solid #eaeaea; border-radius: var(--radius); padding: 1rem 1.1rem; background: #fff; box-shadow: 0 2px 10px rgba(0,0,0,.03); }
.badge-required { display:inline-block; margin-left:.5rem; padding:.08rem .45rem; font-size:.75rem; font-weight:700; color:#b91c1c; background:#fee2e2; border:1px solid #fecaca; border-radius:999px; vertical-align:middle; }
.footer-cta { position: fixed; bottom: 8px; left: 0; right: 0; z-index: 9999; display: grid; place-items: center; }
.footer-cta-inner { background:#0ea5e9; color:#fff; font-weight:700; padding:.8rem 1.2rem; border-radius:999px; }
.validation-msg { color:#b91c1c; font-size:0.9rem; margin-top:0.25rem; }
.preview { border:1px dashed #cbd5e1; border-radius:12px; padding:10px 12px; background:#fafafa; }
.help { color:#64748b; font-size:.85rem; }
</style>
""", unsafe_allow_html=True)

# ====== データ ======
INDUSTRY_HINTS = {
    "飲食":  {"tags": ["駅近", "仕事帰り", "女子会", "禁煙", "家族連れ", "コスパ", "映え", "予約即時", "口コミ重視"]},
    "美容・サロン": {"tags": ["時短", "ダメージケア", "学生割", "在宅ワーク", "ホットペッパー", "平日昼", "指名", "口コミ重視"]},
    "クリニック": {"tags": ["痛みが不安", "女性医師", "待ち時間短縮", "土日OK", "オンライン予約", "駅近", "清潔感"]},
    "フィットネス": {"tags": ["体験重視", "時短30分", "ダイエット", "ヨガ", "パーソナル", "仕事前", "仕事後"]},
    "EC/物販": {"tags": ["ギフト", "限定色", "レビュー重視", "お急ぎ", "返品無料", "SNS紹介", "セット割"]},
    "B2B":   {"tags": ["決裁者目線", "ROI重視", "比較検討", "資料DL", "導入事例", "セミナー", "トライアル"]},
    "不動産": {"tags": ["駅近", "築浅", "子育て", "投資用", "賃貸", "購入", "内見即時"]},
    "教育":  {"tags": ["受験対策", "オンライン", "個別指導", "送迎あり", "短期集中", "初めて"]},
    "その他": {"tags": ["口コミ重視", "即時", "短納期", "価格重視", "品質重視"]},
}

PRESETS = {
    "飲食": [
        {"name":"仕事帰りのOL","age":"25-34","gender":"女性","role":"事務職","income":"300-500万",
         "interests":["女子会","映え"],"pains":["並びたくない","失敗したくない"],"triggers":["SNSの写真","友人の口コミ"],
         "channels":["Instagram","Googleマップ"],"time":["平日夜"]},
        {"name":"子連れファミリー","age":"30-44","gender":"男女","role":"会社員","income":"500-800万",
         "interests":["家族で安心","禁煙"],"pains":["子供連れで入りづらい"],"triggers":["口コミ","クーポン"],
         "channels":["Googleマップ","LINE"],"time":["土日昼"]},
    ],
    "B2B": [
        {"name":"情報シスMgr","age":"35-49","gender":"男性","role":"情報システム","income":"800-1200万",
        "interests":["コスト削減","安定稼働"],"pains":["比較の手間"],"triggers":["事例","価格表"],
        "channels":["LinkedIn","ウェビナー"],"time":["平日昼"]},
    ]
}

# ====== 生成ロジック（ルールベース & LLM） ======
DEFAULT_CHANNELS = ["Googleビジネスプロフィール","Instagramリール","LINE公式","検索広告(指名)"]

def pick_channels(industry: str, budget: int) -> List[str]:
    guess = {
        "飲食": ["Googleマップ最適化","Instagramリール","LINE公式","食べログ広告","検索広告(指名)"],
        "美容・サロン": ["Instagramストーリーズ","ホットペッパー","LINE予約","TikTok UGC","検索広告(指名)"],
        "クリニック": ["検索広告(症状)","ローカルSEO","LP最適化","LINE問診","Googleマップ最適化"],
        "フィットネス": ["YouTubeショート","体験会LP","Meta(リード)","LINE予約","検索広告(指名)"],
        "EC/物販": ["Meta(カタログ)","Instagramショップ","リール広告","レビュー収集","検索広告(指名)"],
        "B2B": ["ウェビナー","LinkedIn広告","ホワイトペーパー","メールナーチャリング","検索広告(非指名)"],
    }.get(industry, DEFAULT_CHANNELS)
    if budget < 50000: return guess[:3]
    if budget < 200000: return guess[:4]
    return list(dict.fromkeys(guess + ["TikTok UGC","YouTubeショート"]))[:5]

def estimate_kpi(industry: str, budget: int) -> str:
    if industry == "B2B":
        lo, hi = max(1, budget//9000), max(1, budget//4000)
        return f"商談 {lo}〜{hi}件（目安）"
    lo, hi = max(1, budget//2000), max(1, budget//800)
    unit = "購入" if industry == "EC/物販" else "件"
    return f"{lo}〜{hi}{unit}（目安）"

def human_money(n:int)->str:
    try: return f"{int(n):,}円"
    except: return str(n)

def build_day_plan(day:int, channels:List[str], pro:bool)->Dict:
    skeleton = ["市場/競合リサーチ・カスタマージャーニー設計","計測設定（GA4/タグ/電話計測）","クリエイティブ作成（画像/動画/コピー）",
                "LP改善とABテスト設計","広告出稿・予算配分・除外設定","UGC/口コミ獲得・SNS運用","分析・次週計画・伸びしろ抽出"]
    today = ", ".join(random.sample(channels, min(3, len(channels))))
    plan = {"day": f"Day {day}", "theme": skeleton[(day-1)%len(skeleton)], "focus": today,
            "tasks": [f"{today} を中心に実施","KPI ダッシュボード更新","翌日の改善点をメモ"]}
    if pro:
        plan["checks"] = ["計測：CV/UTM/電話計測","品質：関連度/LP速度/ファーストビュー","コスト：入札・除外KW"]
        plan["ab"] = ["見出し A/B（ベネ vs 社会証明）","CTA（今すぐ vs 無料で試す）"]
    return plan

def rule_based_markdown(industry: str, goal: str, budget: int, region: str, persona: str, pro: bool) -> str:
    channels = pick_channels(industry, budget)
    kpi = estimate_kpi(industry, budget)
    days = [build_day_plan(i, channels, pro) for i in range(1,8)]
    md = [f"# 7日間アクションプラン（{'PRO' if pro else 'FREE'}）\n",
          "## 要約", f"- 業種: {industry}", f"- 目標: {goal}", f"- 予算: {human_money(budget)}",
          f"- 地域: {region}", f"- ペルソナ: {persona}", f"- 主要チャネル: {', '.join(channels)}", f"- KPI（目安）: {kpi}", ""]
    md += ["## 日別タスク"]
    for d in days:
        md += [f"### {d['day']}｜{d['theme']}", f"- フォーカス: {d['focus']}"]
        for t in d["tasks"]: md += [f"  - {t}"]
        if d.get("checks"): md += ["  - チェック:"] + [f"    - {c}" for c in d["checks"]]
        if d.get("ab"): md += ["  - ABテスト:"] + [f"    - {a}" for a in d["ab"]]
        md += [""]
    return "\n".join(md)

def llm_markdown(industry: str, goal: str, budget: int, region: str, persona: str, pro: bool) -> str:
    if not (USE_LLM and OpenAI and st.secrets.get("OPENAI_API_KEY")):
        raise RuntimeError("LLM未設定")
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
    sys = (
        "日本語のシニアグロースコンサルとして、7日間の集客アクションプランを提案。"
        "現実的な媒体設計・KPI・チェック項目込み。"
        "出力はJSONのみ: summary{industry,goal,budget,region,persona,channels[],kpi}, days[{day,theme,focus,tasks[],checks[],ab[]}]."
    )
    user = {"industry":industry,"goal":goal,"budget":budget,"region":region,"persona":persona,"detail_level":"pro" if pro else "free"}
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role":"system","content":sys},{"role":"user","content":json.dumps(user, ensure_ascii=False)}],
            temperature=0.7,
            response_format={"type":"json_object"},
        )
        data = json.loads(resp.choices[0].message.content)
    except Exception as e:
        raise RuntimeError(f"LLM生成に失敗: {e}")

    s = data.get("summary", {})
    dlist = data.get("days", [])
    md = [f"# 7日間アクションプラン（{'PRO' if pro else 'FREE'}・LLM生成）\n",
          "## 要約",
          f"- 業種: {s.get('industry', industry)}",
          f"- 目標: {s.get('goal', goal)}",
          f"- 予算: {human_money(s.get('budget', budget))}",
          f"- 地域: {s.get('region', region)}",
          f"- ペルソナ: {s.get('persona', persona)}",
          f"- 主要チャネル: {', '.join(s.get('channels', []))}",
          f"- KPI: {s.get('kpi', '')}", ""]
    md += ["## 日別タスク"]
    for d in dlist:
        md += [f"### {d.get('day','Day ?')}｜{d.get('theme','')}", f"- フォーカス: {d.get('focus','')}"]
        for t in d.get("tasks", []): md += [f"  - {t}"]
        if pro and d.get("checks"): md += ["  - チェック:"] + [f"    - {x}" for x in d.get("checks", [])]
        if pro and d.get("ab"): md += ["  - ABテスト:"] + [f"    - {x}" for x in d.get("ab", [])]
        md += [""]
    return "\n".join(md)

# ====== Persona Builder ======
def persona_builder(industry: str) -> str:
    st.markdown("#### ペルソナ<span class='badge-required'>必須</span>", unsafe_allow_html=True)
    with st.expander("かんたん作成（推奨）", expanded=True):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("呼び名（例：仕事帰りのOL）", value="")
        age = c2.selectbox("年齢帯", ["", "18-24","25-34","35-44","45-54","55-64","65+"], index=0)
        gender = c3.selectbox("性別", ["","女性","男性","男女","その他"], index=0)

        role = st.text_input("職業・役割（例：事務職 / 情シス / 主婦 など）", value="")
        c4, c5 = st.columns(2)
        income = c4.selectbox("年収帯", ["","〜300万","300-500万","500-800万","800-1200万","1200万+"])
        timeband = c5.multiselect("行動時間帯", ["平日朝","平日昼","平日夜","土日昼","土日夜"])

        # タグ（業種に応じたヒント）
        tags = INDUSTRY_HINTS.get(industry, INDUSTRY_HINTS["その他"])["tags"]
        st.caption("関連タグ"); interests = st.multiselect("関心事", list(sorted(set(tags+["価格重視","品質重視","時短","安心","口コミ重視","限定/レア"]))))
        pains = st.text_area("悩み・不安（改行区切り）", placeholder="例：並びたくない\n失敗したくない")
        triggers = st.multiselect("意思決定のきっかけ", ["口コミ","SNSの写真","クーポン","ランキング","事例","比較表","価格"])
        channels = st.multiselect("よく見るチャネル", ["Googleマップ","Instagram","LINE","YouTube","TikTok","Facebook","LinkedIn","メール"])

        # プリセット
        with st.popover("業種プリセットを読み込む"):
            options = PRESETS.get(industry, [])
            if not options:
                st.caption("この業種のプリセットは準備中です。")
            for i, p in enumerate(options, 1):
                if st.button(f"プリセット {i}: {p['name']}"):
                    st.session_state.update({
                        "pb_name": p["name"], "pb_age": p["age"], "pb_gender": p["gender"], "pb_role": p["role"],
                        "pb_income": p["income"], "pb_time": p["time"],
                    })
                    st.rerun()

        # LLMで自動草案（任意）
        if USE_LLM and OpenAI:
            if st.button("AIに自動作成してもらう（任意）"):
                client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
                prompt = {"industry": industry, "tone": "日本語", "fields": ["name","age","gender","role","income","interests","pains","triggers","channels","time"]}
                try:
                    resp = client.chat.completions.create(
                        model=OPENAI_MODEL,
                        messages=[{"role":"system","content":"日本語で簡潔なJSONを返す"},
                                  {"role":"user","content":json.dumps(prompt, ensure_ascii=False)}],
                        response_format={"type":"json_object"},
                        temperature=0.6,
                    )
                    data = json.loads(resp.choices[0].message.content)
                    st.session_state.update({
                        "pb_name": data.get("name",""),
                        "pb_age": data.get("age",""),
                        "pb_gender": data.get("gender",""),
                        "pb_role": data.get("role",""),
                        "pb_income": data.get("income",""),
                        "pb_time": data.get("time", []),
                    })
                    st.success("AIで下書きを入れました。内容は編集できます。")
                except Exception as e:
                    st.error(f"AI生成に失敗: {e}")

        # 復元
        name = st.session_state.get("pb_name", name)
        age = st.session_state.get("pb_age", age)
        gender = st.session_state.get("pb_gender", gender)
        role = st.session_state.get("pb_role", role)
        income = st.session_state.get("pb_income", income)
        timeband = st.session_state.get("pb_time", timeband)

        preview = f"""
**{name or '（呼び名未入力）'}** / {age or '年齢不明'} / {gender or '性別不明'}  
- 役割: {role or '不明'} / 年収: {income or '不明'} / 行動時間帯: {', '.join(timeband) or '不明'}  
- 関心: {', '.join(interests) or '—'}  
- 悩み: {pains.replace('\n', ' / ') or '—'}  
- きっかけ: {', '.join(triggers) or '—'}  
- 見るチャネル: {', '.join(channels) or '—'}
"""
        st.markdown("<div class='preview'>"+preview+"</div>", unsafe_allow_html=True)

        persona_text = f"{age or ''}{('・'+gender) if gender else ''}、{role or '—'}。関心は「{', '.join(interests) or '—'}」。悩みは「{pains.replace('\n',' / ') or '—'}」。意思決定のきっかけは「{', '.join(triggers) or '—'}」。主に「{', '.join(channels) or '—'}」を見て、{', '.join(timeband) or '—'}に行動。"

    st.markdown("**ペルソナ要約（編集可）**")
    persona = st.text_area("", value=persona_text, label_visibility="collapsed")

    if not persona.strip():
        st.markdown("<div class='validation-msg'>⚠️ ペルソナ情報を入力してください（上のかんたん作成を使うと早いです）</div>", unsafe_allow_html=True)

    return persona

# ====== 本編 ======
st.title("📈 集客コンサルAI")
st.caption("業種・目標・予算・地域・ペルソナを入れるだけ。7日間の具体アクションを自動生成。")

if "step" not in st.session_state: st.session_state.step = "input"
if "form_data" not in st.session_state: st.session_state.form_data = {}
if "plan_md" not in st.session_state: st.session_state.plan_md = ""

if st.session_state.step == "input":
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("業種<span class='badge-required'>必須</span>", unsafe_allow_html=True)
            industry = st.selectbox("", ["飲食","美容・サロン","クリニック","フィットネス","EC/物販","B2B","不動産","教育","その他"], index=0, label_visibility="collapsed")
        with c2:
            st.markdown("目標<span class='badge-required'>必須</span>", unsafe_allow_html=True)
            goal = st.selectbox("", ["予約","問い合わせ","資料請求","売上","リード獲得"], label_visibility="collapsed")

        c3, c4 = st.columns(2)
        with c3:
            st.markdown("月間予算（円）<span class='badge-required'>必須</span>", unsafe_allow_html=True)
            budget = st.number_input("", min_value=10000, step=10000, value=100000, label_visibility="collapsed")
        with c4:
            st.markdown("地域（市区町村/エリア）<span class='badge-required'>必須</span>", unsafe_allow_html=True)
            region = st.text_input("", value="東京都内", label_visibility="collapsed")
        st.markdown('</div>', unsafe_allow_html=True)

        # Persona
        persona = persona_builder(industry)

        # 未入力チェック
        missing = []
        if not industry: missing.append("業種")
        if not goal: missing.append("目標")
        if not budget: missing.append("予算")
        if not region: missing.append("地域")
        if not persona.strip(): missing.append("ペルソナ")
        disabled = len(missing) > 0

        # CTAボタン
        if st.button("7日間プランを作成", use_container_width=True, disabled=disabled):
            st.session_state.form_data = {"industry":industry,"goal":goal,"budget":int(budget),"region":region,"persona":persona}
            st.session_state.ad_started_at = time.time(); st.session_state.step = "ad"; st.experimental_rerun()

        # 押せるフッターCTA
        st.markdown("<div class='footer-cta'><a href='?cta=1'><div class='footer-cta-inner'>無料で今すぐ作成 ▶</div></a></div>", unsafe_allow_html=True)
        q = st.query_params
        if q.get("cta") == "1":
            if disabled:
                st.toast(f"未入力: {', '.join(missing)}", icon="⚠️")
            else:
                st.session_state.form_data = {"industry":industry,"goal":goal,"budget":int(budget),"region":region,"persona":persona}
                st.session_state.ad_started_at = time.time(); st.session_state.step = "ad"
                st.query_params.clear(); st.experimental_rerun()

elif st.session_state.step == "ad":
    st.header("少々お待ちください…結果を準備中")
    st.caption("スポンサー動画が流れます。数秒後に結果ページへ進めます。")
    st.video(random.choice(["https://www.w3schools.com/html/mov_bbb.mp4","https://www.w3schools.com/html/movie.mp4"]))

    elapsed = int(time.time() - (st.session_state.ad_started_at or time.time()))
    remain = max(0, 6 - elapsed)
    btn_label = "結果へ進む" if remain == 0 else f"{remain}秒後に進む"
    if st.button(btn_label, use_container_width=True, disabled=(remain>0)):
        d = st.session_state.form_data
        pro = True  # PRO相当の詳細版（必要に応じてフラグで分岐）
        if USE_LLM and OpenAI:
            try:
                st.session_state.plan_md = llm_markdown(d["industry"], d["goal"], d["budget"], d["region"], d["persona"], pro)
            except Exception:
                st.session_state.plan_md = rule_based_markdown(d["industry"], d["goal"], d["budget"], d["region"], d["persona"], pro)
        else:
            st.session_state.plan_md = rule_based_markdown(d["industry"], d["goal"], d["budget"], d["region"], d["persona"], pro)
        st.session_state.step = "result"; st.experimental_rerun()
    if remain>0:
        time.sleep(1); st.experimental_rerun()

else:
    md = st.session_state.plan_md
    if not md: st.warning("先に入力から開始してください。"); st.stop()
    st.subheader("✅ 7日間アクションプラン")
    st.markdown(md)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("条件を変えて再作成", use_container_width=True):
            st.session_state.step = "input"; st.experimental_rerun()
    with col2:
        st.download_button("Markdown をダウンロード", data=md.encode("utf-8"), file_name="7day_plan.md", mime="text/markdown", use_container_width=True)
