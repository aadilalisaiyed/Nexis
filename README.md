# Code Review Environment — OpenEnv

An RL environment where an AI agent reviews real buggy Python code snippets, identifies issues, and suggests fixes. Built on the [OpenEnv](https://openenv.ai) spec for training and evaluating language model agents on realistic software engineering tasks.

---

## Why this environment?

Code review is one of the most common tasks senior engineers perform — and one of the hardest to automate well. A good code reviewer must:

- Spot bugs that aren't immediately obvious
- Identify security vulnerabilities
- Reason about concurrency and performance
- Suggest concrete, actionable fixes

This environment provides a structured, reproducible benchmark for measuring how well AI agents can do exactly that. Unlike toy environments, every task here reflects a class of bug that has caused real production incidents.

---

## Environment overview

| Property | Value |
|---|---|
| Domain | Software engineering — code review |
| Tasks | 3 (easy → medium → hard) |
| Reward range | 0.0 – 1.0 |
| Observation type | Structured JSON |
| Action type | Structured JSON |
| API spec | OpenEnv v1 |
| Framework | FastAPI + Pydantic |
| Port | 7860 |

---

## Action space

Each agent action is a JSON object with the following fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `comment` | string | yes | The agent's review comment describing the issue found |
| `severity` | string | yes | One of: `low`, `medium`, `high`, `critical` |
| `line_numbers` | list[int] or null | no | Line numbers where the issue occurs |
| `suggested_fix` | string or null | no | Concrete code or description of how to fix the issue |

Example action:
```json
{
  "comment": "This function is vulnerable to SQL injection because user input is interpolated directly into the query string.",
  "severity": "critical",
  "line_numbers": [6, 7],
  "suggested_fix": "Use parameterized queries: conn.execute('SELECT * FROM users WHERE username=? AND password=?', (username, password))"
}
```

---

## Observation space

Each observation returned by `reset()` and `step()` contains:

| Field | Type | Description |
|---|---|---|
| `task_id` | string | Identifier of the current task |
| `code_snippet` | string | The Python code the agent must review |
| `language` | string | Programming language (always `python`) |
| `instructions` | string | What the agent should look for |
| `feedback_history` | list[string] | All previous comments the agent has made |
| `step_number` | int | Current step count within the episode |

---

## Tasks

### Task 1 — Find the bug (easy)

**Objective:** Identify a division-by-zero error in a simple utility function.

**Code under review:**
```python
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)   # Bug: crashes on empty list
```

**Hidden issue:** The function raises `ZeroDivisionError` when called with an empty list.

**Expected agent behaviour:** Comment on the empty list edge case, assign `high` severity, and suggest a guard clause.

**Max steps:** 5
**Expected score:** 0.6 – 0.9

---

### Task 2 — Security review (medium)

**Objective:** Identify security vulnerabilities in a login function.

**Code under review:**
```python
import sqlite3

def login(username, password):
    conn = sqlite3.connect('users.db')
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = conn.execute(query).fetchone()
    return result is not None
```

**Hidden issues:**
- SQL injection via string interpolation
- Plaintext password comparison (no hashing)
- Database connection is never closed

**Expected agent behaviour:** Flag SQL injection as `critical`, mention password hashing, suggest parameterized queries, and note the missing `conn.close()`.

**Max steps:** 8
**Expected score:** 0.5 – 0.85

---

### Task 3 — Full architecture review (hard)

**Objective:** Perform a comprehensive review covering bugs, security, performance, and design.

**Code under review:**
```python
import threading
import requests

cache = {}

def fetch_user_data(user_ids):
    results = []
    threads = []

    def fetch(uid):
        if uid in cache:
            results.append(cache[uid])
        else:
            r = requests.get(f"http://internal-api/users/{uid}")
            data = r.json()
            cache[uid] = data
            results.append(data)

    for uid in user_ids:
        t = threading.Thread(target=fetch, args=(uid,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    return results
```

**Hidden issues (6 total):**
- Race condition on shared `results` list (multiple threads append simultaneously)
- Race condition on shared `cache` dict (concurrent reads/writes)
- No error handling for failed HTTP requests
- Unbounded cache grows forever (memory leak)
- Hardcoded internal URL — not configurable
- No timeout on HTTP requests (can hang indefinitely)

**Expected agent behaviour:** Identify thread safety issues with `critical` severity, mention `threading.Lock`, flag the unbounded cache, suggest `requests` timeout parameter, and recommend environment variables for the URL.

**Max steps:** 12
**Expected score:** 0.4 – 0.95

---

## Reward function

Rewards are computed after every step, giving the agent continuous signal rather than a sparse end-of-episode score.

The score is a weighted sum of three components:

| Component | Weight | How it's measured |
|---|---|---|
| Issues found | 60% | Fraction of required keywords present across all comments |
| Fix quality | 30% | Whether any action contains a `suggested_fix` longer than 20 characters |
| Severity accuracy | 10% | Whether the agent assigned the correct severity level for the task |

```
score = (issues_found × 0.6) + (fix_quality × 0.3) + (severity × 0.1)
```

Scores are always clamped to `[0.0, 1.0]`. An episode ends when the agent reaches max steps or achieves a score ≥ 0.95.

---

## API reference

### `POST /reset?task_id={task_id}`

Resets the environment and returns the initial observation.

**Parameters:**
- `task_id`: one of `task_easy`, `task_medium`, `task_hard` (default: `task_easy`)

**Response:**
```json
{
  "observation": { ... },
  "reward": 0.0,
  "done": false,
  "info": { "difficulty": "easy" }
}
```

---

### `POST /step`

Sends one agent action and returns the next observation and reward.

**Request body:** a `CodeReviewAction` JSON object (see Action space above)

**Response:**
```json
{
  "observation": { ... },
  "reward": 0.64,
  "done": false,
  "info": {
    "issues_found": 0.5,
    "fix_quality": 0.8,
    "severity": 1.0
  }
}
```

---

### `GET /state`

Returns the current internal state of the environment without advancing it.

**Response:**
```json
{
  "task_id": "task_medium",
  "step": 3,
  "done": false,
  "action_count": 3
}
```

---

### `GET /health`

Returns `{"status": "ok"}` — used for deployment health checks.

---

## Project structure

```
code-review-env/
├── app/
│   ├── __init__.py
│   ├── main.py          ← FastAPI app with all endpoints
│   ├── models.py        ← Pydantic Observation / Action / Reward models
│   ├── environment.py   ← Core env logic: reset(), step(), state()
│   ├── tasks.py         ← 3 tasks with code snippets and hidden issues
│   └── graders.py       ← Scoring functions (partial credit)
├── inference.py         ← Baseline agent script (root level, required)
├── openenv.yaml         ← OpenEnv spec metadata
├── Dockerfile           ← Container definition
├── requirements.txt     ← Python dependencies
└── README.md
```

---

## Setup and usage

### Prerequisites

- Python 3.11+
- pip
- Docker (for containerised deployment)
- A Groq API key (free at [console.groq.com](https://console.groq.com)) or any OpenAI-compatible API key

---

### Run locally

```bash
# 1. Clone the repo
git clone https://huggingface.co/spaces/Aadilali/code-review-env
cd code-review-env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
uvicorn app.main:app --reload --port 7860
```

The server is now running at `http://localhost:7860`.

---

### Quick smoke test

```bash
# Reset the environment
curl -X POST "http://localhost:7860/reset?task_id=task_easy"

# Send a review action
curl -X POST "http://localhost:7860/step" \
  -H "Content-Type: application/json" \
  -d '{"comment":"Empty list causes ZeroDivisionError","severity":"high","suggested_fix":"Add: if not numbers: return 0"}'

# Check state
curl http://localhost:7860/state
```

---

### Run the baseline inference script

```bash
API_BASE_URL=http://localhost:7860 \
MODEL_NAME=llama-3.1-8b-instant \
GROQ_API_KEY=your_groq_key_here \
python inference.py
```

---

### Run with Docker

```bash
# Build the image
docker build -t code-review-env .

# Run the container
docker run -p 7860:7860 code-review-env
```

---

## Baseline scores

Measured using `llama-3.1-8b-instant` via Groq API:

| Task | Difficulty | Score | Success |
|---|---|---|---|
| `task_easy` | Easy | 0.64 | ✅ |
| `task_medium` | Medium | 0.70 | ✅ |
| `task_hard` | Hard | 0.45 | ❌ |

The hard task genuinely challenges frontier models — a perfect score requires identifying all 6 concurrent programming issues across multiple steps.

---

## Environment variables

| Variable | Description | Required |
|---|---|---|
| `API_BASE_URL` | URL of the running environment server | Yes |
| `MODEL_NAME` | LLM model identifier for the agent | Yes |
| `HF_TOKEN` | HuggingFace token for deployment | Yes |
| `GROQ_API_KEY` | Groq API key for LLM inference | Yes (if using Groq) |

---

## Deployment on HuggingFace Spaces

This environment is deployed as a Docker Space on HuggingFace.

**Live URL:** `https://Aadilali-code-review-env.hf.space`

To deploy your own copy:

```bash
# Add HuggingFace as a git remote
git remote add hfspace https://huggingface.co/spaces/YOUR_USERNAME/code-review-env

# Push
git push hfspace main
```

Set the following secrets in your Space settings (`Settings → Repository secrets`):

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN`
- `GROQ_API_KEY`

---

## OpenEnv spec compliance

This environment implements the full OpenEnv interface:

- ✅ Typed `Observation`, `Action`, `Reward` Pydantic models
- ✅ `POST /reset` — returns initial observation
- ✅ `POST /step` — returns observation, reward, done, info
- ✅ `GET /state` — returns current environment state
- ✅ `openenv.yaml` with metadata
- ✅ Minimum 3 tasks with difficulty progression
- ✅ Graders produce deterministic scores in `[0.0, 1.0]`
- ✅ Partial reward signal at every step (not just end-of-episode)
- ✅ Dockerfile builds and runs cleanly
- ✅ Baseline `inference.py` at root with `[START]`/`[STEP]`/`[END]` log format

---

## License

MIT