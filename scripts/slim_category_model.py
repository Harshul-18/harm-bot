#!/usr/bin/env python3
"""Reduce the category forest for memory-constrained deployment."""

from __future__ import annotations

import argparse
import pickle
from pathlib import Path


VALIDATION_TEXTS = [
    "python programming tutorial for beginners",
    "advanced web development and software architecture",
    "data science machine learning course",
    "accounting bookkeeping fundamentals",
    "cryptocurrency investing and financial analysis",
    "entrepreneurship business strategy and management",
    "digital marketing and social media growth",
    "network security certification tutorial",
    "computer hardware troubleshooting course",
    "graphic design illustration fundamentals",
    "user experience and web design tutorial",
    "fitness workout and general health advice",
    "meditation mental health and wellbeing",
    "photography camera and video editing course",
    "music vocal training lessons",
    "mathematics science and engineering lecture",
    "language learning and teacher training",
    "study skills productivity and career development",
    "google office productivity tutorial",
    "competitive exam preparation and practice questions",
    "travel arts and crafts tutorial",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--trees", type=int, default=20)
    parser.add_argument("--minimum-agreement", type=float, default=0.90)
    args = parser.parse_args()

    with args.input.open("rb") as model_file:
        pipeline = pickle.load(model_file)
    forest = pipeline.named_steps["clf"]
    original_count = len(forest.estimators_)
    if not 1 <= args.trees < original_count:
        raise ValueError(f"--trees must be between 1 and {original_count - 1}")

    full_predictions = pipeline.predict(VALIDATION_TEXTS)
    # Every tree is independently trained; evenly spaced selection avoids
    # depending on one contiguous part of the serialized ensemble.
    selected_indices = (
        [0]
        if args.trees == 1
        else [
            round(index * (original_count - 1) / (args.trees - 1))
            for index in range(args.trees)
        ]
    )
    forest.estimators_ = [forest.estimators_[index] for index in selected_indices]
    forest.n_estimators = args.trees
    slim_predictions = pipeline.predict(VALIDATION_TEXTS)
    agreement = float((full_predictions == slim_predictions).mean())
    if agreement < args.minimum_agreement:
        raise RuntimeError(
            f"Prediction agreement {agreement:.1%} is below "
            f"{args.minimum_agreement:.1%}; output was not written."
        )

    with args.output.open("wb") as model_file:
        pickle.dump(pipeline, model_file, protocol=pickle.HIGHEST_PROTOCOL)
    print(
        f"Retained {args.trees}/{original_count} trained trees; "
        f"validation agreement: {agreement:.1%}; "
        f"output: {args.output.stat().st_size / 1024**2:.1f} MiB"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
