import os
import json
import time
import subprocess
import google.generativeai as genai

# --- Configuration ---
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash" 
LOG_FILE = "agent.log"
WORKDIR = "/testbed/openlibrary"

# --- Tools ---
def read_file(file_path: str):
    """Reads file content."""
    try:
        full_path = os.path.join(WORKDIR, file_path)
        with open(full_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

def write_file(file_path: str, content: str):
    """Writes content to file."""
    try:
        full_path = os.path.join(WORKDIR, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return f"Success: Wrote to {file_path}"
    except Exception as e:
        return f"Error: {str(e)}"

def run_bash(command: str):
    """Runs a bash command."""
    try:
        result = subprocess.run(command, shell=True, cwd=WORKDIR, capture_output=True, text=True, timeout=60)
        return f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    except Exception as e:
        return f"Error: {str(e)}"

# --- Logging ---
def log_event(event_type, content, **kwargs):
    entry = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "type": event_type, "content": content, **kwargs}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

# --- Main Logic ---
def main():
    if not API_KEY:
        print("Missing GEMINI_API_KEY")
        return

    genai.configure(api_key=API_KEY)
    
    # Task Instructions
    task = "Improve ISBN import logic in OpenLibrary. Use local staged records instead of API calls. Fix test: openlibrary/tests/core/test_imports.py::TestImportItem::test_find_staged_or_pending"

    model = genai.GenerativeModel(
        MODEL_NAME,
        tools=[read_file, write_file, run_bash],
        system_instruction="You are a senior dev. Explore the repo, run the failing test to see the error, fix the code, and confirm the fix. Reply 'TASK_COMPLETED' when done."
    )

    chat = model.start_chat(enable_automatic_function_calling=True)
    log_event("system", "Agent started", task=task)
    
    response = chat.send_message(task)
    
    # Simple loop to ensure it doesn't stop too early
    for i in range(10):
        print(f"Agent Turn {i+1}...")
        if "TASK_COMPLETED" in response.text:
            print("Task marked as completed by agent.")
            break
        response = chat.send_message("Continue your work. If you have applied a fix, run the test to verify. If the test passes, say TASK_COMPLETED.")
        
    # Log the history for the hackathon artifacts
    for msg in chat.history:
        for part in msg.parts:
            if fn := part.function_call:
                log_event("tool_use", fn.name, args=dict(fn.args))
            if text := part.text:
                log_event("response", text)

if __name__ == "__main__":
    main()
