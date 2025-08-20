# web_consult_ai

`ai_core.py`（静的ロジック）に **Web情報収集** を重ねて、提案の鮮度と妥当性を高めるためのミニフレームワークです。  
`ai_core.py` はアップロード済みのものをそのまま同梱しています。既存の関数（`funnel_diagnosis`/`three_horizons_actions`/`concrete_examples` など）を活用します【6†source】.

## できること
- Google Trends（`pytrends`）またはダミー値で **トレンド** を取得
- SerpAPI（APIキーあり）またはDuckDuckGo簡易パーサで **競合スニペット/広告例** を収集
- **業界別ベンチマーク**からCTR/CVR/開始率を引き、**KPI逆算** を実施
- トレンド勢いに応じて **業界重み（認知/検討/成約）を +-20% 以内で補正**

## セットアップ
```bash
python -m venv .venv && source .venv/bin/activate  # Windowsは .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env  # 必要に応じてAPIキーを設定
```

## 使い方（CLI）
```bash
python -m web_consult_ai.cli \
  --industry 飲食 \
  --channel 広告 \
  --goal "今週：主要CV 25 件" \
  --keywords ランチ デリバリー クーポン \
  --scores 40 55 35 60 50 \
  --out report.json
```

出力：`report.json` にリサーチ結果・ファネル診断・KPI逆算・施策案がまとまります。

## 設計
- `market_research.py`：外部データ取得（トレンド/検索）。キーが無くても **ダミーで動作**。
- `adapters.py`：トレンド→重み補正、ベンチマーク→KPI逆算へ変換。
- `services.py`：一連の **オーケストレーション**。`ai_core.py` は編集せずに活用。

## 設定・APIキー
- `SERPAPI_KEY`：SerpAPI（推奨）
- `pytrends` はキー不要。インストールされていない場合は自動でダミーにフォールバック。

## 注意
- DuckDuckGoのHTML解析はサービス変更で壊れる可能性があります。**本番はSerpAPI** を推奨。
- ベンチマークは `config.py` の `DEFAULT_BENCHMARKS` を起点に、各自の実績/資料で上書きください。

---

© 2025 MIT License
