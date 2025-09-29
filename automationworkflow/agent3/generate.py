from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List

from .prompts import SYSTEM, USER_TEMPLATE
from prompts.loader import get_prompt


def call_openai_json(messages: List[Dict], model: str = "gpt-4o-mini") -> Dict:
    import requests
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "response_format": {"type": "json_object"}, "messages": messages, "temperature": 0.3}
    r = requests.post(url, headers=headers, json=payload, timeout=180)
    r.raise_for_status()
    content = r.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def generate_plan(guest: str, north_star_obj: Dict, snippets: List[Dict], out_dir: Path, model: str = "gpt-4o-mini") -> Dict:
    north_star = json.dumps(north_star_obj.get("north_star", []), ensure_ascii=False)
    lesser = json.dumps(north_star_obj.get("lesser_known", []), ensure_ascii=False)
    compact_snips = json.dumps(snippets[:80], ensure_ascii=False)
    user = USER_TEMPLATE.format(guest=guest, north_star=north_star, lesser_known=lesser, snippets=compact_snips)
    system_prompt = get_prompt("agent3.system", SYSTEM)
    user_prompt = get_prompt("agent3.user", user)
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    result = call_openai_json(messages, model=model)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "plan.json").open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result



