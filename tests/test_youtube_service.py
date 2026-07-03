from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from youtube_service import (
    YouTubeService,
    YouTubeServiceError,
    extract_playlist_id,
    extract_video_id,
)


VIDEO_INFO = {
    "id": "rfscVS0vtbw",
    "title": "Learn Python",
    "description": "A complete course",
    "channel_id": "UC123",
    "channel": "Example Channel",
    "categories": ["Education"],
}


class IdentifierTests(unittest.TestCase):
    def test_extracts_common_video_urls(self) -> None:
        video_id = "UOD4_4op2-k"
        values = [
            video_id,
            f"https://www.youtube.com/watch?v={video_id}",
            f"https://youtu.be/{video_id}",
            f"https://www.youtube.com/shorts/{video_id}",
            f"https://www.youtube.com/embed/{video_id}",
        ]
        self.assertEqual([extract_video_id(value) for value in values], [video_id] * 5)

    def test_rejects_invalid_video_url(self) -> None:
        with self.assertRaises(YouTubeServiceError):
            extract_video_id("https://example.com/not-youtube")

    def test_extracts_playlist_id(self) -> None:
        playlist_id = "PL-osiE80TeTt2d9bfVyTiXJA-UTHn6WwU"
        self.assertEqual(
            extract_playlist_id(
                f"https://www.youtube.com/playlist?list={playlist_id}"
            ),
            playlist_id,
        )


class YouTubeServiceTests(unittest.TestCase):
    def test_video_uses_ytdlp_and_normalizes_metadata(self) -> None:
        service = YouTubeService()
        service._extract_with_ytdlp = Mock(return_value=VIDEO_INFO)
        video = service.get_video("UOD4_4op2-k")
        self.assertEqual(video.title, "Learn Python")
        self.assertEqual(video.category, "Education")
        self.assertEqual(video.provider, "yt-dlp")
        self.assertEqual(video.url, "https://www.youtube.com/watch?v=UOD4_4op2-k")

    def test_video_falls_back_to_pytubefix(self) -> None:
        service = YouTubeService()
        service._extract_with_ytdlp = Mock(side_effect=RuntimeError("primary failed"))
        fallback = Mock(
            video_id="UOD4_4op2-k",
            title="Fallback title",
            description="Fallback description",
            channel_id="UC123",
            author="Fallback Channel",
        )
        with patch("youtube_service.YouTube", return_value=fallback):
            video = service.get_video("UOD4_4op2-k")
        self.assertEqual(video.title, "Fallback title")
        self.assertEqual(video.provider, "pytubefix")

    def test_search_uses_flat_keyless_results(self) -> None:
        service = YouTubeService()
        service._extract_with_ytdlp = Mock(
            return_value={"entries": [VIDEO_INFO, {**VIDEO_INFO, "id": "dQw4w9WgXcQ"}]}
        )
        videos = service.search_videos("python tutorial", 2)
        self.assertEqual([video.video_id for video in videos], ["UOD4_4op2-k", "dQw4w9WgXcQ"])
        call_value = service._extract_with_ytdlp.call_args.args[0]
        self.assertEqual(call_value, "ytsearch2:python tutorial")

    def test_playlist_returns_all_public_flat_entries(self) -> None:
        service = YouTubeService()
        service._extract_with_ytdlp = Mock(
            return_value={"entries": [VIDEO_INFO, {**VIDEO_INFO, "id": "dQw4w9WgXcQ"}]}
        )
        videos = service.get_playlist_videos("PL1234567890")
        self.assertEqual(len(videos), 2)
        self.assertTrue(
            service._extract_with_ytdlp.call_args.args[0].endswith("PL1234567890")
        )

    def test_channel_accepts_handle_and_honors_limit(self) -> None:
        service = YouTubeService()
        service._extract_with_ytdlp = Mock(
            return_value={"entries": [VIDEO_INFO, {**VIDEO_INFO, "id": "dQw4w9WgXcQ"}]}
        )
        videos = service.get_channel_videos("@freecodecamp", 1)
        self.assertEqual(len(videos), 1)
        self.assertEqual(
            service._extract_with_ytdlp.call_args.args[0],
            "https://www.youtube.com/@freecodecamp/videos",
        )


if __name__ == "__main__":
    unittest.main()
