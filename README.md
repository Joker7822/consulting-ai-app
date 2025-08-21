# 集客コンサルAI Pro+（Web情報→チャネル別コピー生成付き）

## セットアップ
```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## 使い方
1. STEP1でブリーフを入力して「診断する」
2. 結果画面で「Web→実行計画」を生成（任意）
3. その下の「チャネル別コピー」セクションでコピーを生成→保存→CSVダウンロード
4. CSVを各チャネルの運用に貼り付け

### 環境変数（任意）
- `PAID_PASSCODE` … 有料解放コード（デフォルト `PAID2025`）
