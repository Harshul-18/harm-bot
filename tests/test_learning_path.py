from __future__ import annotations

import unittest

from learning_path import build_learning_path, learning_path_markdown
from youtube_service import VideoData


def educational_classifier(text: str):
    if "off topic" in text:
        return "Non Educational", "", [], []
    probability = 90.0 if "python" in text.lower() else 75.0
    return "Educational", "Coding", ["Python", "Web"], [probability, 100 - probability]


class LearningPathTests(unittest.TestCase):
    def test_filters_and_orders_beginner_before_advanced(self) -> None:
        videos = [
            VideoData("aaaaaaaaaaa", "Advanced Python", "deep dive", "", "A", "", duration_seconds=600),
            VideoData("bbbbbbbbbbb", "Python for beginners", "from scratch", "", "B", "", duration_seconds=300),
            VideoData("ccccccccccc", "Off topic vlog", "off topic", "", "C", ""),
        ]
        items, skipped = build_learning_path(videos, educational_classifier)
        self.assertEqual(skipped, 1)
        self.assertEqual([item.level for item in items], ["Beginner", "Advanced"])
        self.assertEqual([item.duration_minutes for item in items], [5, 10])

    def test_markdown_contains_clickable_study_plan(self) -> None:
        video = VideoData("aaaaaaaaaaa", "Python basics", "", "", "Teacher", "")
        items, _ = build_learning_path([video], educational_classifier)
        markdown = learning_path_markdown(items)
        self.assertIn("# HARM Bot Learning Path", markdown)
        self.assertIn("[Python basics](https://www.youtube.com/watch?v=aaaaaaaaaaa)", markdown)


if __name__ == "__main__":
    unittest.main()
