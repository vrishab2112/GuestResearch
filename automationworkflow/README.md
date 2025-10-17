Local development and usage

1) Prerequisites
- Python 3.10+
- Git

2) Clone and install
```
git clone https://github.com/<you>/GuestResearch.git
cd GuestResearch
pip install -r requirements.txt
```

3) Optional environment (set per-session in the UI too)
Create `automationworkflow/.env` (optional):
```
OPENAI_API_KEY=...
YOUTUBE_API_KEY=...   # enables YouTube comments via Data API v3
TAVILY_API_KEY=...    # optional web enrichment
```

4) Run the Streamlit app
```
streamlit run automationworkflow/ui/app.py
```

5) In the app sidebar
- Enter the Guest name
- Paste your `OPENAI_API_KEY` and (optional) `YOUTUBE_API_KEY`
- Click “Run Agent 1” to ingest data
- Click “Generate North Star…” (Agent 2)
- Click “Generate 10 Topics…” (Agent 3)
- Choose Final Report format (Markdown/Word) and “Generate Final Report”
- Use “Guests Manager” page to select/delete guest folders

6) Word export troubleshooting
- If python‑docx isn’t available or save fails, the app falls back to Pandoc (`pypandoc`) or Markdown.
- Install optional fallback: `pip install pypandoc`

7) Command‑line Agent 1 (optional)
```
python automationworkflow/run_agent1.py --guest "Guest Name" --max-videos 5 --max-comments 100
```

Outputs
- `outputs/<guest>/raw/youtube.jsonl` – YouTube videos, transcripts, comments
- `outputs/<guest>/web.jsonl` – non‑YouTube pages (cleaned) with metadata
- `outputs/<guest>/chunks.jsonl` – normalized text chunks
- `outputs/<guest>/agent2/north_star.json` – Agent 2
- `outputs/<guest>/agent3/plan.json` – Agent 3

Notes
- YouTube comments require `YOUTUBE_API_KEY`; otherwise they’re skipped gracefully.
- The sidebar keys override `.env` for the current session.
