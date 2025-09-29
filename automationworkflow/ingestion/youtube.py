import os
from typing import List, Dict, Optional
from datetime import datetime

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except Exception:
    YouTubeTranscriptApi = None  # type: ignore

import requests


class YouTubeIngestor:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")

    @property
    def comments_enabled(self) -> bool:
        return bool(self.api_key)

    def search_videos(self, query: str, max_results: int = 5) -> List[Dict]:
        if not self.api_key:
            return []
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "key": self.api_key,
        }
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        videos = []
        for item in data.get("items", []):
            videos.append({
                "source_type": "youtube_video",
                "video_id": item["id"]["videoId"],
                "title": item["snippet"].get("title"),
                "channel": item["snippet"].get("channelTitle"),
                "published_at": item["snippet"].get("publishedAt"),
                "url": f"https://www.youtube.com/watch?v={item['id']['videoId']}",
            })
        return videos

    def fetch_transcript(self, video_id: str) -> Optional[Dict]:
        if not YouTubeTranscriptApi:
            return None
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            text = " ".join([t.get("text", "") for t in transcript])
            return {
                "source_type": "youtube_transcript",
                "video_id": video_id,
                "text": text,
                "fetched_at": datetime.utcnow().isoformat(),
                "url": f"https://www.youtube.com/watch?v={video_id}",
            }
        except Exception:
            return None

    def fetch_comments(self, video_id: str, max_comments: int = 200, include_replies: bool = False, order: str = "relevance") -> List[Dict]:
        if not self.api_key:
            return []
        url = "https://www.googleapis.com/youtube/v3/commentThreads"
        params = {
            "part": "snippet,replies" if include_replies else "snippet",
            "videoId": video_id,
            "maxResults": 100,
            "order": order,
            "key": self.api_key,
        }
        comments: List[Dict] = []
        next_page = None
        while True:
            if next_page:
                params["pageToken"] = next_page
            try:
                r = requests.get(url, params=params, timeout=30)
                if r.status_code == 403:
                    # Gracefully degrade on forbidden/quota/comments disabled
                    try:
                        data = r.json()
                        reason = ((data.get("error", {}).get("errors") or [{}])[0]).get("reason", "")
                        if reason in ("commentsDisabled", "forbidden", "quotaExceeded", "keyInvalid", "dailyLimitExceeded"):
                            return comments
                    except Exception:
                        return comments
                r.raise_for_status()
            except Exception:
                return comments
            data = r.json()
            for item in data.get("items", []):
                top = item["snippet"]["topLevelComment"]["snippet"]
                comment_id = item["id"]
                comments.append({
                    "source_type": "youtube_comment",
                    "video_id": video_id,
                    "comment_id": comment_id,
                    "text": top.get("textDisplay", ""),
                    "author": top.get("authorDisplayName"),
                    "like_count": top.get("likeCount", 0),
                    "reply_count": item["snippet"].get("totalReplyCount", 0),
                    "published_at": top.get("publishedAt"),
                    "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                })
                if include_replies:
                    for rep in item.get("replies", {}).get("comments", []):
                        rep_snip = rep.get("snippet", {})
                        rid = rep.get("id")
                        comments.append({
                            "source_type": "youtube_comment_reply",
                            "video_id": video_id,
                            "comment_id": rid,
                            "text": rep_snip.get("textDisplay", ""),
                            "author": rep_snip.get("authorDisplayName"),
                            "like_count": rep_snip.get("likeCount", 0),
                            "reply_count": 0,
                            "published_at": rep_snip.get("publishedAt"),
                            "url": f"https://www.youtube.com/watch?v={video_id}&lc={rid}",
                        })
                if len(comments) >= max_comments:
                    return comments[:max_comments]
            next_page = data.get("nextPageToken")
            if not next_page:
                break
        return comments


