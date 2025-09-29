from typing import List, Dict
from datetime import datetime
import hashlib


def compute_text_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def _chunk_text(text: str, max_tokens: int = 800) -> List[str]:
    # Simple character-based chunker approximating tokens
    max_len = max_tokens * 4
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_len)
        chunk = text[start:end]
        chunks.append(chunk)
        start = end
    return chunks


class ChunkNormalizer:
    def normalize(self, records: List[Dict], guest: str) -> List[Dict]:
        chunks: List[Dict] = []
        created = datetime.utcnow().isoformat()
        for rec in records:
            if rec.get("source_type") in {"web_article", "youtube_transcript", "youtube_comment", "youtube_comment_reply"}:
                text = rec.get("text") or ""
                if not text:
                    continue
                for idx, ch in enumerate(_chunk_text(text)):
                    chunk_id = f"{rec.get('source_type')}_{rec.get('video_id', '')}_{rec.get('comment_id', '')}_{idx}"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "text": ch,
                        "source_type": rec.get("source_type"),
                        "video_id": rec.get("video_id"),
                        "comment_id": rec.get("comment_id"),
                        "url": rec.get("url"),
                        "guest": guest,
                        "created_at": created,
                    })
        return chunks


