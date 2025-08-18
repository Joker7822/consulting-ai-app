# 集客コンサルAI（LLM搭載・Streamlit）

- 無料/PRO差別化、Stripe課金、Supabase会員化、動画広告インタースティシャル、裏コマンド（7タップで7日PRO）
- **LLM生成**（OpenAI）：`OPENAI_API_KEY` を `.streamlit/secrets.toml` に設定し、`USE_LLM=true` で有効化
- LLM失敗時はルールベースに自動フォールバック

## セットアップ
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### .streamlit/secrets.toml（例）
```toml
# Stripe
STRIPE_SECRET_KEY = "sk_test_xxx"
STRIPE_PUBLISHABLE_KEY = "pk_test_xxx"
STRIPE_PRICE_ID = "price_xxx"
STRIPE_DOMAIN = "http://localhost:8501"
STRIPE_SUCCESS_PATH = "/?paid=1"
STRIPE_CANCEL_PATH = "/?canceled=1"

# Supabase
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_ANON_KEY = "public-anon-key"

# LLM
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
USE_LLM = true

# Demo（本番は無効化）
PRO_UNLOCK_CODE = "PRO-2025"
```

## デプロイ
- GitHubにpush → Streamlit Community Cloudでデプロイ
- もしくは任意のPaaSで `streamlit run streamlit_app.py`
