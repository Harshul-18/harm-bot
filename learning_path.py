"""Create an explainable study plan from HARM Bot's existing classifiers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from io import StringIO
from typing import Callable, Iterable

import pandas as pd

from categoryPredictor import predictCategoryFor
from youtube_service import VideoData


Classifier = Callable[[str], tuple[str, str, list[str], object]]

BEGINNER_WORDS = (
    "beginner", "introduction", "intro ", "basics", "fundamentals",
    "getting started", "from scratch", "101", "first steps",
)
ADVANCED_WORDS = (
    "advanced", "expert", "masterclass", "deep dive", "architecture",
    "optimization", "interview", "production",
)

PREREQUISITES = {
    "Coding": "Basic computer use and the ability to install the demonstrated tools.",
    "IT and Software": "Basic computer, operating-system, and networking vocabulary.",
    "Finance and Accounting": "Comfort with arithmetic, percentages, and spreadsheets.",
    "Business": "No formal prerequisite; familiarity with common business terms helps.",
    "Design": "Basic visual communication and comfort with the demonstrated design tool.",
    "Health and Fitness": "Check personal limitations and seek professional advice where appropriate.",
    "Teaching and Academics": "Review the subject fundamentals named in the first module.",
}


@dataclass(frozen=True)
class LearningPathItem:
    order: int
    level: str
    category: str
    subcategory: str
    confidence: float
    title: str
    channel: str
    duration_minutes: int | None
    url: str
    prerequisite: str


def _difficulty(text: str) -> tuple[int, str]:
    normalized = f" {text.lower()} "
    if any(word in normalized for word in BEGINNER_WORDS):
        return 0, "Beginner"
    if any(word in normalized for word in ADVANCED_WORDS):
        return 2, "Advanced"
    return 1, "Intermediate"


def _best_subcategory(names: list[str], probabilities: object) -> tuple[str, float]:
    values = [float(value) for value in probabilities]
    if not names or not values:
        return "General", 0.0
    best = max(range(min(len(names), len(values))), key=values.__getitem__)
    return names[best], values[best]


def build_learning_path(
    videos: Iterable[VideoData],
    classifier: Classifier = predictCategoryFor,
) -> tuple[list[LearningPathItem], int]:
    """Filter, group, and order educational videos using explainable heuristics."""
    candidates: list[tuple[int, int, VideoData, str, str, float, str]] = []
    skipped = 0
    for source_index, video in enumerate(videos):
        status, category, subcategories, probabilities = classifier(
            video.prediction_text
        )
        if status != "Educational":
            skipped += 1
            continue
        subcategory, confidence = _best_subcategory(subcategories, probabilities)
        difficulty_rank, level = _difficulty(video.prediction_text)
        candidates.append(
            (
                difficulty_rank,
                source_index,
                video,
                category,
                subcategory,
                confidence,
                level,
            )
        )

    candidates.sort(key=lambda item: (item[3], item[4], item[0], item[1]))
    items: list[LearningPathItem] = []
    for order, (_, _, video, category, subcategory, confidence, level) in enumerate(
        candidates, start=1
    ):
        duration = (
            max(1, round(video.duration_seconds / 60))
            if video.duration_seconds
            else None
        )
        items.append(
            LearningPathItem(
                order=order,
                level=level,
                category=category,
                subcategory=subcategory,
                confidence=round(confidence, 1),
                title=video.title,
                channel=video.channel_name,
                duration_minutes=duration,
                url=video.url,
                prerequisite=PREREQUISITES.get(
                    category,
                    "Start with the introductory videos and review unfamiliar terminology.",
                ),
            )
        )
    return items, skipped


def learning_path_frame(items: list[LearningPathItem]) -> pd.DataFrame:
    frame = pd.DataFrame(asdict(item) for item in items)
    return frame.rename(
        columns={
            "order": "Order",
            "level": "Level",
            "category": "Category",
            "subcategory": "Topic",
            "confidence": "Topic confidence (%)",
            "title": "Video",
            "channel": "Channel",
            "duration_minutes": "Minutes",
            "url": "URL",
            "prerequisite": "Suggested preparation",
        }
    )


def learning_path_markdown(items: list[LearningPathItem]) -> str:
    output = StringIO()
    output.write("# HARM Bot Learning Path\n\n")
    previous_group: tuple[str, str] | None = None
    for item in items:
        group = (item.category, item.subcategory)
        if group != previous_group:
            output.write(f"## {item.category} — {item.subcategory}\n\n")
            output.write(f"Suggested preparation: {item.prerequisite}\n\n")
            previous_group = group
        duration = f" · {item.duration_minutes} min" if item.duration_minutes else ""
        output.write(
            f"{item.order}. [{item.title}]({item.url}) — {item.level}{duration}"
            f" · {item.channel}\n"
        )
    return output.getvalue()
