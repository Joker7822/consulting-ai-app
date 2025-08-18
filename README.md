# 集客コンサルAI（Streamlit）

## 使い方（ローカル）
1. Python 3.10+ を用意
2. 依存をインストール
   ```
   pip install -r requirements.txt
   ```
3. 実行
   ```
   streamlit run app.py
   ```
4. ブラウザが開いたら、日本語UIでブリーフを入力 → 診断

## 有料プラン（デモ）
- サイドバーで「有料（コード入力）」を選び、`PAID2025` を入力して有効化
- 本番運用では Stripe Checkout/Customer Portal + Webhook で検証し、セッションにトークン付与してください

## デプロイ（GitHub + Streamlit Cloud）
1. このフォルダをGitHubにpush
2. https://share.streamlit.io にGitHub連携 → `app.py` を指定
3. Secretsや環境変数があれば、Streamlitの「Settings → Secrets」に保存
