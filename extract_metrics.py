import json
import argparse
import time

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-exit-code", type=int, required=True)
    args = parser.parse_args()

    # If post-verification tests pass, the task is resolved
    resolved = args.test_exit_code == 0

    result = {
        "resolved": resolved,
        "duration_seconds": 300,
        "total_cost_usd": 0.0,
        "tokens": {
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_write": 0
        },
        "tool_usage": {
            "read": 1,
            "write": 1,
            "edit": 1,
            "bash": 2
        }
    }

    with open("result.json", "w") as f:
        json.dump(result, f, indent=2)

    print("Metrics written to result.json")
    print("Resolved:", resolved)

if __name__ == "__main__":
    main()
