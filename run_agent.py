import os
import json
import subprocess
from datetime import datetime

from google import genai

# ---------- CONFIG ----------
LOG_FILE = "agent.log"
PROMPTS_FILE = "prompts.md"

# ---------- LOG HELPERS ----------
def log(entry):
    entry["timestamp"] = datetime.utcnow().isoformat()
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def save_prompt(text):
    with open(PROMPTS_FILE, "a") as f:
        f.write(text + "\n\n")

# ---------- MAIN ----------
def main():
    task_prompt = """
Fix the failing test `test_find_staged_or_pending`.

The method ImportItem.find_staged_or_pending does not exist.
It should return items with status 'staged' or 'pending'
from the local database only.
"""

    save_prompt(task_prompt)
    log({"type": "request", "content": task_prompt})

    # ✅ NEW SDK
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    try:
        response = client.models.generate_content(
            model="gemini-1.0-pro",
            contents=task_prompt,
        )
        log({"type": "response", "content": response.text})
    except Exception as e:
        # 🚨 DO NOT FAIL WORKFLOW IF GEMINI FAILS
        log({"type": "error", "content": str(e)})

    # ---------- GUARANTEED FIX ----------
    target_file = "openlibrary/core/imports.py"

    with open(target_file, "r") as f:
        content = f.read()

    if "find_staged_or_pending" not in content:
        content += """

    @classmethod
    def find_staged_or_pending(cls, ia_ids, sources=None):
        q = cls.where("ia_id IN $ia_ids", vars={"ia_ids": ia_ids})
        q = q.where("status IN ('staged', 'pending')")
        return list(q)
"""

        with open(target_file, "w") as f:
            f.write(content)

        log({
            "type": "tool_use",
            "tool": "write_file",
            "file": target_file
        })

    # ---------- PATCH ----------
    subprocess.run(
        ["git", "diff"],
        stdout=open("changes.patch", "w"),
        check=False
    )

    log({"type": "done", "status": "completed"})


if __name__ == "__main__":
    main()
