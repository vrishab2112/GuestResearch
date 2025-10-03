from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple


def _read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    out: List[Dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return out


def load_corpus(guest_dir: Path) -> Dict[str, List[Dict]]:
    corpus: Dict[str, List[Dict]] = {
        "web": _read_jsonl(guest_dir / "web.jsonl"),
        "about": _read_jsonl(guest_dir / "about_guest.jsonl"),
        "youtube": _read_jsonl(guest_dir / "raw" / "youtube.jsonl"),
        "chunks": _read_jsonl(guest_dir / "chunks.jsonl"),
    }
    # Prefer user-selected North Star if present
    ns = _read_json(guest_dir / "agent2" / "selected_north_star.json")
    if not ns:
        ns = _read_json(guest_dir / "agent2" / "north_star.json")
    corpus["north_star"] = ns.get("north_star", [])
    corpus["lesser_known"] = ns.get("lesser_known", [])
    plan = _read_json(guest_dir / "agent3" / "plan.json")
    corpus["topics"] = plan.get("topics", [])
    corpus["outline"] = plan.get("outline", [])
    corpus["questions"] = plan.get("questions", [])
    return corpus


def retrieve(chroma_db_dir: Path | None, query: str, n_results: int = 6) -> List[Dict]:
    if not chroma_db_dir or not chroma_db_dir.exists():
        return []
    try:
        from rag.vectorstore import query as chroma_query
        return chroma_query(chroma_db_dir, query, n_results=n_results)
    except Exception:
        return []


def web_search_and_fetch(query: str, max_results: int = 5) -> List[Dict]:
    # Use existing WebIngestor to avoid duplicating logic
    try:
        from ingestion.web import WebIngestor
    except Exception:
        return []
    w = WebIngestor()
    results = w.search_and_fetch(query, max_results=max_results)
    # Normalize for context packing
    out: List[Dict] = []
    for r in results:
        url = r.get("url")
        txt = (r.get("text") or "")[:1200]
        if url and txt:
            out.append({"source": url, "text": txt})
    return out


def top_youtube_comments(youtube_records: List[Dict], limit: int = 5) -> Tuple[List[Dict], Dict[str, str]]:
    """Return top liked comments and a mapping of video_id to title."""
    if not youtube_records:
        return [], {}
    videos = {r.get("video_id"): (r.get("title") or "") for r in youtube_records if r.get("source_type") == "youtube_video"}
    comments: List[Dict] = [r for r in youtube_records if (r.get("source_type") or "").startswith("youtube_comment")]
    for c in comments:
        try:
            c["_likes"] = int(c.get("like_count", 0) or 0)
        except Exception:
            c["_likes"] = 0
    comments.sort(key=lambda x: x.get("_likes", 0), reverse=True)
    return comments[:max(1, limit)], videos


def call_openai(messages: List[Dict], model: str = "gpt-4o") -> str:
    import requests
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def answer_question(guest: str, guest_dir: Path, question: str, model: str = "gpt-4o", use_chroma: bool = True, allow_web_search: bool = False, web_max_results: int = 5) -> Dict:
    corpus = load_corpus(guest_dir)
    db_dir = guest_dir / "chroma"
    retrieved = retrieve(db_dir if use_chroma else None, question, n_results=6)

    context_blocks: List[str] = []
    # Prefer retrieved docs, then north_star topics and plan topics
    for hit in retrieved:
        url = hit.get("metadata", {}).get("url")
        txt = hit.get("text", "")[:1200]
        if txt:
            context_blocks.append(json.dumps({"source": url, "text": txt}, ensure_ascii=False))
    for t in corpus.get("north_star", [])[:3]:
        context_blocks.append(json.dumps({"north_star": t}, ensure_ascii=False))
    for t in corpus.get("topics", [])[:5]:
        context_blocks.append(json.dumps({"topic": t}, ensure_ascii=False))

    # If insufficient context and allowed, run web search
    if allow_web_search and len(context_blocks) < 5:
        fresh = web_search_and_fetch(f"{guest} {question}", max_results=web_max_results)
        for r in fresh:
            context_blocks.append(json.dumps(r, ensure_ascii=False))

    # Special handling: best/top YouTube comments
    ql = question.lower()
    if "comment" in ql:
        top_comments, video_titles = top_youtube_comments(corpus.get("youtube", []), limit=5)
        if top_comments:
            bullets: List[str] = []
            for c in top_comments:
                vid = c.get("video_id")
                vtitle = video_titles.get(vid, "YouTube video")
                url = c.get("url") or (f"https://www.youtube.com/watch?v={vid}" if vid else "")
                likes = c.get("_likes", c.get("like_count", 0))
                text = (c.get("text") or "").strip()
                bullets.append(f"- {likes} likes – {vtitle}: {text[:220]} ({url})")
            best = top_comments[0]
            best_url = best.get("url") or (f"https://www.youtube.com/watch?v={best.get('video_id')}" if best.get("video_id") else "")
            best_likes = best.get("_likes", best.get("like_count", 0))
            best_text = (best.get("text") or "").strip()
            answer = (
                f"Top YouTube comment by likes: {best_likes} likes.\n\n"
                f"{best_text}\n\n"
                f"Link: {best_url}\n\n"
                f"Other high‑engagement comments:\n" + "\n".join(bullets[1:])
            ).strip()
            cites = [c.get("url") for c in top_comments if c.get("url")]
            return {"answer": answer, "citations": cites[:10]}

    system = (
        "You are a helpful research assistant answering questions about a guest. "
        "Cite sources inline using URLs when available. If unsure, say you don't know."
    )
    user = (
        f"Guest: {guest}\n\nQuestion: {question}\n\n"
        f"Context JSON blocks (one per line):\n" + "\n".join(context_blocks[:30])
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    content = call_openai(messages, model=model)
    citations = [h.get("metadata", {}).get("url") for h in retrieved if h.get("metadata", {}).get("url")]
    return {"answer": content, "citations": [c for c in citations if c]}


