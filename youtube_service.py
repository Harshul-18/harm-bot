"""Maintained YouTube Data API integration used by every app page."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import requests


API_BASE_URL = "https://www.googleapis.com/youtube/v3"
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHANNEL_ID_PATTERN = re.compile(r"^UC[A-Za-z0-9_-]{22}$")

YOUTUBE_CATEGORIES = {
    "1": "Film & Animation",
    "2": "Autos & Vehicles",
    "10": "Music",
    "15": "Pets & Animals",
    "17": "Sports",
    "19": "Travel & Events",
    "20": "Gaming",
    "22": "People & Blogs",
    "23": "Comedy",
    "24": "Entertainment",
    "25": "News & Politics",
    "26": "How-to & Style",
    "27": "Education",
    "28": "Science & Technology",
    "29": "Nonprofits & Activism",
}


class YouTubeServiceError(RuntimeError):
    """A user-facing YouTube API failure."""


@dataclass(frozen=True)
class VideoData:
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_name: str
    category: str

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.video_id}"

    @property
    def prediction_text(self) -> str:
        return f"{self.title} {self.description}".strip()


def extract_video_id(value: str) -> str:
    """Extract an 11-character YouTube video ID from common URL forms."""
    candidate = value.strip()
    if VIDEO_ID_PATTERN.fullmatch(candidate):
        return candidate

    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    host = parsed.netloc.lower().split(":")[0]
    path_parts = [part for part in parsed.path.split("/") if part]

    if host in {"youtu.be", "www.youtu.be"} and path_parts:
        candidate = path_parts[0]
    elif host.endswith("youtube.com"):
        if parsed.path == "/watch":
            candidate = parse_qs(parsed.query).get("v", [""])[0]
        elif path_parts and path_parts[0] in {"embed", "shorts", "live"}:
            candidate = path_parts[1] if len(path_parts) > 1 else ""

    if not VIDEO_ID_PATTERN.fullmatch(candidate):
        raise YouTubeServiceError("Please enter a valid YouTube video URL or video ID.")
    return candidate


def extract_playlist_id(value: str) -> str:
    """Extract a playlist ID from a URL or accept a raw playlist ID."""
    candidate = value.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{10,80}", candidate) and "youtube" not in candidate:
        return candidate
    parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
    playlist_id = parse_qs(parsed.query).get("list", [""])[0]
    if not playlist_id:
        raise YouTubeServiceError("Please enter a valid YouTube playlist URL or ID.")
    return playlist_id


class YouTubeService:
    def __init__(self, api_key: str, timeout: int = 20) -> None:
        if not api_key.strip():
            raise YouTubeServiceError(
                "YouTube API access is not configured. Add YOUTUBE_API_KEY to "
                "Streamlit secrets."
            )
        self.api_key = api_key.strip()
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, endpoint: str, **params: object) -> dict:
        response = self.session.get(
            f"{API_BASE_URL}/{endpoint}",
            params={**params, "key": self.api_key},
            timeout=self.timeout,
        )
        try:
            payload = response.json()
        except ValueError as exc:
            raise YouTubeServiceError("YouTube returned an unreadable response.") from exc
        if not response.ok:
            message = payload.get("error", {}).get("message", "YouTube request failed.")
            raise YouTubeServiceError(message)
        return payload

    @staticmethod
    def _video_from_item(item: dict) -> VideoData:
        snippet = item.get("snippet", {})
        video_id = item.get("id", "")
        if isinstance(video_id, dict):
            video_id = video_id.get("videoId", "")
        return VideoData(
            video_id=video_id,
            title=snippet.get("title", "Untitled video"),
            description=snippet.get("description", ""),
            channel_id=snippet.get("channelId", ""),
            channel_name=snippet.get("channelTitle", "Unknown channel"),
            category=YOUTUBE_CATEGORIES.get(snippet.get("categoryId", ""), "Unknown"),
        )

    def get_video(self, value: str) -> VideoData:
        video_id = extract_video_id(value)
        payload = self._get("videos", part="snippet", id=video_id)
        items = payload.get("items", [])
        if not items:
            raise YouTubeServiceError("That video was not found or is not public.")
        return self._video_from_item(items[0])

    def get_videos(self, video_ids: list[str]) -> list[VideoData]:
        results: list[VideoData] = []
        for start in range(0, len(video_ids), 50):
            chunk = video_ids[start : start + 50]
            payload = self._get("videos", part="snippet", id=",".join(chunk))
            by_id = {
                item["id"]: self._video_from_item(item)
                for item in payload.get("items", [])
            }
            results.extend(by_id[video_id] for video_id in chunk if video_id in by_id)
        return results

    def search_videos(self, query: str, limit: int) -> list[VideoData]:
        payload = self._get(
            "search",
            part="snippet",
            q=query,
            type="video",
            maxResults=max(1, min(int(limit), 50)),
            safeSearch="moderate",
        )
        return [
            self._video_from_item(item)
            for item in payload.get("items", [])
            if item.get("id", {}).get("videoId")
        ]

    def get_playlist_videos(self, value: str) -> list[VideoData]:
        playlist_id = extract_playlist_id(value)
        video_ids: list[str] = []
        page_token: str | None = None
        while True:
            params: dict[str, object] = {
                "part": "contentDetails",
                "playlistId": playlist_id,
                "maxResults": 50,
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._get("playlistItems", **params)
            video_ids.extend(
                item.get("contentDetails", {}).get("videoId", "")
                for item in payload.get("items", [])
            )
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        video_ids = [video_id for video_id in video_ids if video_id]
        if not video_ids:
            raise YouTubeServiceError("No public videos were found in that playlist.")
        return self.get_videos(video_ids)

    def resolve_channel_id(self, value: str) -> str:
        candidate = value.strip()
        if CHANNEL_ID_PATTERN.fullmatch(candidate):
            return candidate

        try:
            return self.get_video(candidate).channel_id
        except YouTubeServiceError:
            pass

        parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "channel" and CHANNEL_ID_PATTERN.fullmatch(parts[1]):
            return parts[1]

        if parts and parts[0].startswith("@"):
            payload = self._get("channels", part="id", forHandle=parts[0][1:])
            items = payload.get("items", [])
            if items:
                return items[0]["id"]

        if len(parts) >= 2 and parts[0] == "user":
            payload = self._get("channels", part="id", forUsername=parts[1])
            items = payload.get("items", [])
            if items:
                return items[0]["id"]

        query = parts[-1] if parts else candidate.lstrip("@")
        payload = self._get(
            "search", part="snippet", q=query, type="channel", maxResults=1
        )
        items = payload.get("items", [])
        if not items:
            raise YouTubeServiceError("That YouTube channel could not be found.")
        return items[0]["id"]["channelId"]

    def get_channel_videos(self, value: str, limit: int) -> list[VideoData]:
        channel_id = self.resolve_channel_id(value)
        channel_payload = self._get(
            "channels", part="contentDetails", id=channel_id
        )
        items = channel_payload.get("items", [])
        if not items:
            raise YouTubeServiceError("That YouTube channel could not be found.")
        uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]

        video_ids: list[str] = []
        page_token: str | None = None
        requested = max(1, int(limit))
        while len(video_ids) < requested:
            params: dict[str, object] = {
                "part": "contentDetails",
                "playlistId": uploads_id,
                "maxResults": min(50, requested - len(video_ids)),
            }
            if page_token:
                params["pageToken"] = page_token
            payload = self._get("playlistItems", **params)
            video_ids.extend(
                item.get("contentDetails", {}).get("videoId", "")
                for item in payload.get("items", [])
            )
            page_token = payload.get("nextPageToken")
            if not page_token:
                break
        return self.get_videos([video_id for video_id in video_ids if video_id])
