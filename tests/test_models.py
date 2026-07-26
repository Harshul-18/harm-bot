from __future__ import annotations

import pickle
import unittest
from pathlib import Path

from categoryPredictor import get_model_path, load_model
from colors import dataset


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"


class ModelInventoryTests(unittest.TestCase):
    def test_runtime_model_cache_is_memory_bounded(self) -> None:
        self.assertEqual(load_model.cache_parameters()["maxsize"], 3)

    def test_primary_category_model_fits_hosted_memory_budget(self) -> None:
        category_model = Path(get_model_path("cat_model.pkl"))
        self.assertLess(category_model.stat().st_size, 350 * 1024 * 1024)

    def test_every_category_has_a_matching_model_and_class_count(self) -> None:
        for category, labels in dataset.items():
            filename = f"{category.lower().replace(' ', '_')}_model.pkl"
            path = Path(get_model_path(filename))
            self.assertTrue(path.exists(), f"Missing model for {category}")
            with path.open("rb") as handle:
                model = pickle.load(handle)
            self.assertEqual(len(model.classes_), len(labels), category)

    def test_core_models_predict(self) -> None:
        samples = ["complete python programming tutorial for beginners"]
        education_model = load_model("educated_model.pkl")
        category_model = load_model("cat_model.pkl")
        self.assertEqual(len(category_model.named_steps["clf"].estimators_), 20)
        self.assertEqual(len(education_model.predict(samples)), 1)
        self.assertEqual(len(category_model.predict(samples)), 1)


if __name__ == "__main__":
    unittest.main()
