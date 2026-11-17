"""Small, lazy dataset index for real counts and opt-in profile suggestions."""

from __future__ import annotations

import math
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "data" / "dataset_index.json"
NUMERIC_FIELDS = [
    "cgpa", "coding_skill_score", "aptitude_score",
    "communication_skill_score", "logical_reasoning_score",
    "mock_interview_score", "backlogs", "github_repos",
    "internships_count", "projects_count",
]
PROFILE_FIELDS = NUMERIC_FIELDS + ["branch", "student_skills"]
RANGES = {
    "cgpa": 10.0,
    "coding_skill_score": 100.0,
    "aptitude_score": 100.0,
    "communication_skill_score": 100.0,
    "logical_reasoning_score": 100.0,
    "mock_interview_score": 100.0,
    "backlogs": 10.0,
    "github_repos": 100.0,
    "internships_count": 10.0,
    "projects_count": 20.0,
}


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def dataset_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        raise FileNotFoundError(
            f"Dataset index not found: {INDEX_PATH}. Run backend/build_dataset_index.py once."
        )
    with INDEX_PATH.open("r", encoding="utf-8") as source:
        return json.load(source)


def suggest_profile(partial: dict[str, Any]) -> dict[str, Any]:
    index = dataset_index()
    supplied: dict[str, Any] = {}
    for field in PROFILE_FIELDS:
        value = partial.get(field)
        if value is None or value == "":
            continue
        supplied[field] = _number(value) if field in NUMERIC_FIELDS else str(value).strip()
    if len(supplied) < 2:
        raise ValueError("Enter at least two profile details to find a similar example.")

    best_profile = None
    best_distance = float("inf")
    for candidate in index["profiles"]:
        distance = 0.0
        dimensions = 0
        for field, value in supplied.items():
            if value is None:
                continue
            other = candidate.get(field)
            if field in NUMERIC_FIELDS:
                if other is None:
                    continue
                difference = min(abs(float(value) - float(other)) / RANGES[field], 1.0)
                distance += difference * difference
            else:
                difference = 0.0 if str(value).casefold() == str(other).casefold() else 1.0
                distance += difference * difference
            dimensions += 1
        if dimensions and distance < best_distance:
            best_distance = distance
            best_profile = candidate

    if best_profile is None:
        raise ValueError("No comparable profiles were found in the dataset.")
    suggestions = {
        field: best_profile[field]
        for field in PROFILE_FIELDS
        if field not in supplied and best_profile.get(field) not in (None, "")
    }
    similarity = max(0.0, 1.0 - math.sqrt(best_distance / max(len(supplied), 1)))
    return {
        "suggested_fields": suggestions,
        "similarity_pct": round(similarity * 100, 1),
        "source": "An anonymized similar profile from the provided dataset. Review each suggestion before using it.",
    }


def extract_dataset_skills(description: str) -> list[str]:
    terms = dataset_index()["skill_vocabulary"]
    text = description.casefold()
    matches = []
    for term in terms:
        pattern = rf"(?<![\w+#.]){re.escape(term)}(?![\w+#.])"
        if re.search(pattern, text):
            matches.append(term)
    return sorted(matches, key=lambda value: (-len(value), value))
