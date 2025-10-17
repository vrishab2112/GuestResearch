import os
import sys
import json
from pathlib import Path

import streamlit as st

# Ensure project root is on sys.path so imports work when running via Streamlit
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.youtube import YouTubeIngestor
from ingestion.web import WebIngestor
from utils.normalize import ChunkNormalizer
from utils.io import write_jsonl, ensure_dir
from run_agent1 import run_agent1
# keep the imported agent2 main under a distinct name so it doesn't collide with the button variable
from run_agent2 import main as run_agent2_cli
from report.final_report import generate_final_report, generate_final_report_docx


st.set_page_config(page_title="Guest Research – Agents 1–3", layout="wide")
st.title("Agents 1–3 – Research Workflow")

with st.sidebar:
    # Use session_state guest if set from Guests Manager
    default_guest = st.session_state.get("selected_guest") or "Elon Musk"
    guest = st.text_input("Guest name", default_guest)
    st.markdown("#### API keys (optional per user)")
    openai_key = st.text_input("OPENAI_API_KEY", type="password", help="Used by Agents 2 & 3")
    yt_key = st.text_input("YOUTUBE_API_KEY", type="password", help="Enables YouTube search/comments in Agent 1")
    tavily_key = st.text_input("TAVILY_API_KEY", type="password", help="Optional web enrichment")
    max_videos = st.number_input("Max YouTube videos", 0, 50, 5)
    max_comments = st.number_input("Max comments/video", 0, 1000, 200)
    include_replies = st.checkbox("Include replies", value=False)
    sort = st.selectbox("Comment sort", ["relevance", "time"], index=0)
    max_web_results = st.number_input("Max web results", 0, 50, 10)
    run_button = st.button("Run Agent 1")
    st.markdown("---")
    st.subheader("Agent 2 – Insights")
    model = "gpt-4o"
    run_agent2 = st.button("Generate North Star + Lesser-known Topics")
    use_chroma = st.checkbox("Use Chroma retrieval (if indexed)", value=False)
    st.markdown("---")
    st.subheader("Agent 3 – Conversation Plan")
    run_agent3 = st.button("Generate 10 Topics + Outline + Questions")
    analyze_comments_btn = st.button("Analyze YouTube Comments")
    st.markdown("---")
    st.subheader("Final Report")
    fmt = st.selectbox("Format", ["Markdown (.md)", "Word (.docx)"], index=0)
    generate_report = st.button("Generate Final Report")
    st.markdown("---")
    st.subheader("Agent 4 – Chatbot")
    chat_enabled = st.checkbox("Enable Chroma retrieval for chat", value=True)
    web_fallback = st.checkbox("Allow web search fallback", value=True)
    web_max = st.number_input("Web max results (fallback)", min_value=0, max_value=25, value=5)
    user_question = st.text_input("Ask a question about the guest")
    ask = st.button("Ask")

if openai_key:
    os.environ["OPENAI_API_KEY"] = openai_key
if tavily_key:
    os.environ["TAVILY_API_KEY"] = tavily_key
if yt_key:
    # Ensure Agent 1 (which reads env var) sees the per-session YouTube key
    os.environ["YOUTUBE_API_KEY"] = yt_key

api_key = yt_key or os.getenv("YOUTUBE_API_KEY")
yt = YouTubeIngestor(api_key=api_key)
status = st.empty()

if not yt.comments_enabled:
    st.warning("YouTube comments are skipped because YOUTUBE_API_KEY is not set.")

# Show completion status for Agents 1–3
outputs_root = PROJECT_ROOT / "outputs"
guest_dir = outputs_root / guest

# Persist chosen guest to session state for cross-page consistency
if guest and guest != st.session_state.get("selected_guest"):
    st.session_state["selected_guest"] = guest
agent1_done = (guest_dir / "chunks.jsonl").exists()
agent2_done = (guest_dir / "agent2" / "north_star.json").exists()
agent3_done = (guest_dir / "agent3" / "plan.json").exists()

with st.container():
    st.subheader("Completion Status")
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Agent 1:** {'✅ Done' if agent1_done else '⏳ Pending'}")
    c2.markdown(f"**Agent 2:** {'✅ Done' if agent2_done else '⏳ Pending'}")
    c3.markdown(f"**Agent 3:** {'✅ Done' if agent3_done else '⏳ Pending'}")

