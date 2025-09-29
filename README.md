# Guest Research – Agents 1–4

A Streamlit app that gathers public info about a guest (web + YouTube), generates insights (North Star + lesser‑known), creates a conversation plan (with audience psychology and data‑backed insights), produces a final report (MD/DOCX), and includes a chatbot powered by the collected corpus.

## Run locally

```bash
pip install -r requirements.txt
streamlit run automationworkflow/ui/app.py
```

Enter your own keys in the sidebar:
- OPENAI_API_KEY (required for Agents 2–4)
- YOUTUBE_API_KEY (optional; enables YouTube search/comments)
- TAVILY_API_KEY (optional)

## Deploy (free)
- Streamlit Community Cloud → App file: `automationworkflow/ui/app.py`
- Leave secrets empty so users supply keys in the UI

## Structure
- `automationworkflow/run_agent1.py` – web + YouTube ingestion
- `automationworkflow/agent2` – summarization (North Star + lesser‑known)
- `automationworkflow/agent3` – conversation plan, audience psychology, insights & data
- `automationworkflow/report` – final report (Markdown + DOCX)
- `automationworkflow/ui` – Streamlit UI (main app + prompt editor page)

## Notes
- Outputs → `automationworkflow/outputs/<Guest>/` (git‑ignored)
- Word export requires `python-docx`; optional Chroma retrieval requires `chromadb`
