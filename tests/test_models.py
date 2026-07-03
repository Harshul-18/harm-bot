from __future__ import annotations

import pickle
import unittest
from pathlib import Path

from colors import dataset


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"


class ModelInventoryTests(unittest.TestCase):
    def test_every_category_has_a_matching_model_and_class_count(self) -> None:
        for category, labels in dataset.items():
            filename = f"{category.lower().replace(' ', '_')}_model.pkl"
            path = MODEL_DIR / filename
            self.assertTrue(path.exists(), f"Missing model for {category}")
            with path.open("rb") as handle:
                model = pickle.load(handle)
            self.assertEqual(len(model.classes_), len(labels), category)

    def test_core_models_predict(self) -> None:
        samples = ["complete python programming tutorial for beginners"]
        with (MODEL_DIR / "educated_model.pkl").open("rb") as handle:
            education_model = pickle.load(handle)
        with (MODEL_DIR / "cat_model.pkl").open("rb") as handle:
            category_model = pickle.load(handle)
        self.assertEqual(len(education_model.predict(samples)), 1)
        self.assertEqual(len(category_model.predict(samples)), 1)


if __name__ == "__main__":
    unittest.main()
