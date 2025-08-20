from web_consult_ai.services import consult

def test_smoke():
    report = consult({
        "industry": "飲食",
        "channel": "広告",
        "goal": "今週：主要CV 12 件",
        "keywords": ["ランチ", "デリバリー", "クーポン"],
        "score_awareness": 40,
        "score_consideration": 55,
        "score_conversion": 35,
        "score_retention": 60,
        "score_referral": 50,
        "tone": "やさしめ",
    })
    assert "diagnosis" in report and "kpi" in report and "research" in report
