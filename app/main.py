from fastapi import FastAPI
from .environment import CodeReviewEnv
from .models import CodeReviewAction

app = FastAPI(title="Code Review OpenEnv")
env = CodeReviewEnv()

@app.post("/reset")
def reset(task_id: str = "task_easy"):
    result = env.reset(task_id)
    result["observation"] = result["observation"].model_dump()
    return result

@app.post("/step")
def step(action: CodeReviewAction):
    result = env.step(action)
    result["observation"] = result["observation"].model_dump()
    return result

@app.get("/state")
def state():
    return env.state()

@app.get("/health")
def health():
    return {"status": "ok"}