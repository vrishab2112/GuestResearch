import argparse
from pathlib import Path

from agent2.loader import load_agent1_outputs, build_snippets
from agent2.summarize import generate_insights


def main():
    parser = argparse.ArgumentParser(description="Agent 2 – Generate North Star and lesser-known topics")
    parser.add_argument("--guest", required=True)
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--outputs-root", default=str(Path(__file__).parent / "outputs"))
    parser.add_argument("--use-chroma", action="store_true")
    args = parser.parse_args()

    guest_dir = Path(args.outputs_root) / args.guest
    data = load_agent1_outputs(guest_dir)
    snippets = build_snippets(data)
    db_dir = guest_dir / "chroma"
    result = generate_insights(args.guest, snippets, guest_dir / "agent2", model=args.model, use_chroma=args.use_chroma, db_dir=db_dir)
    print({"north_star_count": len(result.get("north_star", [])), "lesser_known_count": len(result.get("lesser_known", []))})


if __name__ == "__main__":
    main()


