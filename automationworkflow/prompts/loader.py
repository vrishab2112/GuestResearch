from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


OVERRIDES_PATH = Path(__file__).resolve().parent / "overrides.json"


def load_overrides() -> Dict[str, Any]:
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        return json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_overrides(data: Dict[str, Any]) -> None:
    OVERRIDES_PATH.parent.mkdir(parents=True, exist_ok=True)
    OVERRIDES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_prompt(key: str, default_value: str) -> str:
    ov = load_overrides()
    v = ov.get(key)
    if isinstance(v, str) and v.strip():
        return v
    return default_value


