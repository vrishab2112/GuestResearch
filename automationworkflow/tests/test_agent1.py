import types
from pathlib import Path

from utils.normalize import ChunkNormalizer
from utils.io import write_jsonl, ensure_dir


def test_normalize_and_write_tmp(tmp_path: Path):
    records = [
        {"source_type": "web_article", "url": "https://example.com", "text": "hello world" * 50},
        {"source_type": "youtube_comment", "video_id": "vid", "comment_id": "c1", "text": "great interview"},
    ]
    norm = ChunkNormalizer()
    chunks = norm.normalize(records, guest="Guest")
    assert len(chunks) >= 2

    out = tmp_path / "chunks.jsonl"
    write_jsonl(out, chunks)
    assert out.exists()
    assert out.read_text(encoding="utf-8").strip() != ""


