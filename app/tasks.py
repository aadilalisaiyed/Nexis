TASKS = {
    "task_easy": {
        "id": "task_easy",
        "difficulty": "easy",
        "language": "python",
        "instructions": "Find the bug in this function and suggest a fix.",
        "code": """
def calculate_average(numbers):
    total = 0
    for n in numbers:
        total += n
    return total / len(numbers)   # Bug: crashes on empty list
""",
        "hidden_issues": ["division by zero when list is empty"],
        "required_keywords": ["empty", "zero", "len", "ZeroDivisionError"],
        "max_steps": 5,
    },

    "task_medium": {
        "id": "task_medium",
        "difficulty": "medium",
        "language": "python",
        "instructions": "Review this login function for security vulnerabilities.",
        "code": """
import sqlite3

def login(username, password):
    conn = sqlite3.connect('users.db')
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = conn.execute(query).fetchone()
    return result is not None
""",
        "hidden_issues": ["SQL injection", "plaintext password comparison", "no connection close"],
        "required_keywords": ["injection", "sql", "password", "hash", "parameterized"],
        "max_steps": 8,
    },

    "task_hard": {
        "id": "task_hard",
        "difficulty": "hard",
        "language": "python",
        "instructions": "Perform a full code review: bugs, security, performance, and design issues.",
        "code": """
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
""",
        "hidden_issues": [
            "race condition on shared `results` list",
            "race condition on shared `cache` dict",
            "no error handling for failed HTTP requests",
            "unbounded cache (memory leak)",
            "hardcoded internal URL",
            "no timeout on requests",
        ],
        "required_keywords": ["race", "thread", "lock", "cache", "timeout", "error", "exception"],
        "max_steps": 12,
    },
}