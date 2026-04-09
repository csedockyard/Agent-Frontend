from pprint import pprint

try:
    from backend.agent import run_demo_showcase
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from backend.agent import run_demo_showcase


def main() -> None:
    demo = run_demo_showcase().model_dump()
    print("=== PlacementPro One-Click Demo ===")
    print("Status:", demo["status"])
    print("\nCycle Summary:")
    pprint(demo["data"]["cycle_summary"])

    print("\nSteps Executed:")
    for index, step in enumerate(demo["data"]["steps_executed"], start=1):
        print(f"{index}. {step}")

    print("\nHighlighted Changes:")
    for index, change in enumerate(demo["data"]["highlighted_changes"], start=1):
        print(f"{index}. {change}")

    print("\nLive Campaign After Demo:")
    pprint(demo["data"]["live_after"]["active_campaigns"])


if __name__ == "__main__":
    main()
