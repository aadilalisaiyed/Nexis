from pydantic import BaseModel
from typing import Optional, List

class CodeReviewObservation(BaseModel):
    task_id: str
    code_snippet: str          # The code the agent must review
    language: str              # e.g. "python"
    instructions: str          # What to look for
    feedback_history: List[str] = []   # Previous agent comments
    step_number: int = 0

class CodeReviewAction(BaseModel):
    comment: str               # The agent's review comment
    severity: str              # "low" | "medium" | "high" | "critical"
    line_numbers: Optional[List[int]] = None
    suggested_fix: Optional[str] = None

class CodeReviewReward(BaseModel):
    score: float               # 0.0 – 1.0
    breakdown: dict            # e.g. {"bug_found": 0.4, "fix_quality": 0.3}
    feedback: str              # Human-readable explanation