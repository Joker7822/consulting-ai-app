# streamlit_app.py
# -*- coding: utf-8 -*-
"""
集客コンサルAI（Stripe課金・会員化・ユーザー保存・動画広告・裏コマンド対応）

このアプリは以下を満たします：
- 日本語UI：業種/目標/予算/地域/ペルソナで 7日間アクションプラン自動生成
- 入力 → **動画広告**（インタースティシャル）→ 結果 の3ステップ
- **無料/PRO（有料）**の差別化（PROは詳細チェックやAB設計など拡張）
- **Stripe Checkout** で決済 → 返却URLで検証し PRO 付与
- **Supabase** で会員化（ログイン/サインアップ）＆プラン保存
- **裏コマンド（イースターエッグ）**：特定ボタンの**連続7タップ**で **7日間だけPRO解放**
  - ログイン済み=Supabaseの `profiles.pro_until` に期限を書き込み
  - 未ログイン（ゲスト）=セッション内のみ有効
- スマホに最適化した UI

【設定】.streamlit/secrets.toml に以下を定義してください：

[secrets]
# Stripe
STRIPE_SECRET_KEY = "sk_live_... または sk_test_..."
STRIPE_PUBLISHABLE_KEY = "pk_live_... または pk_test_..."
STRIPE_PRICE_ID = "price_..."                # サブスク/一括いずれも可
STRIPE_DOMAIN = "https://あなたのドメイン"      # 例: https://your-app.streamlit.app
STRIPE_SUCCESS_PATH = "/?paid=1"
STRIPE_CANCEL_PATH = "/?canceled=1"

# Supabase
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_ANON_KEY = "public anon key"

# デモ用バックドア（本番は無効化推奨）
PRO_UNLOCK_CODE = "PRO-2025"

【Supabase 側の用意】
- Auth：Email/Password（または Google/OAuth）を有効化
- Table: profiles(
    id uuid pk,
    email text unique,
    created_at timestamptz default now(),
    stripe_customer_id text,
    pro boolean default false,
    pro_until timestamptz  -- ★ 裏コマンド用の期限
  )
- Table: plans(id bigserial pk, user_id uuid references profiles(id), created_at timestamptz default now(), form jsonb, plan_md text)
- RLS: profiles は auth.uid() = id に限定、plans は user_id = auth.uid() のみ読書き可能

【Stripe 側の用意】
- 商品/PRICE を作成（例：月額プランや買い切り）
- Checkout の成功URL / キャンセルURL を secrets で指定
- Webhook を別途 Cloud Functions などに用意できると堅牢（本コードは戻り URL で session を検証する方式）
"""

from __future__ import annotations
import os
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import streamlit as st

# 追加ライブラリ（requirements.txt に追記）
# streamlit
# stripe==7.*
# supabase==2.*
import stripe
from supabase import create_client, Client

# ---------------------------
# ページ設定 & CSS（スマホ向け）
# ---------------------------
st.set_page_config(
    page_title="集客コンサルAI",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)

MOBILE_CSS = """
<style>
:root { --radius: 16px; }
.block-container { padding-top: 1rem; padding-bottom: 3.5rem; }
.stButton>button { border-radius: var(--radius); padding: 0.9rem 1.1rem; font-weight: 700; }
.card { border: 1px solid #eaeaea; border-radius: var(--radius); padding: 1rem 1.1rem; background: #fff; box-shadow: 0 2px 10px rgba(0,0,0,.03); }
.ad { border: 1px dashed #cfcfcf; border-radius: var(--radius); padding: .6rem; background: #fffdfa; }
.ad small { color:#888; }
.footer-cta { position: fixed; bottom: 8px; left: 0; right: 0; z-index: 9999; display: grid; place-items: center; }
.footer-cta > div { background:#0ea5e9; color:#fff; font-weight:700; padding:.8rem 1.2rem; border-radius:999px; }
.hidden { color: transparent; user-select: none; }
</style>
"""
st.markdown(MOBILE_CSS, unsafe_allow_html=True)

