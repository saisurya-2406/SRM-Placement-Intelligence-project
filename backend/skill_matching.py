"""Exact, case-insensitive skill matching used by analysis and reports."""

from __future__ import annotations

import re
from typing import Any


_SKILL_ALIASES = {
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "ms excel": "Excel",
    "excel": "Excel",
    "structured query language": "SQL",
    "sql": "SQL",
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "postgresql": "PostgreSQL",
}


def normalize_skill(value: str) -> str:
    """Canonicalize known aliases while retaining the display name for other skills."""
    display = " ".join(value.split()).strip()
    if not display:
        return ""
    key = display.casefold()
    return _SKILL_ALIASES.get(key, display)


def parse_skills(value: Any, field: str = "skills") -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r"[,;\n]", value)
    elif isinstance(value, list) and all(isinstance(item, str) for item in value):
        parts = value
    else:
        raise ValueError(f"{field} must be a string or a list of strings.")
    normalized = {}
    for part in parts:
        token = normalize_skill(part)
        if token:
            normalized.setdefault(token.casefold(), token)
    return sorted(normalized.values(), key=str.casefold)


def match_skills(student_skills: Any, required_skills: Any) -> dict[str, Any]:
    student = parse_skills(student_skills, "student_skills")
    required = parse_skills(required_skills, "required_skills")
    student_index = {skill.casefold(): skill for skill in student}
    required_index = {skill.casefold(): skill for skill in required}
    common = student_index.keys() & required_index.keys()
    matched = sorted((required_index[key] for key in common), key=str.casefold)
    missing = sorted((required_index[key] for key in required_index.keys() - common), key=str.casefold)
    additional = sorted((student_index[key] for key in student_index.keys() - required_index.keys()), key=str.casefold)
    percentage = round(len(matched) * 100 / len(required), 2) if required else None
    return {
        "student_skills": student,
        "required_skills": required,
        "matched_skills": matched,
        "missing_skills": missing,
        "additional_skills": additional,
        "required_skill_count": len(required),
        "matched_skill_count": len(matched),
        "missing_skill_count": len(missing),
        "skill_match_pct": percentage,
        "matching_method": "Case-insensitive exact phrase overlap after whitespace cleanup and the documented skill-alias map; unknown skills remain exact phrases.",
    }


_CATEGORY_SKILLS = {
    "Programming": {"python", "java", "javascript", "typescript", "c", "c++", "c#", "r", "sql", "go", "rust", "php", "ruby", "kotlin", "swift"},
    "Frameworks & Libraries": {"react", "angular", "vue", "flask", "django", "fastapi", "spring", "node.js", "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch"},
    "Databases": {"mysql", "postgresql", "mongodb", "sqlite", "oracle", "redis", "sql server", "database", "database administration"},
    "Machine Learning": {"machine learning", "deep learning", "nlp", "computer vision", "classification", "regression", "neural networks", "generative ai", "artificial intelligence"},
    "Data Analysis": {"data analysis", "data analytics", "data visualization", "statistics", "tableau", "power bi", "excel", "matplotlib", "seaborn"},
    "Cloud & DevOps": {"aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "ci/cd", "terraform", "devops"},
    "Cybersecurity": {"cybersecurity", "security", "web security", "penetration testing", "threat modeling"},
    "Networking": {"networking", "network administration", "tcp/ip", "dns", "routing", "switching"},
    "Software Testing": {"software testing", "testing", "qa", "quality assurance", "playwright", "pytest", "selenium", "test automation"},
    "Business Analysis": {"business analysis", "requirements analysis", "business process modeling", "stakeholder management", "product analysis"},
    "Tools": {"git", "github", "linux", "jira", "postman", "jenkins", "api", "rest api"},
    "Soft Skills": {"communication", "leadership", "teamwork", "problem solving", "collaboration", "presentation"},
}


def categorize_skill(skill: str) -> str:
    term = skill.casefold()
    for category, terms in _CATEGORY_SKILLS.items():
        if term in terms:
            return category
    return "Other / uncategorized"


def analyze_gap(student_skills: Any, required_skills: Any, optional_skills: Any = None) -> dict[str, Any]:
    result = match_skills(student_skills, required_skills)
    optional = match_skills(student_skills, optional_skills)
    grouped: dict[str, list[str]] = {}
    for skill in result["missing_skills"]:
        grouped.setdefault(categorize_skill(skill), []).append(skill)
    result["technical_skill_gaps"] = {
        category: skills for category, skills in grouped.items() if category != "Soft Skills"
    }
    result["soft_skill_gaps"] = grouped.get("Soft Skills", [])
    result["skill_coverage_pct"] = result["skill_match_pct"]
    result["matched_optional_skills"] = optional["matched_skills"]
    result["missing_optional_skills"] = optional["missing_skills"]
    result["optional_skill_count"] = optional["required_skill_count"]
    result["priority_rule"] = "No priority ranking is inferred because the dataset provides no per-skill importance weights."
    return result
