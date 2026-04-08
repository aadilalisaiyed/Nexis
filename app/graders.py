def grade_response(task: dict, action_history: list) -> dict:
    """
    Score 0.0-1.0 based on:
    - Did the agent mention the key issues? (60%)
    - Quality of suggested fixes (30%)
    - Correct severity assessment (10%)
    """
    all_comments = " ".join(
        a["comment"].lower() for a in action_history
    )
    all_fixes = " ".join(
        (a.get("suggested_fix") or "").lower() for a in action_history
    )

    required = task["required_keywords"]
    found = sum(1 for kw in required if kw in all_comments)
    keyword_score = found / len(required)           # 0.0 – 1.0

    has_fix = any(
        a.get("suggested_fix") and len(a["suggested_fix"]) > 20
        for a in action_history
    )
    fix_score = 0.8 if has_fix else 0.0

    severities = [a.get("severity", "") for a in action_history]
    severity_ok = task["difficulty"] == "easy" and "high" in severities \
               or task["difficulty"] == "medium" and "critical" in severities \
               or task["difficulty"] == "hard" and "critical" in severities
    severity_score = 1.0 if severity_ok else 0.3

    total = (keyword_score * 0.6) + (fix_score * 0.3) + (severity_score * 0.1)
    return {
        "score": round(min(max(total, 0.0), 1.0), 3),
        "breakdown": {
            "issues_found": round(keyword_score, 3),
            "fix_quality": round(fix_score, 3),
            "severity": round(severity_score, 3),
        },
        "feedback": f"Found {found}/{len(required)} key issues.",
    }