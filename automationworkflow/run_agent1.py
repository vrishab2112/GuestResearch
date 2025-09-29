import argparse
import os
from pathlib import Path
from datetime import datetime, timezone

from ingestion.youtube import YouTubeIngestor
from ingestion.web import WebIngestor
from ingestion.tavily import TavilyClient
from utils.io import write_jsonl, ensure_dir
from utils.normalize import ChunkNormalizer, compute_text_hash
from urllib.parse import urlparse
from storage.sqlite_store import SQLiteStore

try:
    # Load environment variables from automationworkflow/.env if present
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env")
except Exception:
    pass

def run_agent1(guest: str, max_videos: int, max_comments: int, include_replies: bool, sort: str, max_web_results: int):

    timestamp = datetime.now(timezone.utc).isoformat()
    base_dir = Path(__file__).parent
    out_dir = base_dir / "outputs" / guest
    raw_dir = out_dir / "raw"
    ensure_dir(raw_dir)

    records = []

    web = WebIngestor()
    web_results = web.search_and_fetch(guest, max_results=max_web_results)
    categories = web.categorized_discovery(guest)
    # Guarantee some web articles: fetch from categories if initial pass produced none
    if not web_results:
        cat_fetch = web.fetch_from_categories(categories, per_category_fetch=3)
        web_results.extend(cat_fetch)

    tavily = TavilyClient()
    overview = tavily.search_overview(guest, max_results=8)
    books_articles = tavily.search_books_and_articles(guest, max_results=12)
    social_handles = tavily.search_social_handles(guest, max_results=10)
    records.extend(web_results)

    yt_api_key = os.getenv("YOUTUBE_API_KEY") or ""
    yt = YouTubeIngestor(api_key=yt_api_key or None)
    # Try multiple query variants if too few videos
    videos = yt.search_videos(guest, max_results=max_videos)
    if len(videos) < max(1, max_videos // 2):
        alt_queries = [f"{guest} interview", f"{guest} podcast", f"{guest} talk"]
        for q in alt_queries:
            extra = yt.search_videos(q, max_results=max_videos)
            # de-duplicate by video_id
            seen_ids = {v.get("video_id") for v in videos}
            for v in extra:
                if v.get("video_id") not in seen_ids:
                    videos.append(v)
                    seen_ids.add(v.get("video_id"))
            if len(videos) >= max_videos:
                break
    for v in videos:
        records.append(v)
        transcript = yt.fetch_transcript(v.get("video_id"))
        if transcript:
            records.append(transcript)
        comments = []
        if yt.comments_enabled:
            comments = yt.fetch_comments(v.get("video_id"), max_comments=max_comments, include_replies=include_replies, order=sort)
            records.extend(comments)

    # Also add Tavily results for traceability
    tavily_records = []
    for r in overview + books_articles + social_handles:
        tavily_records.append({
            "source_type": "tavily_result",
            "title": r.get("title"),
            "url": r.get("url"),
            "text": r.get("content"),
        })
    records.extend(tavily_records)
    # Write YouTube-only dataset
    youtube_records = [
        r for r in records
        if r.get("source_type") in ("youtube_video", "youtube_transcript", "youtube_comment", "youtube_comment_reply")
    ]
    write_jsonl(raw_dir / "youtube.jsonl", youtube_records)

    # Write web.jsonl with metadata; include web_article and fallback web_link entries
    web_articles = [r for r in web_results if r.get("source_type") == "web_article"]
    if not web_articles:
        # If no fetched articles, try fetching from categories to populate
        web_results.extend(web.fetch_from_categories(categories, per_category_fetch=3))
        web_articles = [r for r in web_results if r.get("source_type") == "web_article"]

    web_enriched = []
    for r in web_results:
        if r.get("source_type") == "web_article":
            text = r.get("text") or ""
            domain = urlparse(r.get("url") or "").netloc
            web_enriched.append({
                **r,
                "domain": domain,
                "text_hash": compute_text_hash(text),
                "estimated_tokens": max(1, len(text) // 4),
            })
        elif r.get("source_type") == "web_link":
            domain = urlparse(r.get("url") or "").netloc
            web_enriched.append({
                **r,
                "domain": domain,
                "text_hash": "",
                "estimated_tokens": 0,
            })
    write_jsonl(out_dir / "web.jsonl", web_enriched)

    normalizer = ChunkNormalizer()
    chunks = normalizer.normalize(records, guest=guest)
    write_jsonl(out_dir / "chunks.jsonl", chunks)

    # Summary file with requested sections
    # Build about_guest from multiple sources: Wikipedia + personal site + blogs + top web articles
    about_sources = []
    # Wikipedia top result (prefer English domain)
    if categories.get("wikipedia"):
        for url in categories["wikipedia"][:1]:
            try:
                doc = web.fetch_url(url)
                about_sources.append({"url": url, "title": doc.get("title"), "text": doc.get("text", "")})
            except Exception:
                pass
    # Personal sites (first one)
    if categories.get("personal"):
        for url in categories["personal"][:1]:
            try:
                doc = web.fetch_url(url)
                about_sources.append({"url": url, "title": doc.get("title"), "text": doc.get("text", "")})
            except Exception:
                pass
    # Blogs (first one)
    if categories.get("blogs"):
        for url in categories["blogs"][:1]:
            try:
                doc = web.fetch_url(url)
                about_sources.append({"url": url, "title": doc.get("title"), "text": doc.get("text", "")})
            except Exception:
                pass
    # Fallback to top fetched articles (avoid non-English domains for About)
    if web_results:
        picked = []
        for rec in web_results:
            if rec.get("source_type") != "web_article":
                continue
            u = rec.get("url") or ""
            # Prefer .com/.org/.edu and avoid obvious non-English top-levels when possible
            if any(tld in u for tld in (".com", ".org", ".edu", ".gov")) and not any(tld in u for tld in (".ru", ".cn", ".jp", ".it", ".de", ".fr")):
                picked.append(rec)
            if len(picked) >= 2:
                break
        if not picked:
            picked = [r for r in web_results if r.get("source_type") == "web_article"][:2]
        for rec in picked:
            about_sources.append({"url": rec.get("url"), "title": rec.get("title"), "text": rec.get("text", "")})

    about_intro_parts = []
    for s in about_sources:
        t = (s.get("text") or "").strip()
        if not t:
            continue
        about_intro_parts.append(t[:400])
        if len(" ".join(about_intro_parts)) > 1200:
            break
    about_guest = {
        "summary": " ".join(about_intro_parts)[:1400],
        "sources": [{"url": s.get("url"), "title": s.get("title")} for s in about_sources],
    }

    # If summary is still empty, fall back to Tavily overview URLs by fetching page text
    if not about_guest.get("summary") and overview:
        fetched_overview = []
        for r in overview[:3]:
            u = r.get("url")
            if not u:
                continue
            doc = web.safe_fetch(u)
            fetched_overview.append({"url": u, "title": doc.get("title"), "text": doc.get("text", "")})
        parts = []
        for s in fetched_overview:
            txt = (s.get("text") or "").strip()
            if not txt:
                continue
            parts.append(txt[:400])
            if len(" ".join(parts)) > 1200:
                break
        if parts:
            about_guest = {
                "summary": " ".join(parts)[:1400],
                "sources": [{"url": s.get("url"), "title": s.get("title")} for s in fetched_overview],
            }

    summary = {
        "/youtube_research": {
            "videos": [v for v in records if v.get("source_type") == "youtube_video"],
            "comments_count": sum(1 for r in records if r.get("source_type") in ("youtube_comment", "youtube_comment_reply")),
            "transcripts_count": sum(1 for r in records if r.get("source_type") == "youtube_transcript"),
        },
        "/books_written": categories.get("books", []) or [r.get("url") for r in books_articles],
        "/blogs": categories.get("blogs", []),
        "/personal_sites": categories.get("personal", []),
        "/wikipedia": categories.get("wikipedia", []),
        "/news_interviews": categories.get("news", []),
        "/social_bio": categories.get("social", []) or [r.get("url") for r in social_handles],
        "/podcasts": categories.get("podcasts", []),
        "/about_guest": about_guest or {"summary": (" ".join([r.get("content") or "" for r in overview])[:1400]), "sources": [{"url": r.get("url"), "title": r.get("title")} for r in overview]},
        "/web_articles_fetched": [r.get("url") for r in web_results if r.get("source_type") == "web_article"],
    }
    # Dedicated files as requested (summary file omitted by user preference)
    write_jsonl(out_dir / "about_guest.jsonl", [summary.get("/about_guest", {})])
    write_jsonl(out_dir / "books_written.jsonl", [{"url": u} for u in summary.get("/books_written", [])])
    write_jsonl(out_dir / "social_bio.jsonl", [{"url": u} for u in summary.get("/social_bio", [])])

    # Persist to SQLite database for future agents/chatbot
    store = SQLiteStore(out_dir / "db.sqlite")
    guest_id = store.ensure_guest(guest)
    store.upsert_records(guest_id, records)
    store.upsert_links(guest_id, "books_written", summary.get("/books_written", []))
    store.upsert_links(guest_id, "social_bio", summary.get("/social_bio", []))
    store.upsert_about(guest_id, (summary.get("/about_guest") or {}).get("summary"))

    return {
        "web_records": len(web_results),
        "videos": len(videos),
        "total_records": len(records),
        "chunks": len(chunks),
        "output_dir": str(out_dir),
        "timestamp": timestamp,
        "comments_skipped": not yt.comments_enabled,
        "comments_count": sum(1 for r in records if r.get("source_type") in ("youtube_comment", "youtube_comment_reply")),
        # web_summary_sections omitted since summary.jsonl is not written
        "tavily_enabled": bool(tavily.api_key),
        "sqlite_path": str(out_dir / "db.sqlite"),
    }


def main():
    parser = argparse.ArgumentParser(description="Agent 1 – Data Gathering for guest research")
    parser.add_argument("--guest", required=True, help="Guest name or query")
    parser.add_argument("--max-videos", type=int, default=5)
    parser.add_argument("--max-comments", type=int, default=200)
    parser.add_argument("--include-replies", action="store_true")
    parser.add_argument("--sort", choices=["relevance", "time"], default="relevance")
    parser.add_argument("--max-web-results", type=int, default=10)
    args = parser.parse_args()

    stats = run_agent1(
        guest=args.guest,
        max_videos=args.max_videos,
        max_comments=args.max_comments,
        include_replies=args.include_replies,
        sort=args.sort,
        max_web_results=args.max_web_results,
    )
    print(stats)


if __name__ == "__main__":
    main()


