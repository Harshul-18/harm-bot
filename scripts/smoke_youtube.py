#!/usr/bin/env python3
"""Live, read-only checks for the keyless YouTube integrations."""

from __future__ import annotations

import argparse
import sys
from importlib.metadata import version
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from youtube_transcript_api import YouTubeTranscriptApi

from youtube_service import YouTubeService


VIDEO_ID = "rfscVS0vtbw"
PLAYLIST_ID = "PL-osiE80TeTt2d9bfVyTiXJA-UTHn6WwU"
CHANNEL = "@freecodecamp"


class FallbackOnlyService(YouTubeService):
    """Exercise the real fallback without depending on a primary outage."""

    def _extract_with_ytdlp(self, *args: object, **kwargs: object) -> dict:
        raise RuntimeError("Primary provider disabled by smoke test")


def report(name: str, detail: str) -> None:
    print(f"PASS  {name:<12} {detail}")


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--full",
        action="store_true",
        help="also check search, playlist, channel, and transcript extraction",
    )
    mode.add_argument(
        "--fallback",
        action="store_true",
        help="disable yt-dlp and verify the real PyTubeFix fallback",
    )
    args = parser.parse_args()

    print(
        "Runtime:",
        f"Python {sys.version.split()[0]};",
        f"yt-dlp {version('yt-dlp')};",
        f"pytubefix {version('pytubefix')};",
        f"youtube-transcript-api {version('youtube-transcript-api')}",
    )

    service = FallbackOnlyService() if args.fallback else YouTubeService()
    try:
        video = service.get_video(VIDEO_ID)
        report("video", f"{video.video_id} via {video.provider}")
        if args.fallback:
            if video.provider != "pytubefix":
                raise RuntimeError(f"Expected pytubefix, got {video.provider}")
            return 0

        if args.full:
            results = service.search_videos("python tutorial", 2)
            report("search", f"{len(results)} results via {results[0].provider}")

            playlist = service.get_playlist_videos(PLAYLIST_ID)
            report("playlist", f"{len(playlist)} public videos")

            channel = service.get_channel_videos(CHANNEL, 2)
            report("channel", f"{len(channel)} videos via {channel[0].provider}")

            transcript = YouTubeTranscriptApi().fetch(VIDEO_ID, languages=["en"])
            report("transcript", f"{len(transcript)} caption segments")
    except Exception as error:
        print(f"FAIL  {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
