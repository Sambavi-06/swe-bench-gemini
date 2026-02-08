import json
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-exit-code", type=int, default=1, help="Exit code of the post-verification tests")
    args = parser.parse_args()

    log_file = "agent.log"
    resolved = args.test_exit_code == 0
    
    input_tokens = 0
    output_tokens = 0
    tool_counts = {"read_file": 0, "write_file": 0, "run_bash": 0, "list_files": 0}
    
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    # Rough estimation for hackathon purposes (Gemini counts chars usually)
                    # Actual token usage requires API metadata which simple chat history might not expose easily
                    # We estimate 1 token per 4 chars for content
                    if "content" in entry and entry["content"]:
                        chars = len(str(entry["content"]))
                        if entry["type"] == "response":
                            output_tokens += chars // 4
                        else:
                            input_tokens += chars // 4
                    
                    if entry["type"] == "tool_use":
                        tool_name = entry.get("tool")
                        if tool_name in tool_counts:
                            tool_counts[tool_name] += 1
                except:
                    pass

    # Gemini 1.5 Pro pricing approx (Check current pricing)
    # Input: $3.50 / 1M tokens
    # Output: $10.50 / 1M tokens
    cost = (input_tokens / 1_000_000 * 3.50) + (output_tokens / 1_000_000 * 10.50)

    result = {
        "resolved": resolved,
        "duration_seconds": 0, # Placeholder
        "total_cost_usd": round(cost, 4),
        "tokens": {
            "input": input_tokens,
            "output": output_tokens
        },
        "tool_usage": tool_counts
    }

    with open("result.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"Metrics extracted. Resolved: {resolved}")

if __name__ == "__main__":
    main()