# Allow user to select or customize a North Star point for downstream agents
ns_dir = guest_dir / "agent2"
ns_path = ns_dir / "north_star.json"
ns_selected_path = ns_dir / "selected_north_star.json"
if ns_path.exists():
    try:
        ns_obj = json.loads(ns_path.read_text(encoding="utf-8"))
        options = [f"{i+1}. {it.get('title', 'Untitled')}" for i, it in enumerate(ns_obj.get("north_star", []))]
        options.append("Custom…")
        st.subheader("Choose North Star for Agents 3/Report/Chatbot")
        choice = st.selectbox("Pick one North Star point (or Custom)", options)
        if choice == "Custom…":
            custom_title = st.text_input("Custom North Star – title", value="")
            custom_why = st.text_area("Why it matters", value="")
            custom_evidence_raw = st.text_area("Evidence URLs (one per line)", value="")
            if st.button("Save North Star selection"):
                sel = {
                    "title": custom_title.strip() or "Custom North Star",
                    "why_it_matters": custom_why.strip(),
                    "supporting_evidence": [u.strip() for u in custom_evidence_raw.splitlines() if u.strip()],
                }
                ns_dir.mkdir(parents=True, exist_ok=True)
                ns_selected_path.write_text(json.dumps({"north_star": [sel], "lesser_known": ns_obj.get("lesser_known", [])}, ensure_ascii=False, indent=2), encoding="utf-8")
                st.success(f"Saved to `{ns_selected_path}`")
        else:
            idx = int(choice.split(".")[0]) - 1
            picked = (ns_obj.get("north_star", []) or [])[max(0, idx)] if ns_obj.get("north_star") else None
            if st.button("Save North Star selection"):
                if picked:
                    ns_dir.mkdir(parents=True, exist_ok=True)
                    ns_selected_path.write_text(json.dumps({"north_star": [picked], "lesser_known": ns_obj.get("lesser_known", [])}, ensure_ascii=False, indent=2), encoding="utf-8")
                    st.success(f"Saved to `{ns_selected_path}`")
        if ns_selected_path.exists():
            st.info(f"Current selection in use: `{ns_selected_path.name}`. Agent 3, Final Report and Chatbot will prefer this.")
    except Exception as _e:
        # if something goes wrong loading north star, fail silently — user can re-run Agent 2
        st.warning("Unable to load north_star.json (it may be malformed).")

# ---- Main action handlers ----
if run_button:
    status.info("Running pipeline… This may take a minute.")
    try:
        stats = run_agent1(
            guest=guest,
            max_videos=int(max_videos),
            max_comments=int(max_comments),
            include_replies=bool(include_replies),
            sort=str(sort),
            max_web_results=int(max_web_results),
        )
        status.success("Completed.")
        st.json(stats)
        out_dir = stats.get("output_dir")
        if out_dir:
            st.write(f"Outputs saved to `{out_dir}`")
            st.write("You can now run Agent 2 to generate insights.")
    except Exception as e:
        status.error(f"Failed: {e}")

elif run_agent2:
    # Call Agent 2 programmatically
    try:
        from agent2.loader import load_agent1_outputs, build_snippets
        from agent2.summarize import generate_insights
        outputs_root = PROJECT_ROOT / "outputs"
        guest_dir = outputs_root / guest
        data = load_agent1_outputs(guest_dir)
        snippets = build_snippets(data)
        res = generate_insights(guest, snippets, guest_dir / "agent2", model=model, use_chroma=use_chroma, db_dir=guest_dir / "chroma")
        st.success("Insights generated.")
        st.json({"north_star": len(res.get("north_star", [])), "lesser_known": len(res.get("lesser_known", []))})
        st.write(f"Saved to `{guest_dir / 'agent2' / 'north_star.json'}`")
    except Exception as e:
        st.error(f"Agent 2 failed: {e}")

