"""Keyless, dual-provider YouTube metadata integration.

yt-dlp is the primary extractor. PyTubeFix is an independent fallback for
temporary parser breakages. Both use public YouTube web surfaces, so failures
are handled explicitly and surfaced without crashing the Streamlit session.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from itertools import islice
from urllib.parse import parse_qs, urlparse

from pytubefix import Channel, Playlist, Search, YouTube
from yt_dlp import YoutubeDL


LOGGER = logging.getLogger(__name__)
VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
CHANNEL_ID_PATTERN = re.compile(r"^UC[A-Za-z0-9_-]{22}$")


class YouTubeServiceError(RuntimeError):
    """A user-facing failure from both keyless extraction providers."""


@dataclass(frozen=True)
class VideoData:
    video_id: str
    title: str
    description: str
    channel_id: str
    channel_name: str
    category: str
    provider: str = "unknown"
    duration_seconds: int | None = None

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


def _safe_attribute(instance: object, name: str, default: object = "") -> object:
    try:
        value = getattr(instance, name)
        return default if value is None else value
    except Exception:
        return default


def _optional_duration(value: object) -> int | None:
    try:
        seconds = int(value)
        return seconds if seconds > 0 else None
    except (TypeError, ValueError):
        return None


class _QuietYtDlpLogger:
    def debug(self, message: str) -> None:
        return None

    def warning(self, message: str) -> None:
        LOGGER.debug("yt-dlp: %s", message)

    def error(self, message: str) -> None:
        LOGGER.debug("yt-dlp: %s", message)


class YouTubeService:
    """Fetch YouTube data without a developer API key."""

    def __init__(self, timeout: int = 20, retries: int = 3) -> None:
        self.timeout = timeout
        self.retries = retries

    def _extract_with_ytdlp(
        self,
        value: str,
        *,
        flat: bool,
        limit: int | None = None,
    ) -> dict:
        options: dict[str, object] = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "socket_timeout": self.timeout,
            "retries": self.retries,
            "extractor_retries": self.retries,
            "cachedir": False,
            "logger": _QuietYtDlpLogger(),
            "extract_flat": flat,
        }
        if limit is not None:
            options["playlistend"] = limit
        with YoutubeDL(options) as extractor:
            result = extractor.extract_info(value, download=False)
        if not result:
            raise YouTubeServiceError("YouTube returned no public results.")
        return result

    @staticmethod
    def _video_from_ytdlp(info: dict) -> VideoData:
        video_id = str(info.get("id") or "")
        if not VIDEO_ID_PATTERN.fullmatch(video_id):
            url = str(info.get("webpage_url") or info.get("url") or "")
            video_id = extract_video_id(url)
        categories = info.get("categories") or []
        category = str(categories[0]) if categories else "Unknown"
        duration = info.get("duration")
        return VideoData(
            video_id=video_id,
            title=str(info.get("title") or "Untitled video"),
            description=str(info.get("description") or ""),
            channel_id=str(info.get("channel_id") or info.get("uploader_id") or ""),
            channel_name=str(info.get("channel") or info.get("uploader") or "Unknown channel"),
            category=category,
            provider="yt-dlp",
            duration_seconds=_optional_duration(duration),
        )

    @staticmethod
    def _video_from_pytubefix(video: YouTube) -> VideoData:
        video_id = str(_safe_attribute(video, "video_id"))
        if not VIDEO_ID_PATTERN.fullmatch(video_id):
            video_id = extract_video_id(str(_safe_attribute(video, "watch_url")))
        return VideoData(
            video_id=video_id,
            title=str(_safe_attribute(video, "title", "Untitled video")),
            description=str(_safe_attribute(video, "description")),
            channel_id=str(_safe_attribute(video, "channel_id")),
            channel_name=str(_safe_attribute(video, "author", "Unknown channel")),
            category="Unknown",
            provider="pytubefix",
            duration_seconds=_optional_duration(_safe_attribute(video, "length", 0)),
        )

    @staticmethod
    def _entries(info: dict, limit: int | None = None) -> list[dict]:
        entries = [entry for entry in (info.get("entries") or []) if entry]
        return entries if limit is None else entries[:limit]

    @lru_cache(maxsize=256)
    def get_video(self, value: str) -> VideoData:
        video_id = extract_video_id(value)
        url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            return self._video_from_ytdlp(
                self._extract_with_ytdlp(url, flat=False)
            )
        except Exception as primary_error:
            LOGGER.warning("yt-dlp video extraction failed: %s", primary_error)
            try:
                return self._video_from_pytubefix(YouTube(url))
            except Exception as fallback_error:
                LOGGER.warning("PyTubeFix video extraction failed: %s", fallback_error)
                raise YouTubeServiceError(
                    "This video could not be read by either keyless provider. "
                    "YouTube may be temporarily blocking automated requests."
                ) from fallback_error

    def _search_with_pytubefix(self, query: str, limit: int) -> list[VideoData]:
        videos = list(islice(Search(query).videos, limit))
        return [self._video_from_pytubefix(video) for video in videos]

    @lru_cache(maxsize=64)
    def _search_cached(self, query: str, limit: int) -> tuple[VideoData, ...]:
        requested = max(1, min(int(limit), 50))
        try:
            info = self._extract_with_ytdlp(
                f"ytsearch{requested}:{query}", flat=True, limit=requested
            )
            videos = [
                self._video_from_ytdlp(entry)
                for entry in self._entries(info, requested)
            ]
            if videos:
                return tuple(videos)
        except Exception as primary_error:
            LOGGER.warning("yt-dlp search failed: %s", primary_error)
        try:
            return tuple(self._search_with_pytubefix(query, requested))
        except Exception as fallback_error:
            LOGGER.warning("PyTubeFix search failed: %s", fallback_error)
            raise YouTubeServiceError(
                "YouTube search is temporarily unavailable from both keyless providers."
            ) from fallback_error

    def search_videos(self, query: str, limit: int) -> list[VideoData]:
        if not query.strip():
            return []
        return list(self._search_cached(query.strip(), int(limit)))

    def _playlist_with_pytubefix(self, url: str) -> list[VideoData]:
        return [self._video_from_pytubefix(video) for video in Playlist(url).videos]

    @lru_cache(maxsize=32)
    def _playlist_cached(self, playlist_id: str) -> tuple[VideoData, ...]:
        url = f"https://www.youtube.com/playlist?list={playlist_id}"
        try:
            info = self._extract_with_ytdlp(url, flat=True)
            videos = [
                self._video_from_ytdlp(entry) for entry in self._entries(info)
            ]
            if videos:
                return tuple(videos)
        except Exception as primary_error:
            LOGGER.warning("yt-dlp playlist extraction failed: %s", primary_error)
        try:
            videos = self._playlist_with_pytubefix(url)
            if videos:
                return tuple(videos)
        except Exception as fallback_error:
            LOGGER.warning("PyTubeFix playlist extraction failed: %s", fallback_error)
            raise YouTubeServiceError(
                "This playlist could not be read by either keyless provider."
            ) from fallback_error
        raise YouTubeServiceError("No public videos were found in that playlist.")

    def get_playlist_videos(self, value: str) -> list[VideoData]:
        return list(self._playlist_cached(extract_playlist_id(value)))

    def _channel_url(self, value: str) -> str:
        candidate = value.strip().rstrip("/")
        if CHANNEL_ID_PATTERN.fullmatch(candidate):
            return f"https://www.youtube.com/channel/{candidate}/videos"
        try:
            video_id = extract_video_id(candidate)
            channel_id = self.get_video(video_id).channel_id
            if channel_id:
                return f"https://www.youtube.com/channel/{channel_id}/videos"
        except YouTubeServiceError:
            pass

        parsed = urlparse(candidate if "://" in candidate else f"https://{candidate}")
        if parsed.netloc.lower().endswith("youtube.com"):
            path = parsed.path.rstrip("/")
            if not path:
                raise YouTubeServiceError("Please enter a valid YouTube channel.")
            if path.split("/")[-1] not in {"videos", "shorts", "streams"}:
                path = f"{path}/videos"
            return f"https://www.youtube.com{path}"
        handle = candidate.lstrip("@")
        if not handle or "/" in handle:
            raise YouTubeServiceError("Please enter a valid YouTube channel URL or handle.")
        return f"https://www.youtube.com/@{handle}/videos"

    def _channel_with_pytubefix(self, url: str, limit: int) -> list[VideoData]:
        videos = islice(Channel(url).videos, limit)
        return [self._video_from_pytubefix(video) for video in videos]

    @lru_cache(maxsize=64)
    def _channel_cached(self, url: str, limit: int) -> tuple[VideoData, ...]:
        requested = max(1, int(limit))
        try:
            info = self._extract_with_ytdlp(url, flat=True, limit=requested)
            videos = [
                self._video_from_ytdlp(entry)
                for entry in self._entries(info, requested)
            ]
            if videos:
                return tuple(videos)
        except Exception as primary_error:
            LOGGER.warning("yt-dlp channel extraction failed: %s", primary_error)
        try:
            videos = self._channel_with_pytubefix(url, requested)
            if videos:
                return tuple(videos)
        except Exception as fallback_error:
            LOGGER.warning("PyTubeFix channel extraction failed: %s", fallback_error)
            raise YouTubeServiceError(
                "This channel could not be read by either keyless provider."
            ) from fallback_error
        raise YouTubeServiceError("No public videos were found for this channel.")

    def get_channel_videos(self, value: str, limit: int) -> list[VideoData]:
        return list(self._channel_cached(self._channel_url(value), int(limit)))
