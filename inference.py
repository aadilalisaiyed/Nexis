import asyncio, os, json
from openai import OpenAI
import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:7860")
MODEL_NAME   = os.environ.get("MODEL_NAME", "llama-3.1-8b-instant")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

TASKS = ["task_easy", "task_medium", "task_hard"]
MAX_STEPS = {"task_easy": 5, "task_medium": 8, "task_hard": 12}
SUCCESS_THRESHOLD = 0.6

def log_start(task, env, model):
    print(json.dumps({"type": "START", "task": task, "env": env, "model": model}), flush=True)

def log_step(step, action, reward, done, error):
    print(json.dumps({"type": "STEP", "step": step, "action": action,
                      "reward": reward, "done": done, "error": error}), flush=True)

def log_end(success, steps, score, rewards):
    print(json.dumps({"type": "END", "success": success, "steps": steps,
                      "score": score, "rewards": rewards}), flush=True)

def get_agent_action(code_snippet, instructions, history, step):
    messages = [
    {
        "role": "system",
        "content":
        "You are a senior code reviewer.\n"
        "Return ONLY valid JSON.\n"
        "Do NOT repeat issues.\n"
        "Focus only on important bugs, security, performance, and concurrency issues.\n"
    },
    {
        "role": "user",
        "content":
        f"Code:\n{code_snippet}\n\n"
        f"Task: {instructions}\n\n"
        f"Already found issues:\n{history}\n\n"
        "Find a NEW issue.\n"
        "Do NOT repeat previous issues.\n"
        "Find a DIFFERENT type of issue than before.\n\n"
        f"Step {step}\n\n"
        "Respond in this JSON format ONLY:\n"
        "{\n"
        '  "comment": "...",\n'
        '  "severity": "low|medium|high|critical",\n'
        '  "line_numbers": [1,2] or null,\n'
        '  "suggested_fix": "..."\n'
        "}"
    }
]

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2
    )

    raw = resp.choices[0].message.content.strip()

    # safer cleaning
    if "```" in raw:
        raw = raw.split("```")[1]
        raw = raw.replace("json", "")

    try:
        return json.loads(raw)
    except:
        return {
            "comment": "Parsing failed",
            "severity": "low",
            "line_numbers": None,
            "suggested_fix": None
        }
    
async def run_task(task_id: str):
    rewards, steps_taken, score = [], 0, 0.0
    success = False
    log_start(task=task_id, env="code-review-env", model=MODEL_NAME)
    try:
        async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=30.0) as http:
            # FIX 3: handle reset response safely
            reset_resp = await http.post(f"/reset?task_id={task_id}")
            result = reset_resp.json()

            # FIX 4: task_hard returns observation differently — handle both shapes
            obs = result.get("observation") or result
            history = []

            for step in range(1, MAX_STEPS[task_id] + 1):
                if result.get("done"):
                    break
                try:
                    action = get_agent_action(
                        obs["code_snippet"], obs["instructions"], history, step
                    )
                except Exception as parse_err:
                    # if LLM returns bad JSON, send a safe fallback action
                    action = {
                        "comment": "Unable to parse review",
                        "severity": "low",
                        "line_numbers": None,
                        "suggested_fix": None
                    }

                step_resp = await http.post("/step", json=action)
                result = step_resp.json()
                obs = result.get("observation") or result
                reward = result.get("reward", 0.0)
                done = result.get("done", False)
                rewards.append(reward)
                steps_taken = step
                history.append(action.get("comment", ""))
                log_step(step=step, action=action.get("comment", "")[:100],
                         reward=reward, done=done, error=None)
                if done:
                    break

        score = max(rewards) if rewards else 0.0
        score = round(min(max(score, 0.0), 1.0), 3)
        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        log_step(step=steps_taken, action="", reward=0.0, done=True, error=str(e))
    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score

async def main():
    for task_id in TASKS:
        await run_task(task_id)

if __name__ == "__main__":
    asyncio.run(main())