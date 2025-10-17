import argparse
from pathlib import Path

from rag.vectorstore import build_index


def main():
    parser = argparse.ArgumentParser(description="Build Chroma index from chunks.jsonl")
    parser.add_argument("--guest", required=True)
    parser.add_argument("--outputs-root", default=str(Path(__file__).resolve().parents[1] / "outputs"))
    args = parser.parse_args()

    guest_dir = Path(args.outputs_root) / args.guest
    chunks_path = guest_dir / "chunks.jsonl"
    db_dir = guest_dir / "chroma"
    count, path = build_index(chunks_path, db_dir)
    print({"indexed_chunks": count, "db": path})


if __name__ == "__main__":
    main()





