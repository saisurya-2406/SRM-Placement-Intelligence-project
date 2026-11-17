"""Build the compact dashboard/similarity index from the supplied CSV."""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data" / "student_job_pairs_rebuilt.csv"
OUTPUT_PATH = BASE_DIR / "data" / "dataset_index.json"
NUMERIC_FIELDS = [
    "cgpa", "coding_skill_score", "aptitude_score", "communication_skill_score",
    "logical_reasoning_score", "mock_interview_score", "backlogs", "github_repos",
    "internships_count", "projects_count",
]
PROFILE_FIELDS = NUMERIC_FIELDS + ["branch", "student_skills"]
USECOLS = list(dict.fromkeys([
    "student_id", "job_id", "job_title", "location", "role_category", "work_mode",
    "required_skills", *PROFILE_FIELDS,
]))


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(CSV_PATH)
    rng = random.Random(42)
    seen_students: set[str] = set()
    seen_jobs: set[str] = set()
    profiles: list[dict] = []
    rows = 0
    categories = {key: Counter() for key in ("branch", "role_category", "work_mode")}
    titles: Counter[str] = Counter()
    locations: Counter[str] = Counter()
    skill_terms: Counter[str] = Counter()

    for chunk in pd.read_csv(CSV_PATH, usecols=USECOLS, chunksize=100_000, keep_default_na=False):
        rows += len(chunk)
        for field in categories:
            categories[field].update(chunk[field].astype(str).value_counts().to_dict())
        titles.update(chunk["job_title"].astype(str).value_counts().to_dict())
        locations.update(chunk["location"].astype(str).value_counts().to_dict())
        terms = chunk["required_skills"].astype(str).str.split(",").explode().str.strip().str.casefold()
        terms = terms[terms.ne("")]
        skill_terms.update(terms.value_counts().to_dict())

        for job_id in chunk["job_id"].astype(str).unique():
            if job_id:
                seen_jobs.add(job_id)

        unique_students = chunk.drop_duplicates("student_id", keep="first")
        for record in unique_students.to_dict(orient="records"):
            student_id = str(record.get("student_id", ""))
            if not student_id or student_id in seen_students:
                continue
            seen_students.add(student_id)
            profile = {field: record.get(field, "") for field in PROFILE_FIELDS}
            for field in NUMERIC_FIELDS:
                value = pd.to_numeric(profile[field], errors="coerce")
                profile[field] = None if pd.isna(value) else float(value)
            if len(profiles) < 5000:
                profiles.append(profile)
            else:
                slot = rng.randrange(len(seen_students))
                if slot < len(profiles):
                    profiles[slot] = profile

    summary = {
        "rows": rows,
        "students": len(seen_students),
        "jobs": len(seen_jobs),
        "branches": sorted(key for key, count in categories["branch"].items() if key and count),
        "role_categories": sorted(key for key, count in categories["role_category"].items() if key and count),
        "work_modes": sorted(key for key, count in categories["work_mode"].items() if key and count),
        "category_counts": {
            field: {key: int(count) for key, count in counter.items() if key}
            for field, counter in categories.items()
        },
        "popular_job_titles": [key for key, _ in titles.most_common(12)],
        "popular_locations": [key for key, _ in locations.most_common(12)],
        "skill_vocabulary": [key for key, _ in skill_terms.most_common(500)],
        "profiles": profiles,
    }
    OUTPUT_PATH.write_text(json.dumps(summary, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size:,} bytes) from {rows:,} rows")


if __name__ == "__main__":
    main()
