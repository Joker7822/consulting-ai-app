# ai_engine.py
import random

def generate_persona(goal: str, target: str):
    """入力から簡易ペルソナを生成"""
    persona = {
        "名前": "佐藤さん（仮想顧客）",
        "年齢": "35歳",
        "属性": f"{target} に多い層",
        "悩み": "時間がない、信頼できる選択肢が欲しい",
        "求める価値": "シンプル・安心・コスパ"
    }
    return persona


def smartify_goal(goal: str):
    """曖昧な目標を SMART 目標風に整形"""
    return f"{goal} → 『30日以内に10%成長を数値で確認できる』"


def generate_action_plan(goal: str, target: str, budget: int):
    """7日間のアクションプランを自動生成"""
    plan = []
    actions = [
        "SNSに自己紹介と価値提案を投稿",
        "LINE公式アカウントを開設し友だち登録導線を作成",
        "既存顧客にアンケートを取り信頼構築",
        "Instagramで商品事例を発信",
        "小額広告をテスト配信",
        "LPのCTAを改善",
        "結果を集計し次週の改善点をまとめる"
    ]
    for i, action in enumerate(actions, start=1):
        plan.append({"day": i, "task": action})
    return plan


def generate_consulting(goal: str, target: str, budget: int):
    """総合的なコンサル出力"""
    persona = generate_persona(goal, target)
    smart_goal = smartify_goal(goal)
    plan = generate_action_plan(goal, target, budget)

    advice = f"""
### 🎯 目標の整理
- あなたの入力: {goal}
- SMART変換: {smart_goal}

### 👤 ターゲット（ペルソナ例）
- 名前: {persona['名前']}
- 年齢: {persona['年齢']}
- 属性: {persona['属性']}
- 悩み: {persona['悩み']}
- 求める価値: {persona['求める価値']}

### 📅 7日間アクションプラン
""" 
    for p in plan:
        advice += f"- Day {p['day']}: {p['task']}\n"

    advice += f"""
### 💰 予算アドバイス
- 想定予算: {budget}円
- 推奨配分: SNS運用 {budget*0.4:.0f}円 / 広告 {budget*0.6:.0f}円

---
※ このプランは一般的な例です。実際の事業状況に応じて柔軟に調整してください。
"""
    return advice
