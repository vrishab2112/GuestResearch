from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def _read_json(path: Path) -> Dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _read_jsonl(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    out: List[Dict] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return out


def _summarize_agent1(guest_dir: Path) -> Tuple[str, Dict[str, List[str]], List[str], List[Dict]]:
    about = _read_jsonl(guest_dir / "about_guest.jsonl")
    web = _read_jsonl(guest_dir / "web.jsonl")
    books = _read_jsonl(guest_dir / "books_written.jsonl")
    social = _read_jsonl(guest_dir / "social_bio.jsonl")

    about_text = ""
    if about:
        about_text = (about[0] or {}).get("summary", "")
    about_sources = (about[0] or {}).get("sources", []) if about else []

    # Build grouped link sections for nicer report formatting
    link_sections: Dict[str, List[str]] = {"articles": [], "books": [], "social": [], "youtube": []}
    for r in web[:10]:
        url = r.get("url")
        title = (r.get("title") or url or "").strip()
        if url:
            link_sections["articles"].append(f"- [{title}]({url})")
    # Books/longform
    for r in books[:8]:
        url = r.get("url")
        if url:
            label = "Book" if any(d in url for d in ("amazon.com", "goodreads.com", "books.google", "penguin")) else "Link"
            link_sections["books"].append(f"- [{label}]({url})")
    # Social
    for r in social[:8]:
        url = r.get("url")
        if url:
            link_sections["social"].append(f"- [Social]({url})")

    stats: List[str] = []
    youtube = _read_jsonl(guest_dir / "raw" / "youtube.jsonl")
    # YouTube video links
    yt_videos = [r for r in youtube if r.get("source_type") == "youtube_video"]
    for v in yt_videos[:10]:
        url = v.get("url") or (f"https://www.youtube.com/watch?v={v.get('video_id')}" if v.get("video_id") else None)
        title = (v.get("title") or url or "").strip()
        if url:
            link_sections["youtube"].append(f"- [{title}]({url})")
    videos = len(yt_videos)
    comments = sum(1 for r in youtube if (r.get("source_type") or "").startswith("youtube_comment"))
    transcripts = sum(1 for r in youtube if r.get("source_type") == "youtube_transcript")
    if any([videos, comments, transcripts]):
        stats.append(f"YouTube videos: {videos}")
        stats.append(f"Transcripts: {transcripts}")
        stats.append(f"Top comments: {comments}")

    return about_text, link_sections, stats, about_sources


def _format_north_star(north_star_obj: Dict) -> str:
    lines: List[str] = []
    for i, item in enumerate(north_star_obj.get("north_star", []), start=1):
        title = item.get("title") or f"North Star {i}"
        why = item.get("why_it_matters") or ""
        lines.append(f"#### {i}. {title}")
        if why:
            lines.append(f"{why}")
        evidence = item.get("supporting_evidence") or []
        for ev in evidence[:5]:
            lines.append(f"- {ev}")
        lines.append("")
    lesser = north_star_obj.get("lesser_known", [])
    if lesser:
        lines.append("### Lesser‑known topics")
        for t in lesser:
            lines.append(f"- {t}")
        lines.append("")
    return "\n".join(lines)


def _format_plan(plan_obj: Dict, comment_analysis: Optional[Dict] = None) -> str:
    lines: List[str] = []
    outline = plan_obj.get("outline", [])
    if outline:
        lines.append("### Conversation outline")
        for section in outline:
            sec = section.get("section") or "Section"
            lines.append(f"- **{sec}**")
            for b in section.get("bullets", [])[:10]:
                lines.append(f"  - {b}")
        lines.append("")

    topics = plan_obj.get("topics", [])
    if topics:
        lines.append("### Discussion topics")
        for i, t in enumerate(topics[:10], start=1):
            title = t.get("title") or f"Topic {i}"
            why = t.get("why") or ""
            lines.append(f"#### {i}. {title}")
            if why:
                lines.append(why)
            for c in t.get("citations", [])[:5]:
                lines.append(f"- {c}")
            lines.append("")

    questions = plan_obj.get("questions", [])
    if questions:
        lines.append("### Questions")
        for i, q in enumerate(questions[:25], start=1):
            text = q.get("q") or f"Question {i}"
            lines.append(f"- {i}. {text}")
            for c in q.get("citations", [])[:3]:
                lines.append(f"  - {c}")
        # Subsection: Questions the audience still wants to know (from comments)
        if comment_analysis:
            open_q = comment_analysis.get("open_questions") or []
            if open_q:
                lines.append("")
                lines.append("#### Questions the audience still wants to know")
                for q in open_q[:10]:
                    lines.append(f"- {q}")
        lines.append("")

    # Audience psychology
    audience = plan_obj.get("audience_psychology")
    if audience:
        lines.append("### Audience psychology")
        if audience.get("summary"):
            lines.append(audience["summary"]) 
            lines.append("")
        for t in (audience.get("themes") or [])[:8]:
            theme = t.get("theme") or "Theme"
            why = t.get("why") or ""
            lines.append(f"- {theme}: {why}")
            for c in t.get("citations", [])[:3]:
                lines.append(f"  - {c}")
        # Inline comment analysis under audience psychology
        if comment_analysis:
            overall = comment_analysis.get("overall_sentiment") or {}
            topics = comment_analysis.get("hot_topics") or []
            controversies = comment_analysis.get("controversies") or []
            open_q = comment_analysis.get("open_questions") or []
            top = comment_analysis.get("top_comments") or []
            stats = comment_analysis.get("stats") or {}

            lines.append("")
            lines.append("#### Comment analysis")
            if overall:
                summary = overall.get("summary") or ""
                pos = overall.get("positive_pct")
                neu = overall.get("neutral_pct")
                neg = overall.get("negative_pct")
                parts: List[str] = []
                if pos is not None:
                    parts.append(f"positive: {pos}%")
                if neu is not None:
                    parts.append(f"neutral: {neu}%")
                if neg is not None:
                    parts.append(f"negative: {neg}%")
                if summary:
                    if parts:
                        lines.append(f"{summary} (" + ", ".join(parts) + ")")
                    else:
                        lines.append(summary)
            if topics:
                lines.append("- Hot topics:")
                for t in topics[:4]:
                    why = t.get("why") or ""
                    lines.append(f"  - {t.get('topic')}: {why}")
            if controversies:
                lines.append("- Controversies:")
                for c in controversies[:3]:
                    lines.append(f"  - {c.get('issue')}: {c.get('sides')}")
            if open_q:
                lines.append("- Open questions (from viewers):")
                for q in open_q[:5]:
                    lines.append(f"  - {q}")
            if top:
                lines.append("- Top comments:")
                for c in top[:3]:
                    likes = c.get("likes")
                    quote = c.get("quote")
                    lines.append(f"  - {likes} likes – {quote}")
            if stats:
                lines.append(f"_Analyzed {stats.get('sample_size')} of {stats.get('total_comments')} comments._")
            lines.append("")
        else:
            lines.append("")

    # Tensions & Struggles (before Insights)
    ts = plan_obj.get("tensions_struggles") or {}
    top_ch = ts.get("top_challenges") or []
    biggest_fear = ts.get("biggest_fear") or {}
    if top_ch or biggest_fear:
        lines.append("### Tensions & struggles")
        for c in top_ch[:2]:
            lines.append(f"- Challenge: {c.get('challenge')}")
            if c.get("why"):
                lines.append(f"  - Why: {c.get('why')}")
        if biggest_fear.get("fear"):
            lines.append(f"- Biggest fear: {biggest_fear.get('fear')}")
            if biggest_fear.get("why"):
                lines.append(f"  - Why: {biggest_fear.get('why')}")
        lines.append("")

    # Controversy, Vulnerability & Taboo
    cvt = plan_obj.get("controversy_vulnerability_taboo") or {}
    debates = cvt.get("controversial_debates") or []
    shame_q = cvt.get("shameful_questions") or []
    if debates or shame_q:
        lines.append("### Controversy, vulnerability & taboo")
        for d in debates[:2]:
            lines.append(f"- Debate: {d.get('debate')}")
            if d.get("sides"):
                lines.append(f"  - Sides: {d.get('sides')}")
        if shame_q:
            lines.append("- Uncomfortable questions:")
            for q in shame_q[:2]:
                lines.append(f"  - {q}")
        lines.append("")

    # Insights & data focused on North Star
    insights = plan_obj.get("insights_data")
    if insights:
        lines.append("### Insights & data")
        for it in insights[:10]:
            head = it.get("headline") or "Insight"
            det = it.get("detail") or ""
            conf = it.get("confidence") or ""
            badge = f" (confidence: {conf})" if conf else ""
            lines.append(f"- {head}{badge}")
            if det:
                lines.append(f"  - {det}")
            for c in (it.get("citations") or [])[:3]:
                lines.append(f"  - {c}")
        lines.append("")

    return "\n".join(lines)


def _format_comment_analysis(analysis: Dict) -> str:
    lines: List[str] = []
    if not analysis:
        return ""
    overall = analysis.get("overall_sentiment") or {}
    if overall:
        lines.append("### Overall sentiment")
        summary = overall.get("summary") or ""
        if summary:
            lines.append(summary)
        pos = overall.get("positive_pct")
        neu = overall.get("neutral_pct")
        neg = overall.get("negative_pct")
        parts = []
        if pos is not None:
            parts.append(f"positive: {pos}%")
        if neu is not None:
            parts.append(f"neutral: {neu}%")
        if neg is not None:
            parts.append(f"negative: {neg}%")
        if parts:
            lines.append("(" + ", ".join(parts) + ")")
        lines.append("")

    topics = analysis.get("hot_topics") or []
    if topics:
        lines.append("### Hot topics")
        for t in topics[:8]:
            lines.append(f"- {t.get('topic')}: {t.get('why')}")
            if t.get("example_quote"):
                lines.append(f"  - \"{t.get('example_quote')}\"")
        lines.append("")

    controversies = analysis.get("controversies") or []
    if controversies:
        lines.append("### Controversies")
        for c in controversies[:6]:
            lines.append(f"- {c.get('issue')}: {c.get('sides')}")
            if c.get("example_quote"):
                lines.append(f"  - \"{c.get('example_quote')}\"")
        lines.append("")

    open_q = analysis.get("open_questions") or []
    if open_q:
        lines.append("### Open questions from viewers")
        for q in open_q[:10]:
            lines.append(f"- {q}")
        lines.append("")

    top = analysis.get("top_comments") or []
    if top:
        lines.append("### Top comments (by likes)")
        for c in top[:8]:
            likes = c.get("likes")
            quote = c.get("quote")
            lines.append(f"- {likes} likes – {quote}")
        lines.append("")

    stats = analysis.get("stats") or {}
    if stats:
        lines.append(f"_Analyzed {stats.get('sample_size')} of {stats.get('total_comments')} comments._")
        lines.append("")

    return "\n".join(lines)


def build_markdown_report(guest: str, guest_dir: Path) -> str:
    about_text, link_sections, stats, about_sources = _summarize_agent1(guest_dir)
    # Prefer user-selected North Star if present
    north_star_path = guest_dir / "agent2" / "selected_north_star.json"
    if not north_star_path.exists():
        north_star_path = guest_dir / "agent2" / "north_star.json"
    plan_path = guest_dir / "agent3" / "plan.json"
    north_star_obj = _read_json(north_star_path)
    plan_obj = _read_json(plan_path)
    comment_analysis = _read_json(guest_dir / "agent3" / "comment_analysis.json")
    comment_analysis = _read_json(guest_dir / "agent3" / "comment_analysis.json")

    lines: List[str] = []
    lines.append(f"# Final Interview Research Report — {guest}")
    lines.append("")
    if about_text:
        lines.append("## About the guest")
        lines.append(about_text)
        lines.append("")
        if about_sources:
            lines.append("#### Sources for 'About the guest'")
            for s in about_sources[:5]:
                url = s.get("url")
                title = s.get("title") or url
                if url:
                    lines.append(f"- [{title}]({url})")
            lines.append("")
    # Grouped links with dedupe and simple authority ranking
    if any(link_sections.values()):
        def _dedupe(seq: List[str]) -> List[str]:
            seen = set()
            out: List[str] = []
            for s in seq:
                if s in seen:
                    continue
                seen.add(s)
                out.append(s)
            return out
        def _rank(seq: List[str]) -> List[str]:
            authority = (
                "wikipedia.org", "britannica.com", "reuters.com", "bbc.com",
                "nytimes.com", "forbes.com", "cnn.com", "npr.org"
            )
            def score(item: str) -> int:
                url = item.split("(")[-1].rstrip(")")
                for i, dom in enumerate(authority):
                    if dom in url:
                        return -100 + i
                return 0
            return sorted(seq, key=score)
        lines.append("## Key links")
        if link_sections.get("articles"):
            art = _rank(_dedupe(link_sections["articles"]))
            lines.append("### Articles")
            lines.extend(art[:15])
            lines.append("")
        if link_sections.get("books"):
            books = _dedupe(link_sections["books"])[:12]
            lines.append("### Books & longform")
            lines.extend(books)
            lines.append("")
        if link_sections.get("social"):
            social = _dedupe(link_sections["social"])[:8]
            lines.append("### Social")
            lines.extend(social)
            lines.append("")
        if link_sections.get("youtube"):
            yt = _dedupe(link_sections["youtube"])[:10]
            lines.append("### YouTube")
            lines.extend(yt)
            lines.append("")
    if stats:
        lines.append("## Data gathering summary")
        for s in stats:
            lines.append(f"- {s}")
        lines.append("")

    if north_star_obj:
        lines.append("## North Star insights")
        lines.append(_format_north_star(north_star_obj))
    else:
        lines.append("## North Star insights")
        lines.append("_Not available. Run Agent 2 to generate insights._\n")

    if plan_obj:
        lines.append("## Conversation plan")
        lines.append(_format_plan(plan_obj, comment_analysis=comment_analysis))
    else:
        lines.append("## Conversation plan")
        lines.append("_Not available. Run Agent 3 to generate the plan._\n")

    return "\n".join(lines)


def generate_final_report(guest: str, outputs_root: Path) -> Path:
    guest_dir = outputs_root / guest
    guest_dir.mkdir(parents=True, exist_ok=True)
    content = build_markdown_report(guest, guest_dir)
    report_path = guest_dir / "final_report.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def generate_final_report_docx(guest: str, outputs_root: Path) -> Path:
    try:
        from docx import Document
    except Exception:
        # Fallback: still generate markdown if python-docx is missing
        return generate_final_report(guest, outputs_root)

    guest_dir = outputs_root / guest
    guest_dir.mkdir(parents=True, exist_ok=True)

    # Build sections separately to preserve headings
    about_text, link_sections, stats, about_sources = _summarize_agent1(guest_dir)
    ns_path = guest_dir / "agent2" / "selected_north_star.json"
    if not ns_path.exists():
        ns_path = guest_dir / "agent2" / "north_star.json"
    north_star_obj = _read_json(ns_path)
    plan_obj = _read_json(guest_dir / "agent3" / "plan.json")

    doc = Document()
    doc.add_heading(f"Final Interview Research Report — {guest}", 0)

    if about_text:
        doc.add_heading("About the guest", level=1)
        doc.add_paragraph(about_text)
        if about_sources:
            doc.add_heading("Sources for 'About the guest'", level=2)
            for s in about_sources[:5]:
                url = s.get("url")
                title = s.get("title") or url
                if url:
                    doc.add_paragraph(f"{title}: {url}")

    if any(link_sections.values()):
        doc.add_heading("Key links", level=1)
        if link_sections.get("articles"):
            doc.add_heading("Articles", level=2)
            for l in link_sections["articles"]:
                doc.add_paragraph(l)
        if link_sections.get("books"):
            doc.add_heading("Books & longform", level=2)
            for l in link_sections["books"]:
                doc.add_paragraph(l)
        if link_sections.get("social"):
            doc.add_heading("Social", level=2)
            for l in link_sections["social"]:
                doc.add_paragraph(l)

    if stats:
        doc.add_heading("Data gathering summary", level=1)
        for s in stats:
            doc.add_paragraph(s)

    doc.add_heading("North Star insights", level=1)
    if north_star_obj:
        for i, item in enumerate(north_star_obj.get("north_star", []), start=1):
            title = item.get("title") or f"North Star {i}"
            why = item.get("why_it_matters") or ""
            doc.add_heading(f"{i}. {title}", level=2)
            if why:
                doc.add_paragraph(why)
            for ev in (item.get("supporting_evidence") or [])[:5]:
                doc.add_paragraph(ev)
    else:
        doc.add_paragraph("Not available. Run Agent 2 to generate insights.")

    doc.add_heading("Conversation plan", level=1)
    if plan_obj:
        outline = plan_obj.get("outline", [])
        if outline:
            doc.add_heading("Conversation outline", level=2)
            for section in outline:
                sec = section.get("section") or "Section"
                doc.add_paragraph(sec)
                for b in section.get("bullets", [])[:10]:
                    doc.add_paragraph(f"- {b}")
        topics = plan_obj.get("topics", [])
        if topics:
            doc.add_heading("Discussion topics", level=2)
            for i, t in enumerate(topics[:10], start=1):
                title = t.get("title") or f"Topic {i}"
                why = t.get("why") or ""
                doc.add_heading(f"{i}. {title}", level=3)
                if why:
                    doc.add_paragraph(why)
                for c in t.get("citations", [])[:5]:
                    doc.add_paragraph(c)
        questions = plan_obj.get("questions", [])
        if questions:
            doc.add_heading("Questions", level=2)
            for i, q in enumerate(questions[:25], start=1):
                text = q.get("q") or f"Question {i}"
                doc.add_paragraph(f"{i}. {text}")
                for c in q.get("citations", [])[:3]:
                    doc.add_paragraph(f"  - {c}")
            # Subsection from comment analysis
            comment_analysis = _read_json(guest_dir / "agent3" / "comment_analysis.json")
            if comment_analysis:
                open_q = comment_analysis.get("open_questions") or []
                if open_q:
                    doc.add_heading("Questions the audience still wants to know", level=3)
                    for q in open_q[:10]:
                        doc.add_paragraph(f"- {q}")
        # Audience psychology
        audience = plan_obj.get("audience_psychology")
        if audience:
            doc.add_heading("Audience psychology", level=2)
            if audience.get("summary"):
                doc.add_paragraph(audience["summary"]) 
            for t in (audience.get("themes") or [])[:8]:
                theme = t.get("theme") or "Theme"
                why = t.get("why") or ""
                doc.add_paragraph(f"- {theme}: {why}")
                for c in t.get("citations", [])[:3]:
                    doc.add_paragraph(f"  - {c}")
        # Insights & data
        insights = plan_obj.get("insights_data")
        if insights:
            doc.add_heading("Insights & data", level=2)
            for it in insights[:10]:
                head = it.get("headline") or "Insight"
                det = it.get("detail") or ""
                conf = it.get("confidence") or ""
                badge = f" (confidence: {conf})" if conf else ""
                doc.add_paragraph(f"- {head}{badge}")
                if det:
                    doc.add_paragraph(f"  - {det}")
                for c in (it.get("citations") or [])[:3]:
                    doc.add_paragraph(f"  - {c}")
    else:
        doc.add_paragraph("Not available. Run Agent 3 to generate the plan.")

    # Comment analysis (if present)
    comment_analysis = _read_json(guest_dir / "agent3" / "comment_analysis.json")
    if comment_analysis:
        doc.add_heading("Comment analysis", level=1)
        overall = comment_analysis.get("overall_sentiment") or {}
        if overall:
            doc.add_heading("Overall sentiment", level=2)
            if overall.get("summary"):
                doc.add_paragraph(overall["summary"]) 
            parts = []
            if overall.get("positive_pct") is not None:
                parts.append(f"positive: {overall.get('positive_pct')}%")
            if overall.get("neutral_pct") is not None:
                parts.append(f"neutral: {overall.get('neutral_pct')}%")
            if overall.get("negative_pct") is not None:
                parts.append(f"negative: {overall.get('negative_pct')}%")
            if parts:
                doc.add_paragraph("(" + ", ".join(parts) + ")")
        topics = comment_analysis.get("hot_topics") or []
        if topics:
            doc.add_heading("Hot topics", level=2)
            for t in topics[:8]:
                doc.add_paragraph(f"- {t.get('topic')}: {t.get('why')}")
                if t.get("example_quote"):
                    doc.add_paragraph(f"  - \"{t.get('example_quote')}\"")
        controversies = comment_analysis.get("controversies") or []
        if controversies:
            doc.add_heading("Controversies", level=2)
            for c in controversies[:6]:
                doc.add_paragraph(f"- {c.get('issue')}: {c.get('sides')}")
                if c.get("example_quote"):
                    doc.add_paragraph(f"  - \"{c.get('example_quote')}\"")
        open_q = comment_analysis.get("open_questions") or []
        if open_q:
            doc.add_heading("Open questions from viewers", level=2)
            for q in open_q[:10]:
                doc.add_paragraph(f"- {q}")
        top = comment_analysis.get("top_comments") or []
        if top:
            doc.add_heading("Top comments (by likes)", level=2)
            for c in top[:8]:
                doc.add_paragraph(f"- {c.get('likes')} likes – {c.get('quote')}")
        stats = comment_analysis.get("stats") or {}
        if stats:
            doc.add_paragraph(f"Analyzed {stats.get('sample_size')} of {stats.get('total_comments')} comments.")

    out_path = guest_dir / "final_report.docx"
    # Ensure correct .docx write
    doc.save(str(out_path))
    return out_path


