from __future__ import annotations

import unittest
from pathlib import Path

from streamlit.testing.v1 import AppTest


class AppSmokeTests(unittest.TestCase):
    def test_app_does_not_require_a_youtube_api_key(self) -> None:
        root = Path(__file__).resolve().parents[1]
        source = "\n".join(
            (root / filename).read_text(encoding="utf-8")
            for filename in ("app.py", "youtube_service.py")
        )
        self.assertNotIn("YOUTUBE_API_KEY", source)

    def test_sidebar_reopen_control_is_not_hidden_by_css(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        source = app_path.read_text(encoding="utf-8")
        self.assertNotIn("footer, header", source)
        self.assertIn('[data-testid="stHeader"]', source)
        self.assertIn('stBaseButton-headerNoPadding', source)

    def test_app_starts_with_all_five_pages(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(
            app.selectbox[0].options,
            [
                "Category Predictor",
                "Channel Stats Viewer",
                "Search Videos",
                "Playlist Videos Predictor",
                "Educational Content in a Video",
            ],
        )
        markdown = "\n".join(item.value for item in app.markdown)
        self.assertIn("created by Harshul Nanda", markdown)
        self.assertIn("Project links", markdown)
        self.assertEqual(len(app.link_button), 3)

    def test_each_page_renders_its_original_input(self) -> None:
        app_path = Path(__file__).resolve().parents[1] / "app.py"
        app = AppTest.from_file(str(app_path)).run(timeout=30)
        expected_labels = {
            "Category Predictor": "Enter the URL of the Youtube Video",
            "Channel Stats Viewer": "Enter the Channel ID to get the stats of that channel",
            "Search Videos": "Search for videos",
            "Playlist Videos Predictor": "Enter a YouTube playlist url",
            "Educational Content in a Video": "Enter a Youtube Video URL",
        }
        for page, label in expected_labels.items():
            app.selectbox[0].select(page).run(timeout=30)
            self.assertFalse(app.exception, page)
            self.assertEqual(app.text_input[0].label, label)


if __name__ == "__main__":
    unittest.main()
