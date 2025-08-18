# 集客コンサルAI（Streamlit）

日本語UIで「業種・目標・予算・地域・ペルソナ」を入れるだけで **7日間アクションプラン**を自動生成。
- 無料/PROの差分（PROは詳細チェックやABテスト設計など）
- **Stripe Checkout** 決済 → 成功時に PRO 付与
- **Supabase** で会員化＆プラン保存
- 入力→**動画広告**→結果の3ステップ（インタースティシャル広告）
- **裏コマンド**：サイドバーの「バージョン情報（7回で秘密）」を7回タップで **7日間だけPRO解放**

## セットアップ

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### .streamlit/secrets.toml
`.streamlit/secrets.toml` を作成して以下を設定してください（サンプルは `.streamlit/secrets.toml.sample` 参照）。

### Supabase
- Auth: Email/Password（またはGoogle/OAuth）を有効化
- テーブルとRLSは `supabase_schema.sql` を参考に作成

### Stripe
- 商品/PRICEを作成し、`STRIPE_PRICE_ID` を設定
- Checkout成功/キャンセルURLを `STRIPE_DOMAIN` + パスで指定
- さらに堅牢にするなら Webhook で `checkout.session.completed` を検証して `profiles.pro=true` を更新

## デプロイ
- **Streamlit Community Cloud**：このリポジトリを指定するだけ
- **Docker/他PaaS**：`streamlit run streamlit_app.py` を起動コマンドに設定

## ライセンス
MIT（必要に応じて変更）
