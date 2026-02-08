import json
import argparse
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-exit-code", type=int, default=1)
    args = parser.parse_args()

    # Default metrics structure
    result = {
        "resolved": args.test_exit_code == 0,
        "duration_seconds": 0,
        "total_cost_usd": 0.05,
        "tokens": {"input": 0, "output": 0},
        "tool_usage": {}
    }

    if os.path.exists("agent.log"):
        with open("agent.log", "r") as f:
            lines = f.readlines()
            result["tokens"]["input"] = len(lines) * 500 # Estimate
            result["tokens"]["output"] = len(lines) * 200 # Estimate

    with open("result.json", "w") as f:
        json.dump(result, f, indent=2)

if __name__ == "__main__":
    main()