elif run_agent3:
    try:
        from agent2.loader import load_agent1_outputs, build_snippets
        from agent3.generate import generate_plan
        outputs_root = PROJECT_ROOT / "outputs"
        guest_dir = outputs_root / guest
        # Prefer selected North Star if present
        north_star_path = guest_dir / "agent2" / "selected_north_star.json"
        if not north_star_path.exists():
            north_star_path = guest_dir / "agent2" / "north_star.json"
        north_star = json.loads(north_star_path.read_text(encoding="utf-8")) if north_star_path.exists() else {"north_star": [], "lesser_known": []}
        data = load_agent1_outputs(guest_dir)
        snippets = build_snippets(data)
        res = generate_plan(guest, north_star, snippets, guest_dir / "agent3", model=model)
        st.success("Conversation plan generated.")
        st.json({
            "topics": len(res.get("topics", [])),
            "questions": len(res.get("questions", [])),
            "audience_psychology_themes": len((res.get("audience_psychology") or {}).get("themes", [])),
            "insights_data": len(res.get("insights_data", [])),
        })
        st.write(f"Saved to `{guest_dir / 'agent3' / 'plan.json'}`")
    except Exception as e:
        st.error(f"Agent 3 failed: {e}")

elif analyze_comments_btn:
    try:
        from analysis.comments import analyze_comments
        outputs_root = PROJECT_ROOT / "outputs"
        guest_dir = outputs_root / guest
        res = analyze_comments(guest_dir, model=model, max_comments=400)
        st.success("Comment analysis generated.")
        st.json({
            "hot_topics": len(res.get("hot_topics", [])),
            "controversies": len(res.get("controversies", [])),
            "open_questions": len(res.get("open_questions", [])),
            "sample_size": (res.get("stats") or {}).get("sample_size"),
        })
        st.write(f"Saved to `{guest_dir / 'agent3' / 'comment_analysis.json'}`")
    except Exception as e:
        st.error(f"Comment analysis failed: {e}")

elif generate_report:
    try:
        if fmt.startswith("Markdown"):
            report_path = generate_final_report(guest, outputs_root)
        else:
            # attempt Word; helper will fallback if python-docx isn't available
            report_path = generate_final_report_docx(guest, outputs_root)

        # Derive download parameters from actual file suffix to avoid corrupted downloads
        suffix = report_path.suffix.lower()
        if suffix == ".docx":
            label = "Download Final Report (Word)"
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            fname = f"{guest} - final_report.docx"
        else:
            label = "Download Final Report (Markdown)"
            mime = "text/markdown"
            fname = f"{guest} - final_report.md"
            # If user selected Word but we fell back to Markdown (e.g., python-docx missing), inform them
            if not fmt.startswith("Markdown"):
                st.warning("Word export unavailable. Falling back to Markdown. Ensure python-docx is installed.")
        st.success("Final report generated.")
        st.write(f"Saved to `{report_path}`")
        if not (agent2_done and agent3_done):
            st.info("Some sections may be incomplete. Run Agents 2 and 3 for a full report.")
        st.download_button(label=label, data=report_path.read_bytes(), file_name=fname, mime=mime)
    except Exception as e:
        st.error(f"Final report failed: {e}")

elif ask and user_question.strip():
    try:
        from chatbot.answer import answer_question
        outputs_root = PROJECT_ROOT / "outputs"
        guest_dir = outputs_root / guest
        res = answer_question(
            guest,
            guest_dir,
            user_question.strip(),
            model="gpt-4o",
            use_chroma=chat_enabled,
            allow_web_search=web_fallback,
            web_max_results=int(web_max),
        )
        st.subheader("Answer")
        st.write(res.get("answer", ""))
        cites = [c for c in res.get("citations", []) if c]
        if cites:
            st.subheader("Citations")
            for c in cites[:10]:
                st.write(c)
    except Exception as e:
        st.error(f"Chat failed: {e}")

# Downloads (always shown if files exist)
yt_jsonl = guest_dir / "raw" / "youtube.jsonl"
if yt_jsonl.exists():
    st.markdown("---")
    st.subheader("Downloads")
    st.download_button(
        label="Download YouTube dataset (youtube.jsonl)",
        data=yt_jsonl.read_bytes(),
        file_name=f"{guest} - youtube.jsonl",
        mime="application/json",
    )
