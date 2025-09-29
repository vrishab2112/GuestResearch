Agent 1 (Data Gathering)

Overview
- Given a guest name, search the web (excluding YouTube), fetch relevant pages, find YouTube videos, download available transcripts, and fetch YouTube comments.
- Normalize everything into chunks and write JSONL under `outputs/<guest>/`.

Quick start
1) Create `.env` in this directory (optional for comments API):
```
YOUTUBE_API_KEY=YOUR_YT_DATA_API_V3_KEY
```
2) Run
```
python automationworkflow/run_agent1.py --guest "Guest Name" --max-videos 5 --max-comments 100
```

Outputs
- `outputs/<guest>/raw/youtube.jsonl` – YouTube videos, transcripts, comments
- `outputs/<guest>/chunks.jsonl` – normalized text chunks ready for RAG
- summary.jsonl – not generated (avoids duplication)

Dedicated files
- `outputs/<guest>/about_guest.jsonl`
- `outputs/<guest>/books_written.jsonl`
- `outputs/<guest>/social_bio.jsonl`
 - `outputs/<guest>/web.jsonl` – non‑YouTube pages with metadata (domain, text_hash, estimated_tokens)

Environment
- `.env` can include:
```
YOUTUBE_API_KEY=...
TAVILY_API_KEY=...
```

Notes
- Web search uses DuckDuckGo HTML endpoint (no API key) and filters out YouTube domains for non‑YouTube content.
- YouTube comments use Data API v3 if `YOUTUBE_API_KEY` is set; otherwise comments are skipped gracefully.

