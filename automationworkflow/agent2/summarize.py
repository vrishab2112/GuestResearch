from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from .prompts import NORTH_STAR_SYSTEM, NORTH_STAR_USER_TEMPLATE
from prompts.loader import get_prompt
from rag.vectorstore import query as chroma_query


def call_openai_json(messages: List[Dict], model: str = "gpt-4o-mini") -> Dict:
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
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_insights(guest: str, snippets: List[Dict], out_dir: Path, model: str = "gpt-4o-mini", use_chroma: bool = False, db_dir: Path | None = None) -> Dict:
    # Optionally enrich snippets via Chroma
    if use_chroma and db_dir and db_dir.exists():
        aug: List[Dict] = []
        for probe in [f"{guest} biography", f"{guest} controversies", f"{guest} achievements", f"{guest} timeline"]:
            for hit in chroma_query(db_dir, probe, n_results=3):
                aug.append({"source": hit["metadata"].get("url"), "title": "retrieved", "text": hit.get("text", "")[:1000]})
        snippets = (aug + snippets)[:80]
    # Prepare limited snippet set for context window
    compact = json.dumps(snippets[:60], ensure_ascii=False)
    user = NORTH_STAR_USER_TEMPLATE.format(guest=guest, snippets=compact)
    system_prompt = get_prompt("agent2.system", NORTH_STAR_SYSTEM)
    user_prompt = get_prompt("agent2.user", user)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    result = call_openai_json(messages, model=model)
    # Write outputs
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "north_star.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result


