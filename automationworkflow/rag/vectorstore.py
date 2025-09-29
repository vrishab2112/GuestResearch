from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple


def _lazy_import_chroma():
    import chromadb
    from chromadb.config import Settings
    return chromadb


def build_index(chunks_path: Path, db_dir: Path, collection_name: str = "guest_chunks") -> Tuple[int, str]:
    chroma = _lazy_import_chroma()
    client = chroma.PersistentClient(path=str(db_dir))
    coll = client.get_or_create_collection(name=collection_name, metadata={"hnsw:space": "cosine"})

    ids: List[str] = []
    docs: List[str] = []
    metas: List[Dict] = []
    # Read chunks.jsonl
    count = 0
    with Path(chunks_path).open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = obj.get("chunk_id") or f"auto_{count}"
            txt = obj.get("text") or ""
            meta = {
                "source_type": obj.get("source_type"),
                "url": obj.get("url"),
                "video_id": obj.get("video_id"),
                "comment_id": obj.get("comment_id"),
                "guest": obj.get("guest"),
            }
            ids.append(cid)
            docs.append(txt)
            metas.append(meta)
            count += 1
            if count % 1000 == 0:
                coll.add(ids=ids, documents=docs, metadatas=metas)
                ids, docs, metas = [], [], []
    if ids:
        coll.add(ids=ids, documents=docs, metadatas=metas)
    return count, str(db_dir)


def query(db_dir: Path, query_text: str, n_results: int = 6, collection_name: str = "guest_chunks") -> List[Dict]:
    chroma = _lazy_import_chroma()
    client = chroma.PersistentClient(path=str(db_dir))
    coll = client.get_or_create_collection(name=collection_name)
    res = coll.query(query_texts=[query_text], n_results=n_results)
    out: List[Dict] = []
    for i in range(len(res.get("ids", [[]])[0])):
        out.append({
            "id": res["ids"][0][i],
            "text": res["documents"][0][i],
            "metadata": res["metadatas"][0][i],
            "distance": res.get("distances", [[None]])[0][i],
        })
    return out




