from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple


def _read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    out: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def _call_openai_json(messages: List[Dict], model: str = "gpt-4o") -> Dict:
    import requests
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": messages,
        "temperature": 0.2,
    }
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def analyze_comments(guest_dir: Path, model: str = "gpt-4o", max_comments: int = 500) -> Dict:
    """Analyze YouTube comments and write structured insights to agent3/comment_analysis.json.

    Returns the analysis dict.
    """
    yt_path = guest_dir / "raw" / "youtube.jsonl"
    records = _read_jsonl(yt_path)
    comments = [r for r in records if (r.get("source_type") or "").startswith("youtube_comment")]
    # Sort by likes desc for highest-signal context
    for c in comments:
        try:
            c["_likes"] = int(c.get("like_count", 0) or 0)
        except Exception:
            c["_likes"] = 0
    comments.sort(key=lambda x: x.get("_likes", 0), reverse=True)
    sample = comments[:max_comments]

    # Compact context for the model
    compact: List[Dict] = []
    for c in sample:
        compact.append({
            "likes": c.get("_likes", c.get("like_count", 0)),
            "text": (c.get("text") or "")[:600],
        })
    context_json = json.dumps(compact, ensure_ascii=False)

    system = (
        "You are a data analyst specializing in YouTube community analysis. "
        "Given a JSON array of top comments (most-liked first), produce a concise but detailed analysis. "
        "Return strict JSON with keys: {\n"
        "  \"overall_sentiment\": {summary, positive_pct, neutral_pct, negative_pct},\n"
        "  \"hot_topics\": [{topic, why, example_quote}],\n"
        "  \"controversies\": [{issue, sides, example_quote}],\n"
        "  \"open_questions\": [string]  // 7-10 specific, non-duplicative viewer questions,\n"
        "  \"top_comments\": [{likes, quote}],\n"
        "  \"stats\": {total_comments, sample_size}\n"
        "}"
    )
    user = (
        "Top comments JSON (trimmed):\n" + context_json + "\n\n"
        "Summarize themes (culture/politics/tech), capture controversies fairly, and list real open questions from viewers. "
        "Provide 7-10 concise, distinct open questions that the audience still wants answered."
    )
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    result = _call_openai_json(messages, model=model)
    result["stats"] = result.get("stats", {})
    result["stats"]["total_comments"] = len(comments)
    result["stats"]["sample_size"] = len(sample)

    out_dir = guest_dir / "agent3"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "comment_analysis.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


