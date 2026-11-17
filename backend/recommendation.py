"""Transparent template-based learning activities for identified skill gaps."""

from __future__ import annotations

from typing import Any

try:
    from .skill_matching import categorize_skill, normalize_skill, parse_skills
except ImportError:
    from skill_matching import categorize_skill, normalize_skill, parse_skills


def recommendations_for(
    missing_skills: list[str],
    role: str = "the target role",
    *,
    optional_skills: list[str] | None = None,
    resources: list[dict[str, Any]] | None = None,
    skill_job_counts: dict[str, int] | None = None,
    mastered_skills: set[str] | None = None,
    skill_proficiencies: dict[str, int] | None = None,
) -> list[dict[str, Any]]:
    recommendations = []
    role_text = role.strip() or "the target role"
    job_counts = {
        normalize_skill(skill).casefold(): max(1, int(count))
        for skill, count in (skill_job_counts or {}).items()
    }
    mastered = {normalize_skill(skill).casefold() for skill in mastered_skills or set()}
    proficiencies = {
        normalize_skill(skill).casefold(): int(level)
        for skill, level in (skill_proficiencies or {}).items()
    }
    required = [(skill, "mandatory") for skill in parse_skills(missing_skills, "missing_skills")]
    optional = [(skill, "optional") for skill in parse_skills(optional_skills or [], "optional_skills")]

    for skill, requirement_type in required + optional:
        skill_key = skill.casefold()
        if skill_key in mastered:
            continue
        category = categorize_skill(skill)
        count = job_counts.get(skill_key, 1)
        proficiency = proficiencies.get(skill_key)
        candidates = [
            resource for resource in resources or []
            if normalize_skill(resource.get("skill", "")).casefold() == skill_key
            and resource.get("category") != "Certification"
            and resource.get("verified", True)
        ]
        resource = next(
            (
                item for item in candidates
                if role_text.casefold() in {
                    name.casefold() for name in item.get("relevant_roles", [])
                }
            ),
            candidates[0] if candidates else None,
        )
        rank = count * 2 - int(requirement_type == "optional")
        status = "Partially developed" if proficiency is not None and proficiency > 1 else "Missing"
        if requirement_type == "optional":
            priority = "Optional"
            basis = "Configured as an optional requirement for the selected role."
            why = f"This skill is listed as an optional requirement for {role_text}."
        else:
            priority = "High" if count > 1 else "Required"
            basis = (
                f"Missing from {count} saved job requirements."
                if count > 1 else "Listed as a missing mandatory requirement for the selected role."
            )
            why = f"This skill is listed as a mandatory requirement for {role_text}."
        activity = (
            f"Build on your self-reported {proficiency}/5 {skill} proficiency with a role-focused practice task."
            if proficiency is not None else
            f"Practice {skill} by completing a small task and documenting what you learned."
        )
        recommendations.append({
            "skill": skill,
            "category": category,
            "requirement_type": requirement_type,
            "development_status": status,
            "proficiency_level": proficiency,
            "why_it_matters": why,
            "learning_activity": activity,
            "project_idea": f"Build a compact {role_text} project that uses {skill}, then add a short README explaining your decisions.",
            "priority": priority,
            "priority_rank": rank,
            "priority_basis": basis,
            "resource": ({
                "id": resource["id"],
                "title": resource["title"],
                "provider": resource["provider"],
                "type": resource["type"],
                "difficulty": resource["level"],
                "domain": resource["domain"],
                "url": resource["url"],
                "description": resource["description"],
            } if resource else None),
        })
    return sorted(
        recommendations,
        key=lambda item: (-item["priority_rank"], item["requirement_type"] != "mandatory", item["skill"].casefold()),
    )
