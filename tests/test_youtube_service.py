from __future__ import annotations

import unittest

from youtube_service import (
    YouTubeService,
    YouTubeServiceError,
    extract_playlist_id,
    extract_video_id,
)


class FakeResponse:
    def __init__(self, payload: dict, ok: bool = True) -> None:
        self.payload = payload
        self.ok = ok

    def json(self) -> dict:
        return self.payload


class FakeSession:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = iter(responses)
        self.calls: list[tuple[str, dict, int]] = []

    def get(self, url: str, params: dict, timeout: int) -> FakeResponse:
        self.calls.append((url, params, timeout))
        return FakeResponse(next(self.responses))


class IdentifierTests(unittest.TestCase):
    def test_extracts_common_video_urls(self) -> None:
        video_id = "rfscVS0vtbw"
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
    def test_video_response_is_normalized(self) -> None:
        service = YouTubeService("test-key")
        service.session = FakeSession(
            [
                {
                    "items": [
                        {
                            "id": "rfscVS0vtbw",
                            "snippet": {
                                "title": "Learn Python",
                                "description": "A complete course",
                                "channelId": "UC123",
                                "channelTitle": "Example Channel",
                                "categoryId": "27",
                            },
                        }
                    ]
                }
            ]
        )
        video = service.get_video("rfscVS0vtbw")
        self.assertEqual(video.title, "Learn Python")
        self.assertEqual(video.category, "Education")
        self.assertEqual(video.url, "https://www.youtube.com/watch?v=rfscVS0vtbw")

    def test_playlist_pages_are_followed_and_details_are_batched(self) -> None:
        service = YouTubeService("test-key")
        service.session = FakeSession(
            [
                {
                    "items": [{"contentDetails": {"videoId": "aaaaaaaaaaa"}}],
                    "nextPageToken": "next",
                },
                {"items": [{"contentDetails": {"videoId": "bbbbbbbbbbb"}}]},
                {
                    "items": [
                        {"id": "aaaaaaaaaaa", "snippet": {"title": "A"}},
                        {"id": "bbbbbbbbbbb", "snippet": {"title": "B"}},
                    ]
                },
            ]
        )
        videos = service.get_playlist_videos("PL1234567890")
        self.assertEqual([video.title for video in videos], ["A", "B"])
        self.assertEqual(len(service.session.calls), 3)


if __name__ == "__main__":
    unittest.main()