# ---------------------------
# Secrets / 定数
# ---------------------------
PRO_UNLOCK_CODE = st.secrets.get("PRO_UNLOCK_CODE", "PRO-2025")
AD_MIN_SECONDS = 6

# Stripe
STRIPE_SECRET_KEY = st.secrets.get("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = st.secrets.get("STRIPE_PUBLISHABLE_KEY")
STRIPE_PRICE_ID = st.secrets.get("STRIPE_PRICE_ID")
STRIPE_DOMAIN = st.secrets.get("STRIPE_DOMAIN", "")
STRIPE_SUCCESS_PATH = st.secrets.get("STRIPE_SUCCESS_PATH", "/")
STRIPE_CANCEL_PATH = st.secrets.get("STRIPE_CANCEL_PATH", "/")
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Supabase
SUPABASE_URL = st.secrets.get("SUPABASE_URL")
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY")
sb: Client | None = None
if SUPABASE_URL and SUPABASE_ANON_KEY:
    sb = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

# ---------------------------
# セッション初期化
# ---------------------------
if "step" not in st.session_state:
    st.session_state.step = "input"  # input -> ad -> result
if "form_data" not in st.session_state:
    st.session_state.form_data = {}
if "plan_md" not in st.session_state:
    st.session_state.plan_md = ""
if "tier" not in st.session_state:
    st.session_state.tier = "free"  # free|pro
if "ad_started_at" not in st.session_state:
    st.session_state.ad_started_at = None
if "user" not in st.session_state:
    st.session_state.user = None  # {id, email, pro, pro_until}
# 裏コマンド用カウンタ
if "secret_taps" not in st.session_state:
    st.session_state.secret_taps = 0
if "secret_start" not in st.session_state:
    st.session_state.secret_start = None  # epoch seconds

# ---------------------------
# ユーティリティ
# ---------------------------
def human_money(n: int) -> str:
    try:
        return f"{int(n):,}円"
    except Exception:
        return str(n)

JST = timezone(timedelta(hours=9))

def now_jst():
    return datetime.now(tz=JST)

# 簡易コピー/プラン生成
INDUSTRY_HINTS: Dict[str, Dict] = {
    "飲食": {"channels": ["Googleビジネスプロフィール","Instagramリール","LINE公式","食べログ/ぐるなび広告"], "kpi": "来店予約"},
    "美容・サロン": {"channels": ["Instagram/ストーリーズ","ホットペッパー","LINE予約","TikTok UGC"], "kpi": "予約数"},
    "クリニック": {"channels": ["検索広告(症状)","ローカルSEO","LP最適化","LINE問診"], "kpi": "初診予約"},
    "フィットネス": {"channels": ["YouTubeショート","体験会LP","Meta(リード)","LINE予約"], "kpi": "体験申込"},
    "EC/物販": {"channels": ["Meta(カタログ)","Instショップ","リール広告","レビュー収集"], "kpi": "購入"},
    "B2B": {"channels": ["ウェビナー","LinkedIn広告","WP/LP","ナーチャリング"], "kpi": "商談"},
}
DEFAULT_CHANNELS = ["Googleビジネスプロフィール","Instagramリール","LINE公式","検索広告(指名)"]

def pick_channels(industry: str, budget: int) -> List[str]:
    base = INDUSTRY_HINTS.get(industry, {}).get("channels", DEFAULT_CHANNELS)
    if budget < 50000:
        return base[:3]
    elif budget < 200000:
        return base[:4]
    else:
        extra = ["YouTubeショート","TikTok UGC","Meta(リード)"]
        return list(dict.fromkeys(base + extra))[:5]

def estimate_kpi(industry: str, budget: int) -> str:
    if industry == "B2B":
        low, high = max(1, budget//9000), max(1, budget//4000)
        return f"商談 {low}〜{high}件（目安）"
    else:
        low, high = max(1, budget//2000), max(1, budget//800)
        unit = "購入" if industry == "EC/物販" else "件"
        return f"{low}〜{high}{unit}（目安）"

def copy_examples(goal: str, persona: str, region: str) -> Dict[str, List[str]]:
    pain = "悩みを最短で解決" if goal in ("予約","問い合わせ","資料請求") else "今だけお得"
    return {
        "headline": [f"{region}で{goal}なら今がチャンス", f"{persona[:12]}向け｜{pain}", "初めてでも安心のサポート"],
        "primary": [f"{region}で探している{persona}の方へ。今が最適なご提案です。","スマホ30秒で完了。ご相談は無料。","口コミで選ばれています。まずはチェック。"],
        "cta": ["無料で試す","予約する","相談する"],
    }

def build_day_plan(day: int, channels: List[str], pro: bool) -> Dict:
    skeleton = [
        "市場/競合リサーチ・カスタマージャーニー設計",
        "計測設定（GA4/タグ/電話計測）",
        "クリエイティブ作成（画像/動画/コピー）",
        "LP改善とABテスト設計",
        "広告出稿・予算配分・除外設定",
        "UGC/口コミ獲得・SNS運用",
        "分析・次週計画・伸びしろ抽出",
    ]
    today = ", ".join(random.sample(channels, min(3, len(channels))))
    plan = {
        "day": f"Day {day}",
        "theme": skeleton[(day-1)%len(skeleton)],
        "focus": today,
        "tasks": [f"{today} を中心に実施","KPI ダッシュボード更新","翌日の改善点をメモ"],
    }
    if pro:
        plan["checks"] = ["計測：CV/UTM/電話計測","品質：関連度/LP速度/ファーストビュー","コスト：入札・除外KW"]
        plan["ab"] = ["見出し A/B（ベネ vs 社会証明）","CTA（今すぐ vs 無料で試す）"]
    return plan

def generate_plan(industry: str, goal: str, budget: int, region: str, persona: str, pro: bool) -> str:
    channels = pick_channels(industry, budget)
    kpi = estimate_kpi(industry, budget)
    copies = copy_examples(goal, persona, region)
    days = [build_day_plan(i, channels, pro) for i in range(1,8)]
    md = [f"# 7日間アクションプラン（{'PRO' if pro else 'FREE'}）\n"]
    md += ["## 要約", f"- 業種: {industry}", f"- 目標: {goal}", f"- 予算: {human_money(budget)}",
           f"- 地域: {region}", f"- ペルソナ: {persona}", f"- 主要チャネル: {', '.join(channels)}",
           f"- KPI（目安）: {kpi}", ""]
    md += ["## コピー例"]
    md += [f"- 見出し: {h}" for h in copies["headline"]]
    md += [f"- 本文: {p}" for p in copies["primary"]]
    md += ["- CTA: " + " / ".join(copies["cta"]), ""]
    md += ["## 日別タスク"]
    for d in days:
        md += [f"### {d['day']}｜{d['theme']}", f"- フォーカス: {d['focus']}"]
        for t in d["tasks"]:
            md += [f"  - {t}"]
        if d.get("checks"):
            md += ["  - チェック:"] + [f"    - {c}" for c in d["checks"]]
        if d.get("ab"):
            md += ["  - ABテスト:"] + [f"    - {a}" for a in d["ab"]]
        md += [""]
    return "\n".join(md)

# ---------------------------
# 動画広告
# ---------------------------
VIDEO_ADS = [
    "https://www.w3schools.com/html/mov_bbb.mp4",
    "https://www.w3schools.com/html/movie.mp4",
]

def show_video_ad():
    st.markdown("<div class='ad'><small>スポンサー動画</small>", unsafe_allow_html=True)
    st.video(random.choice(VIDEO_ADS))
    st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------
# 認証（Supabase）とPRO状態の同期
# ---------------------------
def ensure_profile(email: str, user_id: str):
    if not sb:
        return {"id": user_id, "email": email, "pro": False, "pro_until": None}
    sb.table("profiles").upsert({"id": user_id, "email": email}).execute()
    res = sb.table("profiles").select("id,email,pro,pro_until,stripe_customer_id").eq("id", user_id).single().execute()
    return res.data

def refresh_pro_status_from_server():
    """profiles.pro / pro_until を見て tier を更新。期限切れなら free に戻す。"""
    if not (sb and st.session_state.user and st.session_state.user.get("id") not in (None, "guest")):
        return
    try:
        uid = st.session_state.user["id"]
        res = sb.table("profiles").select("pro, pro_until").eq("id", uid).single().execute()
        pro = bool(res.data.get("pro"))
        pro_until = res.data.get("pro_until")
        if pro_until:
            try:
                until_dt = datetime.fromisoformat(pro_until.replace("Z", "+00:00")).astimezone(JST)
                if until_dt > now_jst():
                    pro = True
                else:
                    sb.table("profiles").update({"pro": False}).eq("id", uid).execute()
            except Exception:
                pass
        st.session_state.tier = "pro" if pro else "free"
        st.session_state.user["pro"] = pro
        st.session_state.user["pro_until"] = pro_until
    except Exception:
        pass

def auth_ui():
    if not sb:
        st.info("Supabase未設定のため、ゲストとして利用します。左側の『PRO購入』から決済可能です。")
        if st.session_state.get("user") is None:
            st.session_state.user = {"id": "guest", "email": "guest@example.com", "pro": False, "pro_until": None}
        return

    with st.expander("ログイン / 新規登録", expanded=st.session_state.get("user") is None):
        tab_login, tab_signup = st.tabs(["ログイン", "新規登録"])
        with tab_login:
            email = st.text_input("メールアドレス", key="login_email")
            password = st.text_input("パスワード", type="password", key="login_pw")
            if st.button("ログイン"):
                try:
                    auth = sb.auth.sign_in_with_password({"email": email, "password": password})
                    prof = ensure_profile(email, auth.user.id)
                    st.session_state.user = prof
                    refresh_pro_status_from_server()
                    st.success("ログインしました")
                except Exception as e:
                    st.error(f"ログインに失敗: {e}")
        with tab_signup:
            email = st.text_input("メールアドレス", key="signup_email")
            password = st.text_input("パスワード", type="password", key="signup_pw")
            if st.button("新規登録"):
                try:
                    auth = sb.auth.sign_up({"email": email, "password": password})
                    prof = ensure_profile(email, auth.user.id)
                    st.session_state.user = prof
                    refresh_pro_status_from_server()
                    st.success("登録しました。ログイン済みです。")
                except Exception as e:
                    st.error(f"登録に失敗: {e}")

# ---------------------------
# Stripe 決済
# ---------------------------
def create_checkout_session(email: str | None = None):
    if not STRIPE_PRICE_ID or not STRIPE_SECRET_KEY or not STRIPE_DOMAIN:
        st.error("Stripeの設定が不足しています（PRICE/SECRET/DOMAIN）")
        return
    success_url = f"{STRIPE_DOMAIN}{STRIPE_SUCCESS_PATH}?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{STRIPE_DOMAIN}{STRIPE_CANCEL_PATH}"
    try:
        session = stripe.checkout.Session.create(
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription" if STRIPE_PRICE_ID.startswith("price_") else "payment",
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=email,
            automatic_tax={"enabled": False},
        )
        return session
    except Exception as e:
        st.error(f"Checkout作成に失敗: {e}")
        return None

def verify_checkout_and_mark_pro(session_id: str):
    if not session_id or not STRIPE_SECRET_KEY:
        return False
    try:
        sess = stripe.checkout.Session.retrieve(session_id)
        paid = (sess.get("payment_status") == "paid") or (sess.get("status") == "complete")
        if paid:
            if sb and st.session_state.user and st.session_state.user.get("id") not in (None, "guest"):
                uid = st.session_state.user["id"]
                sb.table("profiles").update({
                    "pro": True,
                    "stripe_customer_id": sess.get("customer"),
                    "pro_until": None,
                }).eq("id", uid).execute()
                st.session_state.user["pro"] = True
                st.session_state.user["pro_until"] = None
            st.session_state.tier = "pro"
            return True
        return False
    except Exception as e:
        st.error(f"決済検証に失敗: {e}")
        return False

# ---------------------------
# 裏コマンド（7タップで7日間PRO）
# ---------------------------
def handle_secret_tap():
    now = time.time()
    if st.session_state.secret_start is None or (now - st.session_state.secret_start) > 20:
        st.session_state.secret_start = now
        st.session_state.secret_taps = 0
    st.session_state.secret_taps += 1
    if st.session_state.secret_taps >= 7:
        expires_at = now_jst() + timedelta(days=7)
        st.session_state.tier = "pro"
        if st.session_state.user is None:
            st.session_state.user = {"id": "guest", "email": "guest@example.com", "pro": True, "pro_until": expires_at.isoformat()}
        else:
            st.session_state.user["pro"] = True
            st.session_state.user["pro_until"] = expires_at.isoformat()
        try:
            if sb and st.session_state.user and st.session_state.user.get("id") not in (None, "guest"):
                uid = st.session_state.user["id"]
                sb.table("profiles").update({"pro": True, "pro_until": expires_at.isoformat()}).eq("id", uid).execute()
        except Exception:
            pass
        st.success("🎉 裏コマンド発動：7日間だけ PRO を解放しました！")
        st.session_state.secret_taps = 0
        st.session_state.secret_start = None

# ---------------------------
# サイドバー
# ---------------------------
with st.sidebar:
    st.markdown("### メニュー")
    refresh_pro_status_from_server()
    if st.session_state.tier == "pro":
        st.success("現在のプラン: PRO（有料/一時解放含む）")
        if st.session_state.user and st.session_state.user.get("pro_until"):
            st.caption(f"期限: {st.session_state.user.get('pro_until')}")
    else:
        st.write("現在のプラン: 無料")

    auth_ui()

    demo = st.text_input("PROコード（デモ）", type="password")
    if demo:
        if demo == PRO_UNLOCK_CODE:
            st.session_state.tier = "pro"
            if st.session_state.user:
                st.session_state.user["pro"] = True
            st.success("PROを解放しました ✨（本番はStripeをご利用ください）")
        else:
            st.error("コードが正しくありません")

    st.divider()
    st.markdown("#### PRO購入")
    if st.button("Stripeで購入する", use_container_width=True):
        email = st.session_state.user.get("email") if st.session_state.user else None
        session = create_checkout_session(email)
        if session and session.get("url"):
            st.write("決済ページへ移動します…")
            st.markdown(f"<a href='{session['url']}' target='_self'>▶ Checkout へ</a>", unsafe_allow_html=True)

    st.divider()
    with st.expander("アプリ情報", expanded=False):
        st.caption("バージョン: 1.2.0（長押し/連打で開発者メニュー…？）")
        if st.button("バージョン情報（7回で秘密）", help="7回連続でタップすると…"):
            handle_secret_tap()
        if 0 < st.session_state.secret_taps < 7:
            st.progress(st.session_state.secret_taps / 7)

# 戻りURLでの検証
q = st.query_params
if q.get("session_id"):
    if verify_checkout_and_mark_pro(q.get("session_id")):
        st.success("決済を確認しました。PRO が有効になりました。")

# 期限切れ処理（ゲスト/ローカル）
if st.session_state.user and st.session_state.user.get("pro_until"):
    try:
        until = datetime.fromisoformat(str(st.session_state.user.get("pro_until")).replace("Z","+00:00")).astimezone(JST)
        if until <= now_jst():
            st.session_state.tier = "free"
            st.session_state.user["pro"] = False
            st.session_state.user["pro_until"] = None
    except Exception:
        pass

# ---------------------------
# 入力 → 動画広告 → 結果
# ---------------------------
st.title("📈 集客コンサルAI")
st.caption("業種・目標・予算・地域・ペルソナを入れるだけ。7日間の具体アクションを自動生成。")

if st.session_state.step == "input":
    with st.container():
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            industry = st.selectbox("業種", options=list(INDUSTRY_HINTS.keys()) + ["不動産","教育","その他"], index=0)
        with col2:
            goal = st.selectbox("目標", ["予約","問い合わせ","資料請求","売上","リード獲得"]) 
        col3, col4 = st.columns(2)
        with col3:
            budget = st.number_input("月間予算（円）", min_value=10000, step=10000, value=100000)
        with col4:
            region = st.text_input("地域（市区町村/エリア）", value="東京都内")
        persona = st.text_area("ペルソナ（属性/悩み/行動）", placeholder="例：30代女性。仕事帰りに寄れる/時短重視。SNSで口コミをよく見る")
        st.markdown('</div>', unsafe_allow_html=True)

        show_video_ad()

        disabled = not (industry and goal and budget and region and persona)
        if st.button("7日間プランを作成", use_container_width=True, disabled=disabled):
            st.session_state.form_data = {
                "industry": industry,
                "goal": goal,
                "budget": int(budget),
                "region": region,
                "persona": persona,
            }
            st.session_state.ad_started_at = time.time()
            st.session_state.step = "ad"
            st.experimental_rerun()

    st.markdown("<div class='footer-cta'><div>無料で今すぐ作成 ▶</div></div>", unsafe_allow_html=True)

elif st.session_state.step == "ad":
    st.header("少々お待ちください…結果を準備中")
    st.caption("スポンサー動画が流れます。数秒後に結果ページへ進めます。")

    show_video_ad()

    elapsed = int(time.time() - (st.session_state.ad_started_at or time.time()))
    remain = max(0, AD_MIN_SECONDS - elapsed)
    btn_label = "結果へ進む" if remain == 0 else f"{remain}秒後に進む"
    disabled = remain > 0

    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        if st.button(btn_label, use_container_width=True, disabled=disabled):
            d = st.session_state.form_data
            pro = (st.session_state.tier == "pro") or (st.session_state.user and st.session_state.user.get("pro"))
            st.session_state.plan_md = generate_plan(d["industry"], d["goal"], d["budget"], d["region"], d["persona"], pro)
            st.session_state.step = "result"
            st.experimental_rerun()

    if remain > 0:
        time.sleep(1)
        st.experimental_rerun()

else:
    md = st.session_state.plan_md
    if not md:
        st.warning("先に入力から開始してください。")
        st.stop()

    st.subheader("✅ 7日間アクションプラン")
    st.markdown(md)

    if sb and st.session_state.user and st.session_state.user.get("id") not in (None, "guest"):
        if st.button("このプランを保存", use_container_width=True):
            try:
                sb.table("plans").insert({
                    "user_id": st.session_state.user["id"],
                    "form": st.session_state.form_data,
                    "plan_md": md,
                }).execute()
                st.success("保存しました")
            except Exception as e:
                st.error(f"保存に失敗: {e}")

    st.download_button("Markdown をダウンロード", data=md.encode("utf-8"), file_name="7day_plan.md", mime="text/markdown", use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("条件を変えて再作成", use_container_width=True):
            st.session_state.step = "input"
            st.experimental_rerun()
    with c2:
        if st.session_state.tier == "free" and not (st.session_state.user and st.session_state.user.get("pro")):
            st.info("PRO を購入すると、詳細チェックやAB設計が追加されます。サイドバーから決済へ。")
        else:
            st.success("PRO 機能が有効です。")
