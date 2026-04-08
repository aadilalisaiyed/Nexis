from .tasks import TASKS
from .graders import grade_response
from .models import CodeReviewObservation, CodeReviewAction, CodeReviewReward

class CodeReviewEnv:
    def __init__(self):
        self.current_task = None
        self.action_history = []
        self.step_count = 0
        self.done = False

    def reset(self, task_id: str = "task_easy"):
        task = TASKS[task_id]
        self.current_task = task
        self.action_history = []
        self.step_count = 0
        self.done = False
        return {
            "observation": CodeReviewObservation(
                task_id=task["id"],
                code_snippet=task["code"],
                language=task["language"],
                instructions=task["instructions"],
                step_number=0,
            ),
            "reward": 0.0,
            "done": False,
            "info": {"difficulty": task["difficulty"]},
        }

    def step(self, action: CodeReviewAction):
        self.step_count += 1
        self.action_history.append(action.model_dump())

        graded = grade_response(self.current_task, self.action_history)
        max_steps = self.current_task["max_steps"]

        # Done when max steps reached or near-perfect score
        self.done = self.step_count >= max_steps or graded["score"] >= 0.95

        print("\n--- STEP DEBUG ---")
        print("Step:", self.step_count)
        print("Action:", action)
        print("Score:", graded["score"])
        print("------------------\n")

        return {
            "observation": CodeReviewObservation(
                task_id=self.current_task["id"],
                code_snippet=self.current_task["code"],
                language=self.current_task["language"],
                instructions=self.current_task["instructions"],
                feedback_history=[a["comment"] for a in self.action_history],
                step_number=self.step_count,
            ),
            "reward": graded["score"],
            "done": self.done,
            "info": graded["breakdown"],
        }

    def state(self):
        return {
            "task_id": self.current_task["id"] if self.current_task else None,
            "step": self.step_count,
            "done": self.done,
            "action_count": len(self.action_history),
        }