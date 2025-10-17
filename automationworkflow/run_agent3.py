import argparse
import json
from pathlib import Path

from agent2.loader import load_agent1_outputs, build_snippets
from agent3.generate import generate_plan


def main():
    parser = argparse.ArgumentParser(description="Agent 3 – Topics, Outline, Questions")
    parser.add_argument("--guest", required=True)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--outputs-root", default=str(Path(__file__).parent / "outputs"))
    args = parser.parse_args()

    guest_dir = Path(args.outputs_root) / args.guest
    north_star_path = guest_dir / "agent2" / "north_star.json"
    north_star = json.loads(north_star_path.read_text(encoding="utf-8")) if north_star_path.exists() else {"north_star": [], "lesser_known": []}

    data = load_agent1_outputs(guest_dir)
    snippets = build_snippets(data)
    result = generate_plan(args.guest, north_star, snippets, guest_dir / "agent3", model=args.model)
    print({"topics": len(result.get("topics", [])), "questions": len(result.get("questions", []))})


if __name__ == "__main__":
    main()





