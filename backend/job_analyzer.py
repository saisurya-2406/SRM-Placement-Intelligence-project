"""Literal job-description skill extraction against observed dataset vocabulary."""

from __future__ import annotations

import re
from typing import Any

try:
    from .dataset_support import dataset_index
    from .skill_matching import categorize_skill
except ImportError:
    from dataset_support import dataset_index
    from skill_matching import categorize_skill


def analyze_job_description(description: Any) -> dict:
    if not isinstance(description, str) or not description.strip():
        raise ValueError("job_description must be a non-empty string.")
    if len(description) > 30000:
        raise ValueError("job_description must be 30,000 characters or fewer.")
    normalized = description.casefold()
    terms = dataset_index().get("skill_vocabulary", [])
    found: list[tuple[int, str]] = []
    for skill in terms:
        pattern = rf"(?<![\w+#.]){re.escape(skill.casefold())}(?![\w+#.])"
        match = re.search(pattern, normalized)
        if match:
            found.append((match.start(), skill))
    skills = list(dict.fromkeys(skill for _, skill in sorted(found)))
    categorized: dict[str, list[str]] = {}
    for skill in skills:
        categorized.setdefault(categorize_skill(skill), []).append(skill)
    return {
        "extracted_skills": skills,
        "categorized_skills": categorized,
        "extraction_method": "Literal phrase matching against the 500 most frequent required-skill terms in the supplied CSV.",
        "notice": "Review the extracted list; uncommon skills outside the dataset vocabulary may not be detected.",
    }
