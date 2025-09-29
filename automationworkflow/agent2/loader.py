from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List


def read_jsonl(path: Path) -> List[Dict]:
    if not Path(path).exists():
        return []
    out: List[Dict] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def load_agent1_outputs(guest_dir: Path) -> Dict:
    return {
        "about": read_jsonl(guest_dir / "about_guest.jsonl"),
        "books": read_jsonl(guest_dir / "books_written.jsonl"),
        "social": read_jsonl(guest_dir / "social_bio.jsonl"),
        "web": read_jsonl(guest_dir / "web.jsonl"),
        "youtube": read_jsonl(guest_dir / "raw" / "youtube.jsonl"),
        "chunks": read_jsonl(guest_dir / "chunks.jsonl"),
    }


def build_snippets(payload: Dict, max_items: int = 15) -> List[Dict]:
    snippets: List[Dict] = []
    # Prefer web pages (title+url+short text)
    for r in payload.get("web", [])[:max_items]:
        if not r.get("text"):
            continue
        snippets.append({
            "source": r.get("url"),
            "title": r.get("title"),
            "text": (r.get("text") or "")[:1200],
        })
    # Add about summary if present
    if payload.get("about"):
        a = payload["about"][0]
        if a.get("summary"):
            snippets.append({
                "source": "about_guest",
                "title": "about_guest",
                "text": a.get("summary")[:1200],
            })
    # Add a few high-like comments
    comments = [r for r in payload.get("youtube", []) if r.get("source_type", "").startswith("youtube_comment")]
    comments.sort(key=lambda x: int(x.get("like_count", 0)), reverse=True)
    for c in comments[:50]:
        # Normalize source to the video page (avoid comment-anchored URLs)
        video_id = c.get("video_id") or ""
        video_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else (c.get("url") or "")
        snippets.append({
            "source": video_url,
            "title": "yt_comment",
            "text": c.get("text", "")[:500],
        })
    # Add transcript excerpts for better YouTube grounding
    transcripts = [r for r in payload.get("youtube", []) if r.get("source_type") == "youtube_transcript" and r.get("text")]
    for t in transcripts[:10]:
        vid = t.get("video_id") or ""
        video_url = f"https://www.youtube.com/watch?v={vid}" if vid else ""
        if video_url:
            snippets.append({
                "source": video_url,
                "title": "yt_transcript",
                "text": (t.get("text") or "")[:1200],
            })
    return snippets



