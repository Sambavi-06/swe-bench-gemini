import os
import json
import time
import subprocess
import google.generativeai as genai
from google.generativeai.types import FunctionDeclaration, Tool

# --- Configuration ---
API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-pro-latest" # Using 1.5 Pro for better reasoning
LOG_FILE = "agent.log"
WORKDIR = "/testbed/openlibrary"

# --- Tools ---

def read_file(file_path: str):
    """Reads the content of a file."""
    try:
        full_path = os.path.join(WORKDIR, file_path)
        with open(full_path, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def write_file(file_path: str, content: str):
    """Overwrites a file with new content. Use carefully."""
    try:
        full_path = os.path.join(WORKDIR, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"

def run_bash(command: str):
    """Runs a bash command in the repository root."""
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            cwd=WORKDIR, 
            capture_output=True, 
            text=True,
            timeout=120
        )
        output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        return output
    except Exception as e:
        return f"Error executing command: {str(e)}"

def list_files(directory: str = "."):
    """Lists files in a directory."""
    try:
        return run_bash(f"find {directory} -maxdepth 2 -not -path '*/.*'")
    except Exception as e:
        return f"Error listing files: {str(e)}"

# --- Logging ---

def log_event(event_type, content, **kwargs):
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": event_type,
        "content": content,
        **kwargs
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

# --- Main Agent Loop ---

def main():
    if not API_KEY:
        print("Error: GEMINI_API_KEY not found.")
        return

    genai.configure(api_key=API_KEY)

    tools_list = [read_file, write_file, run_bash, list_files]
    
    # Task Description provided in the hackathon details
    task_description = """
    You are a Senior Software Engineer at the Internet Archive.
    
    TASK:
    Improve ISBN import logic in OpenLibrary. currently, the import process relies heavily on external API calls.
    We need to use local staged records instead where possible.
    
    The failing test is: `openlibrary/tests/core/test_imports.py::TestImportItem::test_find_staged_or_pending`
    
    YOUR GOAL:
    1. Analyze the failing test to understand what is wrong.
    2. Locate the relevant code in `openlibrary/` that needs fixing.
    3. Modify the code to make the test pass.
    4. Run the test to verify your fix.
    
    You have access to the codebase in `/testbed/openlibrary`.
    """

    system_instruction = """
    You are an autonomous coding agent. You have access to a Linux environment and the codebase.
    You must fix the issue described.
    
    GUIDELINES:
    1. EXPLORE FIRST: Use `ls` or `run_bash` to explore the file structure.
    2. DIAGNOSE: Run the failing test using `run_bash` to see the error output.
    3. READ: Read the relevant source files.
    4. EDIT: Use `write_file` to fix the code.
    5. VERIFY: Run the test again to confirm the fix.
    6. When you are confident the fix works and tests pass, reply with "TASK_COMPLETED".
    """

    model = genai.GenerativeModel(
        MODEL_NAME,
        tools=tools_list,
        system_instruction=system_instruction
    )

    chat = model.start_chat(enable_automatic_function_calling=True)

    print("🚀 Starting Gemini Agent...")
    log_event("system", "Agent started", task=task_description)

    # Initial prompt to kick off the chain
    response = chat.send_message(task_description)
    
    # We iterate manually to capture logs, though auto_function_calling handles the execution
    # For a hackathon, relying on auto-function calling is safer/easier for Gemini
    # But we need to log the specific tool calls. 
    # Since `enable_automatic_function_calling` hides the intermediate steps in the simple API,
    # we will reconstruct the logs from the chat history after execution or simply log the thought process.
    
    # Iteration loop for visibility
    max_turns = 15
    current_turn = 0
    
    while current_turn < max_turns:
        current_turn += 1
        print(f"--- Turn {current_turn} ---")
        
        # In 'automatic' mode, send_message handles the loop of Model -> Tool -> Model
        # We check the history to log what happened.
        
        last_part = response.parts[-1]
        text_response = last_part.text if last_part.text else "Tool execution..."
        
        print(f"Agent: {text_response[:200]}...")
        log_event("response", text_response)

        if "TASK_COMPLETED" in text_response:
            print("✅ Agent marked task as completed.")
            break
            
        # If the agent didn't finish, we prompt it to continue if it stopped.
        # usually auto-calling handles this, but if it stops to ask a question:
        response = chat.send_message("Continue. If finished, say TASK_COMPLETED.")

    # Post-process logging: Dump tool usage from history
    for msg in chat.history:
        for part in msg.parts:
            if fn := part.function_call:
                log_event("tool_use", "call", tool=fn.name, args=dict(fn.args))
            if resp := part.function_response:
                log_event("tool_result", "result", tool=resp.name)

if __name__ == "__main__":
    main()
