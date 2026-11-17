"""Persistent, explainable career matching and student roadmap APIs."""
from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlsplit

from flask import Blueprint, jsonify, request

try:
    from .database import get_db
    from .recommendation import recommendations_for
    from .skill_matching import categorize_skill, match_skills, normalize_skill, parse_skills
except ImportError:
    from database import get_db
    from recommendation import recommendations_for
    from skill_matching import categorize_skill, match_skills, normalize_skill, parse_skills

career = Blueprint("career", __name__, url_prefix="/api")

# Official provider documentation and learning paths. Duration and price are omitted
# unless explicitly stated in the source; these links are checked into the catalog.
RESOURCES: list[dict[str, Any]] = [
    {"id":"python-docs","name":"The Python Tutorial","provider":"Python Software Foundation","skill":"Python","category":"Documentation","level":"Programmer fundamentals","cost":"Free","duration":"Self-paced","url":"https://docs.python.org/3/tutorial/","why":"Official language tutorial for syntax, data structures, modules, and errors."},
    {"id":"postgres-tutorial","name":"PostgreSQL Tutorial","provider":"PostgreSQL Global Development Group","skill":"SQL","category":"Documentation","level":"Beginner","cost":"Free","duration":"Self-paced","url":"https://www.postgresql.org/docs/current/tutorial.html","why":"Official hands-on introduction covering querying, joins, aggregates, and transactions."},
    {"id":"powerbi-path","name":"Prepare and visualize data with Power BI","provider":"Microsoft Learn","skill":"Power BI","category":"Learning path","level":"Beginner","cost":"Free learning content; certification exam cost not listed here","duration":"8 hr 12 min","url":"https://learn.microsoft.com/en-us/training/paths/prepare-visualize-data-power-bi/","why":"Official learning path covering data connection, transformation, and interactive reporting."},
    {"id":"powerbi-prepare","name":"Prepare data for analysis with Power BI","provider":"Microsoft Learn","skill":"Power BI","category":"Learning path","level":"Intermediate","cost":"Free learning content","duration":"Self-paced","url":"https://learn.microsoft.com/en-us/training/paths/prepare-data-power-bi","why":"Official analyst-focused path for profiling, cleaning, loading, and modeling data."},
    {"id":"pl300-cert","name":"Microsoft Certified: Power BI Data Analyst Associate (PL-300)","provider":"Microsoft Learn","skill":"Power BI","category":"Certification","level":"Intermediate","cost":"Exam fee varies by region; provider page lists regional pricing","duration":"100-minute exam","url":"https://learn.microsoft.com/en-us/credentials/certifications/exams/PL-300","why":"Official credential covering preparation, modeling, visualization, analysis, management, and security in Power BI."},
]


def _resource(resource_id, title, skill, provider, kind, url, description, roles, level="All levels", cost="See provider", duration="Self-paced"):
    return {
        "id": resource_id, "title": title, "name": title, "skill": skill, "provider": provider,
        "type": kind, "category": kind, "url": url, "description": description, "why": description,
        "domain": _resource_domain(skill),
        "relevant_roles": roles, "level": level, "cost": cost, "duration": duration,
    }


def _resource_domain(skill):
    key = normalize_skill(skill).casefold()
    if key in {"sql", "mysql", "postgresql", "database", "database administration"}:
        return "Databases"
    if key in {"communication", "interview preparation", "stakeholder management"}:
        return "Communication and Career Skills"
    domains = {
        "Data Analysis": "Data Analytics",
        "Machine Learning": "AI and Machine Learning",
        "Frameworks & Libraries": "Software Development",
        "Cloud & DevOps": "Cloud and DevOps",
        "Cybersecurity": "Cybersecurity",
        "Networking": "Networking",
        "Software Testing": "Software Testing",
        "Business Analysis": "Business Analysis",
        "Tools": "Software Engineering",
        "Soft Skills": "Communication and Career Skills",
        "Other / uncategorized": "General Technical Skills",
    }
    return domains.get(categorize_skill(skill), categorize_skill(skill))


_DATA_ROLES = ["Business Analyst", "Data Analyst", "Data Engineer", "Data Scientist", "Machine Learning Engineer"]
_DEV_ROLES = ["Python Developer", "Data Engineer", "Data Scientist", "Machine Learning Engineer"]
RESOURCES[1]["skill"] = "PostgreSQL"
RESOURCES.extend([
    _resource("sqlbolt", "Interactive SQL Lessons", "SQL", "SQLBolt", "Interactive course", "https://sqlbolt.com/", "Browser-based SQL lessons and exercises for queries, joins, and relational data.", _DATA_ROLES, "Beginner", "Free"),
    _resource("mysql-tutorial", "MySQL Tutorial", "MySQL", "MySQL Tutorial", "Tutorial", "https://www.mysqltutorial.org/", "Practical MySQL lessons with setup guidance and query examples.", _DATA_ROLES, "Beginner"),
    _resource("excel-help", "Excel help & learning", "Excel", "Microsoft Support", "Official learning hub", "https://support.microsoft.com/en-us/excel", "Official Excel guides for formulas, data import, analysis, formatting, and collaboration.", ["Business Analyst", "Data Analyst"], "Beginner"),
    _resource("openintro-statistics", "OpenIntro Statistics", "Statistics", "OpenIntro", "Textbook", "https://www.openintro.org/book/os/", "Statistics textbook and supporting materials for probability, inference, and data analysis.", _DATA_ROLES, "Beginner to intermediate", "Free PDF available"),
    _resource("google-data-analytics", "Google Data Analytics Professional Certificate", "Data Analytics", "Google / Coursera", "Professional certificate", "https://www.coursera.org/professional-certificates/google-data-analytics", "Career certificate covering the analytics process, spreadsheets, SQL, analysis, and presentation.", ["Business Analyst", "Data Analyst"], "Beginner"),
    _resource("kaggle-pandas", "Pandas", "Data Science", "Kaggle Learn", "Interactive course", "https://www.kaggle.com/learn/pandas", "Hands-on lessons for exploring and manipulating tabular data with pandas.", _DATA_ROLES, "Beginner"),
    _resource("kaggle-ml", "Intro to Machine Learning", "Machine Learning", "Kaggle Learn", "Interactive course", "https://www.kaggle.com/learn/intro-to-machine-learning", "Practical lessons on model fitting, validation, and common machine-learning workflows.", ["Data Scientist", "Machine Learning Engineer"], "Beginner"),
    _resource("google-mlcc", "Machine Learning Crash Course", "Machine Learning", "Google for Developers", "Interactive course", "https://developers.google.com/machine-learning/crash-course", "Practical introduction with videos, interactive visualizations, and exercises.", ["Data Scientist", "Machine Learning Engineer"], "Beginner to intermediate"),
    _resource("matplotlib-tutorials", "Matplotlib Tutorials", "Data Visualization", "Matplotlib", "Official tutorials", "https://matplotlib.org/stable/tutorials/index.html", "Official tutorials for creating and customizing visualizations in Python.", ["Data Analyst", "Data Scientist", "Machine Learning Engineer"], "Beginner", "Free"),
    _resource("tableau-training", "Tableau Training", "Tableau", "Tableau", "Training videos", "https://www.tableau.com/learn/training", "Training videos for connecting data, building workbooks, and visualizing information.", ["Business Analyst", "Data Analyst"], "Beginner", "Free training videos"),
    _resource("toastmasters-speaking", "Public Speaking Tips", "Communication", "Toastmasters International", "Practice guide", "https://www.toastmasters.org/resources/public-speaking-tips", "Practical advice for organizing, rehearsing, and delivering clear presentations.", _DATA_ROLES + ["Python Developer"]),
    _resource("google-interview-tips", "How to prepare for an interview", "Interview preparation", "Grow with Google", "Career guide", "https://grow.google/grow-your-career/articles/interview-tips/", "Interview preparation guidance on articulating skills, preparing examples, and evaluating role fit.", _DATA_ROLES + ["Python Developer"]),
    _resource("mdn-javascript", "Dynamic scripting with JavaScript", "JavaScript", "MDN Web Docs", "Learning module", "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Scripting", "Core JavaScript concepts and browser scripting, with guided exercises.", ["Frontend Developer", "Backend Developer", "Full-Stack Developer", "Software Developer"], "Beginner", "Free"),
    _resource("mdn-css", "CSS styling basics", "CSS", "MDN Web Docs", "Learning module", "https://developer.mozilla.org/en-US/docs/Learn_web_development/Core/Styling_basics", "Fundamentals for styling and laying out web pages.", ["Frontend Developer", "Full-Stack Developer", "Software Developer"], "Beginner", "Free"),
    _resource("react-learn", "Quick Start", "React", "React", "Official documentation", "https://react.dev/learn", "Official interactive introduction to components, state, rendering, and events.", ["Frontend Developer", "Full-Stack Developer", "Software Developer"], "Beginner", "Free"),
    _resource("java-learn", "Learn Java", "Java", "Oracle and OpenJDK community", "Tutorials", "https://dev.java/learn/", "Java language fundamentals, object-oriented programming, and standard APIs.", ["Java Developer", "Backend Developer", "Software Developer"], "Beginner", "Free"),
    _resource("aws-skill-builder", "AWS Skill Builder digital training", "AWS", "Amazon Web Services", "Learning platform", "https://aws.amazon.com/training/digital/", "AWS-hosted digital learning catalog with free and paid material; check each course's terms.", ["Cloud Engineer", "DevOps Engineer", "Data Engineer"], "All levels", "Free and paid options"),
    _resource("azure-cloud-concepts", "Introduction to Cloud Infrastructure: Describe Cloud Concepts", "Azure", "Microsoft Learn", "Learning path", "https://learn.microsoft.com/en-us/training/paths/microsoft-azure-fundamentals-describe-cloud-concepts/", "Official Azure cloud concepts learning path; learning content is separate from certification exams.", ["Cloud Engineer", "DevOps Engineer", "Software Developer"], "Beginner", "Free learning content"),
    _resource("docker-get-started", "Get started with Docker", "Docker", "Docker", "Official tutorial", "https://docs.docker.com/get-started/", "Official hands-on introduction to containers, images, and running applications.", ["DevOps Engineer", "Cloud Engineer", "Backend Developer", "Software Developer"], "Beginner", "Free"),
    _resource("kubernetes-tutorials", "Kubernetes Tutorials", "Kubernetes", "Kubernetes", "Official tutorials", "https://kubernetes.io/docs/tutorials/", "Official tutorials for deploying, scaling, and operating containerized applications.", ["DevOps Engineer", "Cloud Engineer"], "Intermediate", "Free"),
    _resource("terraform-aws", "Get Started - AWS", "Terraform", "HashiCorp", "Tutorial series", "https://developer.hashicorp.com/terraform/tutorials/aws-get-started", "Official guided Terraform tutorials for infrastructure as code on AWS.", ["DevOps Engineer", "Cloud Engineer"], "Beginner to intermediate", "Free"),
    _resource("github-actions-quickstart", "GitHub Actions Quickstart", "CI/CD", "GitHub", "Official guide", "https://docs.github.com/en/actions/get-started/quickstart", "Official guide to creating a workflow and automating builds and tests.", ["DevOps Engineer", "Software Developer", "QA Engineer"], "Beginner", "Free"),
    _resource("portswigger-academy", "Web Security Academy", "Cybersecurity", "PortSwigger", "Interactive training", "https://portswigger.net/web-security", "Free web security learning materials and interactive labs.", ["Cybersecurity Analyst", "Security Engineer"], "Beginner to advanced", "Free"),
    _resource("cisco-networking-basics", "Networking Basics", "Networking", "Cisco Networking Academy", "Online course", "https://www.netacad.com/courses/networking-basics?courseLang=en-US", "Cisco Networking Academy course covering fundamental networking concepts.", ["Network Engineer", "Cybersecurity Analyst", "Cloud Engineer"], "Beginner", "See provider"),
    _resource("playwright-intro", "Playwright Test introduction", "Software Testing", "Playwright", "Official documentation", "https://playwright.dev/docs/intro", "Official end-to-end testing guide covering setup, browser support, assertions, and isolation.", ["QA Engineer", "Testing Engineer", "Software Developer"], "Beginner", "Free"),
    _resource("pytest-getting-started", "Get Started", "Python Testing", "pytest", "Official documentation", "https://docs.pytest.org/en/stable/getting-started.html", "Official guide to writing and running Python tests.", ["QA Engineer", "Testing Engineer", "Python Developer"], "Beginner", "Free"),
    _resource("iiba-business-analysis", "Business Analysis Professional Resources", "Business Analysis", "International Institute of Business Analysis", "Professional resource hub", "https://www.iiba.org/career-resources/business-analysis-resources/", "IIBA's professional resource hub for business analysis knowledge and career development.", ["Business Analyst", "Product Analyst", "Business Intelligence Analyst"], "All levels", "Some resources may require membership or purchase"),
])
_ROLE_NAMES = _DATA_ROLES + _DEV_ROLES + ["Software Developer", "Frontend Developer", "Backend Developer", "Full-Stack Developer", "Java Developer", "AI Engineer", "Cloud Engineer", "DevOps Engineer", "Cybersecurity Analyst", "Network Engineer", "QA Engineer", "Testing Engineer", "Product Analyst", "Business Intelligence Analyst"]
for _item in RESOURCES:
    _item.setdefault("domain", _resource_domain(_item["skill"]))
    _item.setdefault("title", _item["name"])
    _item.setdefault("type", _item["category"])
    _item.setdefault("description", _item["why"])
    _item.setdefault("relevant_roles", _ROLE_NAMES)


def _catalog_resources(db):
    for resource in RESOURCES:
        db.execute(
            """INSERT OR IGNORE INTO learning_resource_catalog
               (id,title,skill,domain,provider,resource_type,difficulty,url,description,
                relevant_roles_json,verification_status,cost,duration,is_builtin)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                resource["id"], resource["title"], resource["skill"], resource.get("domain") or _resource_domain(resource["skill"]),
                resource["provider"], resource["type"], resource["level"], resource["url"],
                resource["description"], json.dumps(resource["relevant_roles"]),
                "provider_checked", resource.get("cost", ""), resource.get("duration", ""),
            ),
        )
    rows = db.execute("SELECT * FROM learning_resource_catalog ORDER BY title COLLATE NOCASE,id").fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["name"] = item["title"]
        item["category"] = item["resource_type"]
        item["type"] = item["resource_type"]
        item["level"] = item["difficulty"]
        item["why"] = item["description"]
        item["relevant_roles"] = json.loads(item.pop("relevant_roles_json") or "[]")
        item["verified"] = item["verification_status"] in {"provider_checked", "admin_confirmed"}
        items.append(item)
    return items


def _split(value):
    try: return parse_skills(value or "")
    except ValueError: return []

def _match(student, job):
    fit = match_skills(student["student_skills"], job["required_skills"])
    optional_fit = match_skills(student["student_skills"], job.get("optional_skills", ""))
    fit["normalized_student_skills"] = fit.pop("student_skills")
    fit["normalized_required_skills"] = fit.pop("required_skills")
    fit["matched_optional_skills"] = optional_fit["matched_skills"]
    fit["missing_optional_skills"] = optional_fit["missing_skills"]
    fit["normalized_optional_skills"] = optional_fit["required_skills"]
    failed = []
    if job["min_cgpa"] is not None and student["cgpa"] < job["min_cgpa"]:
        failed.append(f"CGPA {student['cgpa']:g} is below the configured minimum {job['min_cgpa']:g}.")
    degree=job.get("required_degree","").strip()
    if degree and degree.casefold() not in (student.get("degree") or "").casefold():
        failed.append(f"Recorded degree does not satisfy the configured degree requirement ({degree}).")
    branches = _split(job["eligible_branches"])
    if branches and student["branch"].casefold() not in {b.casefold() for b in branches}:
        failed.append("Student branch is outside the configured eligible branches.")
    experience = float(student.get("experience_years") or 0)
    low = job["experience_min_yrs"]
    if low is not None and experience < low:
        failed.append(f"Experience is below the configured minimum of {low:g} years.")
    if job.get("is_fresher_friendly") == 0 and experience <= 0 and low is None:
        failed.append("This job is configured as not fresher-friendly and no work experience is recorded.")
    required_certs = _split(job["required_certifications"])
    student_certs = {c.casefold() for c in _split(student.get("certifications"))}
    missing_certs = [c for c in required_certs if c.casefold() not in student_certs]
    if missing_certs: failed.append("Missing required certification(s): " + ", ".join(missing_certs) + ".")
    status = "not_eligible" if failed else ("strong_match" if fit["required_skill_count"] and not fit["missing_skills"] else "potential_match")
    return {**fit,"eligibility_status":"not_currently_eligible" if failed else "eligible","match_category":status,
            "eligibility_reasons":failed,"missing_certifications":missing_certs,
            "method":"Eligibility uses configured degree, CGPA, branch, minimum experience/fresher, and certification rules. Skill coverage is case-insensitive exact phrase overlap after documented aliases. No ML prediction is used."}


def skill_job_counts_for_student(db, student_pk, job_pks=None):
    job_counts = Counter()
    student = db.execute("SELECT student_skills FROM students WHERE id=?", (student_pk,)).fetchone()
    if student:
        if job_pks:
            placeholders = ",".join("?" for _ in job_pks)
            jobs = db.execute(
                f"SELECT required_skills,optional_skills FROM jobs WHERE id IN ({placeholders})",
                list(job_pks),
            ).fetchall()
        else:
            jobs = db.execute("SELECT required_skills,optional_skills FROM jobs").fetchall()
        for job in jobs:
            for field in ("required_skills", "optional_skills"):
                match = match_skills(student["student_skills"], job[field])
                job_counts.update(skill.casefold() for skill in match["missing_skills"])
    return dict(job_counts)


def recommendations_for_student(
    db, missing_skills, role, student_pk=None, job_pks=None, optional_skills=None,
):
    mastered = set()
    proficiencies = {}
    if student_pk is not None:
        student = db.execute("SELECT student_id,student_skills FROM students WHERE id=?", (student_pk,)).fetchone()
        if student:
            selected_job_pks = (
                [job_pks] if isinstance(job_pks, int)
                else list(job_pks) if job_pks is not None else []
            )
            if selected_job_pks:
                placeholders = ",".join("?" for _ in selected_job_pks)
                jobs = db.execute(
                    f"SELECT required_skills,optional_skills FROM jobs WHERE id IN ({placeholders})",
                    selected_job_pks,
                ).fetchall()
                open_required, open_optional = set(), set()
                for job in jobs:
                    required_fit = match_skills(student["student_skills"], job["required_skills"])
                    optional_fit = match_skills(student["student_skills"], job["optional_skills"])
                    open_required.update(skill.casefold() for skill in required_fit["missing_skills"])
                    open_optional.update(skill.casefold() for skill in optional_fit["missing_skills"])
                missing_skills = [
                    skill for skill in missing_skills
                    if normalize_skill(skill).casefold() in open_required
                ]
                optional_skills = [
                    skill for skill in optional_skills or []
                    if normalize_skill(skill).casefold() in open_optional
                ]
            proficiency_rows = db.execute(
                """SELECT skill,current_proficiency FROM skill_proficiency_history
                   WHERE student_pk=? ORDER BY assessment_date DESC,id DESC""",
                (student_pk,),
            ).fetchall()
            for row in proficiency_rows:
                skill = normalize_skill(row["skill"]).casefold()
                proficiencies.setdefault(skill, row["current_proficiency"])
            mastered.update(skill for skill, value in proficiencies.items() if value == 5)
            completed_rows = db.execute(
                """SELECT lr.skill FROM learning_recommendations lr
                   JOIN analyses a ON a.id=lr.analysis_id
                   WHERE lr.is_completed=1
                     AND (a.student_record_id=? OR a.student_id=?)""",
                (student_pk, student["student_id"]),
            ).fetchall()
            mastered.update(normalize_skill(row["skill"]).casefold() for row in completed_rows)
    return recommendations_for(
        missing_skills, role, optional_skills=optional_skills, resources=_catalog_resources(db),
        skill_job_counts=skill_job_counts_for_student(
            db, student_pk,
            [job_pks] if isinstance(job_pks, int) else job_pks,
        ) if student_pk is not None else {},
        mastered_skills=mastered,
        skill_proficiencies=proficiencies,
    )


def _roadmap_json(db, roadmap):
    result = dict(roadmap)
    result["snapshot"] = json.loads(result.pop("snapshot_json"))
    result["activities"] = []
    for row in db.execute("SELECT * FROM roadmap_activities WHERE roadmap_id=? ORDER BY stage,id", (roadmap["id"],)):
        item = dict(row); item["topics"] = json.loads(item.pop("topics_json")); result["activities"].append(item)
    saved = db.execute("SELECT resource_id,saved_at FROM saved_learning_resources WHERE roadmap_id=? ORDER BY saved_at DESC", (roadmap["id"],)).fetchall()
    catalog = {r["id"]:r for r in _catalog_resources(db)}
    result["saved_resources"] = [{**catalog[row["resource_id"]],"saved_at":row["saved_at"]} for row in saved if row["resource_id"] in catalog]
    return result

@career.get("/job-matches")
def job_matches():
    try: sid = int(request.args["student_id"])
    except (KeyError, ValueError): return jsonify({"error":"student_id is required and must be an integer."}), 400
    with get_db() as db:
        student = db.execute("SELECT * FROM students WHERE id=?", (sid,)).fetchone()
        if not student: return jsonify({"error":"Student not found."}), 404
        jobs = db.execute("SELECT * FROM jobs ORDER BY updated_at DESC").fetchall()
        items = [{**dict(job), **_match(dict(student), dict(job))} for job in jobs]
    return jsonify({"student":dict(student),"items":items,"method":"Rule-based eligibility and exact phrase skill overlap; ML is not used."})

@career.get("/resources")
def resources():
    q = request.args.get("q", "").casefold()
    skill = normalize_skill(request.args.get("skill", "")).casefold()
    role = request.args.get("role", "").strip()
    try:
        missing_skills = parse_skills(request.args.get("missing_skills", ""))
        optional_skills = parse_skills(request.args.get("optional_skills", ""), "optional_skills")
    except ValueError:
        return jsonify({"error": "Skill filters must be comma-separated text."}), 400
    sid = request.args.get("student_id")
    student_pk = None
    if sid:
        try:
            student_pk = int(sid)
        except ValueError:
            return jsonify({"error":"student_id must be an integer."}), 400
    requested_jobs = request.args.get("job_ids", "")
    requested_job = request.args.get("job_id")
    job_pks = []
    try:
        if requested_jobs:
            job_pks = list(dict.fromkeys(int(value) for value in requested_jobs.split(",") if value))
        elif requested_job:
            job_pks = [int(requested_job)]
    except ValueError:
        return jsonify({"error":"job_id and job_ids must contain integers."}), 400
    with get_db() as db:
        if student_pk is not None and not db.execute("SELECT 1 FROM students WHERE id=?", (student_pk,)).fetchone():
            return jsonify({"error":"Student not found."}), 404
        job_comparison = None
        if job_pks:
            placeholders = ",".join("?" for _ in job_pks)
            found = db.execute(
                f"SELECT id FROM jobs WHERE id IN ({placeholders})", job_pks,
            ).fetchall()
            if len(found) != len(job_pks):
                return jsonify({"error":"One or more selected jobs were not found."}), 404
            if student_pk is not None:
                student = db.execute(
                    "SELECT student_skills FROM students WHERE id=?", (student_pk,),
                ).fetchone()
                jobs = db.execute(
                    f"SELECT * FROM jobs WHERE id IN ({placeholders}) ORDER BY id", job_pks,
                ).fetchall()
                job_rows = []
                all_required, all_optional = [], []
                required_sets, missing_sets = [], []
                for job_row in jobs:
                    job = dict(job_row)
                    required_fit = match_skills(student["student_skills"], job["required_skills"])
                    optional_fit = match_skills(student["student_skills"], job["optional_skills"])
                    required_skills = required_fit["required_skills"]
                    missing_required = required_fit["missing_skills"]
                    missing_optional = optional_fit["missing_skills"]
                    required_sets.append({skill.casefold() for skill in required_skills})
                    missing_sets.append({skill.casefold() for skill in missing_required})
                    all_required.extend(missing_required)
                    all_optional.extend(missing_optional)
                    job_rows.append({
                        "job_id": job["id"], "job_title": job["job_title"],
                        "company_name": job["company_name"], "role": job["role_category"] or job["job_title"],
                        "required_skills": required_skills, "matched_skills": required_fit["matched_skills"],
                        "missing_skills": missing_required, "missing_optional_skills": missing_optional,
                    })
                required_map = {normalize_skill(skill).casefold(): normalize_skill(skill) for skill in all_required}
                optional_map = {
                    normalize_skill(skill).casefold(): normalize_skill(skill)
                    for skill in all_optional
                    if normalize_skill(skill).casefold() not in required_map
                }
                missing_skills = list(required_map.values())
                optional_skills = list(optional_map.values())
                shared = set.intersection(*required_sets) if required_sets else set()
                shared_missing = set.intersection(*missing_sets) if missing_sets else set()
                job_comparison = {
                    "jobs": job_rows,
                    "shared_required_skills": sorted(
                        (required_map.get(key) or normalize_skill(key) for key in shared),
                        key=str.casefold,
                    ),
                    "shared_missing_skills": sorted(
                        (required_map.get(key) or normalize_skill(key) for key in shared_missing),
                        key=str.casefold,
                    ),
                    "unique_missing_skills": {
                        str(item["job_id"]): [
                            skill for skill in item["missing_skills"]
                            if sum(
                                skill.casefold() in missing for missing in missing_sets
                            ) == 1
                        ]
                        for item in job_rows
                    },
                }
        suggestions = recommendations_for_student(
            db, missing_skills, role, student_pk, job_pks, optional_skills,
        )
        recommendation_by_id = {
            item["resource"]["id"]: item for item in suggestions if item["resource"]
        }
        saved = {
            row[0] for row in db.execute(
                "SELECT resource_id FROM saved_learning_resources WHERE student_pk=?",
                (student_pk,),
            )
        } if student_pk is not None else set()
        catalog = _catalog_resources(db)
    has_role_matches = bool(role) and any(
        role.casefold() in {item.casefold() for item in resource["relevant_roles"]}
        for resource in catalog
    )
    items = []
    for resource in catalog:
        role_match = (
            not role or not has_role_matches
            or role.casefold() in {item.casefold() for item in resource["relevant_roles"]}
            or resource["id"] in recommendation_by_id
        )
        resource_skill = normalize_skill(resource["skill"]).casefold()
        skill_match = not skill or skill == resource_skill or skill in resource["name"].casefold()
        text_match = not q or q in json.dumps(resource).casefold()
        if role_match and skill_match and text_match:
            recommendation = recommendation_by_id.get(resource["id"])
            items.append({
                **resource,
                "recommended": recommendation is not None,
                "priority": recommendation["priority"] if recommendation else None,
                "priority_rank": recommendation["priority_rank"] if recommendation else None,
                "priority_basis": recommendation["priority_basis"] if recommendation else None,
                "requirement_type": recommendation["requirement_type"] if recommendation else None,
                **({"is_saved": resource["id"] in saved} if student_pk is not None else {}),
            })
    items.sort(key=lambda item: (not item["recommended"], item["title"].casefold()))
    return jsonify({
        "items": items, "recommendations": suggestions,
        "unmatched_skills": [item["skill"] for item in suggestions if not item["resource"]],
        "verified_catalog": all(resource["verified"] for resource in catalog),
        "selected_role": role or None,
        "job_comparison": job_comparison,
    })


@career.post("/resources")
def create_resource():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Send a resource object."}), 400
    fields = {
        "title": 200, "skill": 120, "domain": 120, "provider": 160,
        "resource_type": 80, "difficulty": 80, "url": 2048, "description": 2000,
    }
    resource = {}
    for field, limit in fields.items():
        value = data.get(field)
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
            return jsonify({"error": f"{field} is required and must be at most {limit} characters."}), 400
        resource[field] = value.strip()
    parsed_url = urlsplit(resource["url"])
    if parsed_url.scheme not in {"https", "http"} or not parsed_url.hostname or parsed_url.username or parsed_url.password:
        return jsonify({"error": "url must be a valid HTTP or HTTPS provider URL."}), 400
    if data.get("url_verified") is not True:
        return jsonify({"error": "Confirm that you opened and checked this URL at its provider before saving."}), 400
    raw_roles = data.get("relevant_roles", [])
    if isinstance(raw_roles, str):
        raw_roles = [role.strip() for role in raw_roles.split(",")]
    if not isinstance(raw_roles, list) or not all(isinstance(role, str) for role in raw_roles):
        return jsonify({"error": "relevant_roles must be a list or comma-separated text."}), 400
    roles = list(dict.fromkeys(role.strip() for role in raw_roles if role.strip()))
    if len(roles) > 80 or any(len(role) > 120 for role in roles):
        return jsonify({"error": "Relevant roles must be limited to 80 names of at most 120 characters."}), 400
    resource_id = f"custom-{uuid.uuid4().hex}"
    try:
        with get_db() as db:
            _catalog_resources(db)
            db.execute(
                """INSERT INTO learning_resource_catalog
                   (id,title,skill,domain,provider,resource_type,difficulty,url,description,
                    relevant_roles_json,verification_status,is_builtin)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,0)""",
                (
                    resource_id, resource["title"], normalize_skill(resource["skill"]),
                    resource["domain"], resource["provider"], resource["resource_type"],
                    resource["difficulty"], resource["url"], resource["description"],
                    json.dumps(roles), "admin_confirmed",
                ),
            )
            saved = next(item for item in _catalog_resources(db) if item["id"] == resource_id)
    except sqlite3.IntegrityError:
        return jsonify({"error": "A learning resource already uses this URL."}), 409
    return jsonify(saved), 201


@career.post("/resources/<resource_id>/save")
def save_resource(resource_id):
    data = request.get_json(silent=True) or {}
    try: sid = int(data.get("student_id"))
    except (TypeError, ValueError): return jsonify({"error":"student_id is required."}), 400
    with get_db() as db:
        catalog = _catalog_resources(db)
        if not any(resource["id"] == resource_id for resource in catalog):
            return jsonify({"error":"Resource not found in curated catalog."}), 404
        if not db.execute("SELECT 1 FROM students WHERE id=?",(sid,)).fetchone(): return jsonify({"error":"Student not found."}),404
        roadmap_id=data.get("roadmap_id")
        if roadmap_id is not None:
            try: roadmap_id=int(roadmap_id)
            except (TypeError,ValueError): return jsonify({"error":"roadmap_id must be an integer."}),400
            if not db.execute("SELECT 1 FROM career_roadmaps WHERE id=? AND student_pk=?",(roadmap_id,sid)).fetchone(): return jsonify({"error":"Roadmap not found for this student."}),404
        db.execute("INSERT OR IGNORE INTO saved_learning_resources(student_pk,resource_id,roadmap_id) VALUES (?,?,?)",(sid,resource_id,roadmap_id))
        if roadmap_id is not None: db.execute("UPDATE saved_learning_resources SET roadmap_id=? WHERE student_pk=? AND resource_id=?",(roadmap_id,sid,resource_id))
    return jsonify({"saved":True,"resource_id":resource_id,"roadmap_id":roadmap_id})

@career.get("/saved-resources")
def saved_resources():
    try: sid=int(request.args["student_id"])
    except (KeyError,ValueError): return jsonify({"error":"student_id is required."}),400
    with get_db() as db:
        ids={r[0] for r in db.execute("SELECT resource_id FROM saved_learning_resources WHERE student_pk=?",(sid,))}
        catalog = _catalog_resources(db)
    return jsonify({"items":[r for r in catalog if r["id"] in ids]})

@career.post("/roadmaps")
def create_roadmap():
    data=request.get_json(silent=True) or {}
    try: sid,jid=int(data.get("student_id")),int(data.get("job_id"))
    except (TypeError,ValueError): return jsonify({"error":"student_id and job_id are required integers."}),400
    with get_db() as db:
        student=db.execute("SELECT * FROM students WHERE id=?",(sid,)).fetchone(); job=db.execute("SELECT * FROM jobs WHERE id=?",(jid,)).fetchone()
        if not student or not job: return jsonify({"error":"Student or job not found."}),404
        match=_match(dict(student),dict(job)); snapshot={"student_id":sid,"job_id":jid,"student_name":student["student_name"],"job_title":job["job_title"],"company_name":job["company_name"],"missing_skills":match["missing_skills"],"missing_optional_skills":match["missing_optional_skills"],"matched_skills":match["matched_skills"],"matched_optional_skills":match["matched_optional_skills"],"skill_match_pct":match["skill_match_pct"],"eligibility_status":match["eligibility_status"]}
        cur=db.execute("INSERT INTO career_roadmaps(student_pk,job_pk,snapshot_json) VALUES(?,?,?)",(sid,jid,json.dumps(snapshot)))
        rid=cur.lastrowid
        suggestions = recommendations_for_student(
            db, match["missing_skills"], job["role_category"] or job["job_title"], sid, jid,
        )
        by_skill = {item["skill"].casefold(): item for item in suggestions}
        catalog = _catalog_resources(db)
        for skill in match["missing_skills"]:
            suggestion = by_skill.get(normalize_skill(skill).casefold())
            if suggestion is None:
                continue
            resource = next(
                (item for item in catalog if item["id"] == suggestion["resource"]["id"]),
                None,
            ) if suggestion["resource"] else None
            tasks=[(1,"Build the foundations",f"Explain the core concepts and vocabulary of {skill}.",[f"Core concepts of {skill}","Common terminology","Set up a practice environment"],"Beginner",""),
                   (2,"Practice with guided exercises",f"Apply {skill} to progressively harder tasks related to {job['job_title']}.",[f"Fundamentals exercises","Realistic role-based scenarios","Document mistakes and corrections"],"Beginner to intermediate",""),
                   (3,"Build a portfolio project",f"Build and document a small {job['job_title']} project demonstrating {skill}.",["Define a measurable question","Implement a complete workflow","Write a README with decisions and limitations"],"Intermediate",f"Create a {skill} portfolio artifact tailored to {job['job_title']} and explain your choices.")]
            for stage,title,obj,topics,difficulty,project in tasks:
                db.execute("INSERT INTO roadmap_activities(roadmap_id,skill,stage,title,objective,topics_json,difficulty,resource_id,project_idea) VALUES(?,?,?,?,?,?,?,?,?)",(rid,skill,stage,title,obj,json.dumps(topics),difficulty,resource["id"] if resource else "",project))
        cert_resource=next((r for r in catalog if r["category"]=="Certification" and any(s.casefold()==r["skill"].casefold() for s in match["missing_skills"])),None)
        cert_title=f"Review {cert_resource['name']}" if cert_resource else "Review relevant certifications"
        cert_objective=(f"Compare this official credential with the {job['job_title']} requirements; it is optional unless the saved job explicitly requires it.") if cert_resource else "Check the job's configured certification requirements; pursue credentials only when relevant."
        cert_topics=match["missing_certifications"] or ([cert_resource["name"], cert_resource["cost"]] if cert_resource else ["No certification is configured as mandatory for this role."])
        db.execute("INSERT INTO roadmap_activities(roadmap_id,stage,title,objective,topics_json,resource_id) VALUES(?,4,?,?,?,?)",(rid,cert_title,cert_objective,json.dumps(cert_topics),cert_resource["id"] if cert_resource else ""))
        db.execute("INSERT INTO roadmap_activities(roadmap_id,stage,title,objective,topics_json) VALUES(?,5,?,?,?)",(rid,"Interview practice",f"Practice explaining your evidence for the {job['job_title']} role. Prompts are generated practice, not actual company questions.",json.dumps([f"Explain a project where you used {s}." for s in (match["missing_skills"] or match["matched_skills"][:3])] or ["Describe how you would approach the role's main responsibilities.","Explain a project you are proud of."])))
        db.execute("INSERT INTO roadmap_activities(roadmap_id,stage,title,objective,topics_json) VALUES(?,6,?,?,?)",(rid,"Re-evaluate readiness","Recalculate configured eligibility and exact phrase skill coverage against the saved role.",json.dumps(["Update your profile with skills you can substantiate.","Review missing requirements and eligibility rules."])))
        roadmap=db.execute("SELECT * FROM career_roadmaps WHERE id=?",(rid,)).fetchone()
        return jsonify(_roadmap_json(db,roadmap)),201

@career.get("/roadmaps")
def list_roadmaps():
    try: sid=int(request.args["student_id"])
    except (KeyError,ValueError): return jsonify({"error":"student_id is required."}),400
    with get_db() as db: rows=db.execute("SELECT * FROM career_roadmaps WHERE student_pk=? ORDER BY updated_at DESC,id DESC",(sid,)).fetchall(); items=[_roadmap_json(db,r) for r in rows]
    return jsonify({"items":items})

@career.get("/roadmaps/<int:roadmap_id>")
def get_roadmap(roadmap_id):
    with get_db() as db:
        row=db.execute("SELECT * FROM career_roadmaps WHERE id=?",(roadmap_id,)).fetchone()
        return (jsonify(_roadmap_json(db,row)),200) if row else (jsonify({"error":"Roadmap not found."}),404)

@career.patch("/roadmap-activities/<int:activity_id>")
def update_activity(activity_id):
    data=request.get_json(silent=True) or {}; done=data.get("is_completed")
    if not isinstance(done,bool): return jsonify({"error":"is_completed must be boolean."}),400
    with get_db() as db:
        row=db.execute("SELECT id FROM roadmap_activities WHERE id=?",(activity_id,)).fetchone()
        if not row: return jsonify({"error":"Activity not found."}),404
        db.execute("UPDATE roadmap_activities SET is_completed=?,completed_at=? WHERE id=?",(int(done),datetime.now(timezone.utc).isoformat() if done else None,activity_id))
        db.execute("UPDATE career_roadmaps SET updated_at=CURRENT_TIMESTAMP WHERE id=(SELECT roadmap_id FROM roadmap_activities WHERE id=?)",(activity_id,))
    return jsonify({"id":activity_id,"is_completed":done})

@career.post("/roadmaps/<int:roadmap_id>/recalculate")
def recalculate_roadmap(roadmap_id):
    with get_db() as db:
        row=db.execute("SELECT * FROM career_roadmaps WHERE id=?",(roadmap_id,)).fetchone()
        if not row:return jsonify({"error":"Roadmap not found."}),404
        student=db.execute("SELECT * FROM students WHERE id=?",(row["student_pk"],)).fetchone(); job=db.execute("SELECT * FROM jobs WHERE id=?",(row["job_pk"],)).fetchone(); m=_match(dict(student),dict(job))
        snapshot=json.loads(row["snapshot_json"]); snapshot.update({"missing_skills":m["missing_skills"],"matched_skills":m["matched_skills"],"skill_match_pct":m["skill_match_pct"],"eligibility_status":m["eligibility_status"],"match_category":m["match_category"],"eligibility_reasons":m["eligibility_reasons"],"recalculated_at":datetime.now(timezone.utc).isoformat()})
        db.execute("UPDATE career_roadmaps SET snapshot_json=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(json.dumps(snapshot),roadmap_id)); updated=db.execute("SELECT * FROM career_roadmaps WHERE id=?",(roadmap_id,)).fetchone()
        return jsonify(_roadmap_json(db,updated))

@career.get("/interview-prep")
def interview_prep():
    try: sid,jid=int(request.args["student_id"]),int(request.args["job_id"])
    except (KeyError,ValueError): return jsonify({"error":"student_id and job_id are required."}),400
    with get_db() as db:
        student=db.execute("SELECT * FROM students WHERE id=?",(sid,)).fetchone(); job=db.execute("SELECT * FROM jobs WHERE id=?",(jid,)).fetchone()
        if not student or not job:return jsonify({"error":"Student or job not found."}),404
        fit=_match(dict(student),dict(job))
    skills=fit["missing_skills"]+fit["matched_skills"]
    return jsonify({"role":job["job_title"],"company":job["company_name"],"method":"Generated practice prompts based on this saved job and profile; these are not actual company interview questions.","sections":[{"category":"Technical","topics":skills,"prompts":[{"question":f"Explain a practical use of {s} in a project, including one trade-off.","difficulty":"Intermediate","skill":s} for s in skills]},{"category":"Project explanation","topics":_split(student["projects"]),"prompts":[{"question":"Describe the goal, your contribution, a difficult decision, and what you would improve.","difficulty":"Intermediate","skill":"Project communication"}]},{"category":"HR and role motivation","topics":[job["job_title"]],"prompts":[{"question":f"Why are you interested in a {job['job_title']} role at {job['company_name']}? Use evidence from your saved profile.","difficulty":"Foundational","skill":"Communication"}]},{"category":"SQL and problem solving","topics":[s for s in skills if s.casefold() in ("sql","python","data structures","algorithms")],"prompts":[{"question":"Talk through your assumptions and validation before presenting a solution.","difficulty":"Foundational","skill":"Problem solving"}]}]})


def _interview_questions(role, skills):
    focus = skills[:3] or [role]
    return [
        {"id": 1, "category": "Technical application", "focus_skills": focus[:2], "question": f"How would you apply {focus[0]} to a practical problem in a {role} role? Describe your approach and how you would validate it."},
        {"id": 2, "category": "Problem solving", "focus_skills": focus[1:3] or focus[:1], "question": f"Walk through how you would investigate a difficult {focus[-1]} problem, including the trade-offs you would consider."},
        {"id": 3, "category": "Project evidence", "focus_skills": focus[:2], "question": f"Describe a project or experience relevant to {role}. Explain your contribution, the evidence of impact, and what you learned."},
        {"id": 4, "category": "Role scenario", "focus_skills": focus[:2], "question": f"A stakeholder asks for a quick answer in a {role} task, but the available data or requirements are incomplete. How would you proceed?"},
        {"id": 5, "category": "Communication", "focus_skills": focus[:1], "question": f"Explain a technical decision relevant to {role} to a non-technical teammate, and describe how you would confirm they understood."},
    ]


def _score_interview_answer(question, answer):
    word_count = len(re.findall(r"\b[\w'-]+\b", answer))
    lower = answer.casefold()
    relevance = any(term.casefold() in lower for term in question["focus_skills"] if term)
    evidence = any(term in lower for term in ("for example", "project", "built", "implemented", "used", "created", "analyzed"))
    reflection = any(term in lower for term in ("result", "impact", "trade-off", "tradeoff", "validated", "validation", "learned", "improved", "measured"))
    score = (2 if word_count >= 30 else 0) + int(relevance) + int(evidence) + int(reflection)
    improvements = []
    if word_count < 30:
        improvements.append("Add enough detail to explain the situation and your steps.")
    if not relevance:
        improvements.append("Connect the answer to the role or its relevant skills.")
    if not evidence:
        improvements.append("Include a specific project or example that shows your contribution.")
    if not reflection:
        improvements.append("Explain a result, validation step, trade-off, or lesson learned.")
    return {
        "score": score, "max_score": 5, "word_count": word_count,
        "feedback": "The answer includes " + (", ".join(label for label, met in (
            ("sufficient detail", word_count >= 30), ("role-related terminology", relevance),
            ("a concrete example", evidence), ("reflection or outcome", reflection),
        ) if met) or "none of the current rubric signals") + ".",
        "improvements": improvements,
    }


@career.post("/mock-interviews")
def create_mock_interview():
    data = request.get_json(silent=True) or {}
    try:
        student_pk, job_pk = int(data.get("student_id")), int(data.get("job_id"))
    except (TypeError, ValueError):
        return jsonify({"error": "student_id and job_id are required integers."}), 400
    with get_db() as db:
        student = db.execute("SELECT * FROM students WHERE id=?", (student_pk,)).fetchone()
        job = db.execute("SELECT * FROM jobs WHERE id=?", (job_pk,)).fetchone()
        if not student or not job:
            return jsonify({"error": "Student or job not found."}), 404
        match = _match(dict(student), dict(job))
        questions = _interview_questions(job["job_title"], match["missing_skills"] + match["matched_skills"])
        cursor = db.execute(
            "INSERT INTO mock_interview_attempts(student_pk,job_pk,role,questions_json) VALUES(?,?,?,?)",
            (student_pk, job_pk, job["job_title"], json.dumps(questions)),
        )
        attempt = db.execute("SELECT * FROM mock_interview_attempts WHERE id=?", (cursor.lastrowid,)).fetchone()
    return jsonify({
        "id": attempt["id"], "student_id": student_pk, "job_id": job_pk, "role": attempt["role"],
        "questions": questions, "status": "in_progress", "scoring_method": attempt["scoring_method"],
        "notice": "Rule-based practice feedback only; this score is not an expert or human assessment.",
    }), 201


@career.post("/mock-interviews/<int:attempt_id>/submit")
def submit_mock_interview(attempt_id):
    data = request.get_json(silent=True) or {}
    answers = data.get("answers")
    if not isinstance(answers, list):
        return jsonify({"error": "answers must be a list of question_id and answer objects."}), 400
    with get_db() as db:
        attempt = db.execute("SELECT * FROM mock_interview_attempts WHERE id=?", (attempt_id,)).fetchone()
        if not attempt:
            return jsonify({"error": "Mock interview attempt not found."}), 404
        if attempt["submitted_at"]:
            return jsonify({"error": "This mock interview has already been submitted."}), 409
        questions = json.loads(attempt["questions_json"])
        question_ids = {question["id"] for question in questions}
        answer_map = {}
        for item in answers:
            if not isinstance(item, dict):
                return jsonify({"error": "Each answer must include question_id and answer."}), 400
            try:
                question_id = int(item.get("question_id"))
            except (TypeError, ValueError):
                return jsonify({"error": "question_id must be an integer."}), 400
            text = item.get("answer")
            if question_id not in question_ids or question_id in answer_map or not isinstance(text, str) or len(text) > 10000:
                return jsonify({"error": "Answers must have unique valid question IDs and text of at most 10000 characters."}), 400
            answer_map[question_id] = text.strip()
        if set(answer_map) != question_ids:
            return jsonify({"error": "Submit one answer for every interview question."}), 400
        results = []
        stored_answers = []
        for question in questions:
            answer = answer_map[question["id"]]
            result = _score_interview_answer(question, answer)
            results.append({"question_id": question["id"], **result})
            stored_answers.append({"question_id": question["id"], "answer": answer})
        score_pct = round(sum(result["score"] for result in results) * 100 / (len(results) * 5), 2)
        suggestions = list(dict.fromkeys(item for result in results for item in result["improvements"]))
        rubric = "Each answer is scored on detail (30+ words, 2 points), role-related terminology (1), a concrete example (1), and an outcome/reflection/validation signal (1)."
        db.execute(
            "UPDATE mock_interview_attempts SET answers_json=?,score_pct=?,feedback_json=?,suggestions_json=?,submitted_at=? WHERE id=?",
            (json.dumps(stored_answers), score_pct, json.dumps(results), json.dumps(suggestions), datetime.now(timezone.utc).isoformat(), attempt_id),
        )
        updated = db.execute("SELECT * FROM mock_interview_attempts WHERE id=?", (attempt_id,)).fetchone()
    return jsonify({
        "id": attempt_id, "role": updated["role"], "score_pct": score_pct,
        "feedback": results, "suggestions": suggestions, "scoring_method": updated["scoring_method"],
        "rubric": rubric, "notice": "Rule-based practice feedback only; this score is not an expert or human assessment.",
        "submitted_at": updated["submitted_at"],
    })


@career.get("/mock-interviews")
def mock_interview_history():
    try:
        student_pk = int(request.args["student_id"])
    except (KeyError, ValueError):
        return jsonify({"error": "student_id is required and must be an integer."}), 400
    with get_db() as db:
        if not db.execute("SELECT 1 FROM students WHERE id=?", (student_pk,)).fetchone():
            return jsonify({"error": "Student not found."}), 404
        rows = db.execute(
            "SELECT * FROM mock_interview_attempts WHERE student_pk=? ORDER BY created_at DESC,id DESC LIMIT 50",
            (student_pk,),
        ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["questions"] = json.loads(item.pop("questions_json"))
        item["answers"] = json.loads(item.pop("answers_json"))
        item["feedback"] = json.loads(item.pop("feedback_json"))
        item["suggestions"] = json.loads(item.pop("suggestions_json"))
        item["status"] = "completed" if item["submitted_at"] else "in_progress"
        items.append(item)
    return jsonify({"items": items})


@career.post("/skill-proficiency")
def record_skill_proficiency():
    data = request.get_json(silent=True) or {}
    try:
        student_pk = int(data.get("student_id"))
        current = int(data.get("current_proficiency"))
    except (TypeError, ValueError):
        return jsonify({"error": "student_id and current_proficiency are required integers."}), 400
    skill = normalize_skill(data.get("skill", "")) if isinstance(data.get("skill"), str) else ""
    if not skill or len(skill) > 120 or not 1 <= current <= 5:
        return jsonify({"error": "skill is required (120 characters maximum) and current_proficiency must be between 1 and 5."}), 400
    try:
        progress = float(data.get("learning_progress_pct", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "learning_progress_pct must be numeric."}), 400
    if not 0 <= progress <= 100:
        return jsonify({"error": "learning_progress_pct must be between 0 and 100."}), 400
    assessment_date = data.get("assessment_date") or datetime.now(timezone.utc).date().isoformat()
    if not isinstance(assessment_date, str):
        return jsonify({"error": "assessment_date must be an ISO date."}), 400
    try:
        datetime.strptime(assessment_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "assessment_date must use YYYY-MM-DD format."}), 400
    with get_db() as db:
        if not db.execute("SELECT 1 FROM students WHERE id=?", (student_pk,)).fetchone():
            return jsonify({"error": "Student not found."}), 404
        previous = db.execute(
            "SELECT current_proficiency FROM skill_proficiency_history WHERE student_pk=? AND lower(skill)=? ORDER BY assessment_date DESC,id DESC LIMIT 1",
            (student_pk, skill.casefold()),
        ).fetchone()
        previous_value = previous["current_proficiency"] if previous else None
        cursor = db.execute(
            "INSERT INTO skill_proficiency_history(student_pk,skill,previous_proficiency,current_proficiency,assessment_date,learning_progress_pct) VALUES(?,?,?,?,?,?)",
            (student_pk, skill, previous_value, current, assessment_date, progress),
        )
        row = db.execute("SELECT * FROM skill_proficiency_history WHERE id=?", (cursor.lastrowid,)).fetchone()
    result = dict(row)
    result["improvement"] = current - previous_value if previous_value is not None else None
    return jsonify(result), 201


@career.get("/skill-proficiency")
def skill_proficiency_history():
    try:
        student_pk = int(request.args["student_id"])
    except (KeyError, ValueError):
        return jsonify({"error": "student_id is required and must be an integer."}), 400
    with get_db() as db:
        if not db.execute("SELECT 1 FROM students WHERE id=?", (student_pk,)).fetchone():
            return jsonify({"error": "Student not found."}), 404
        rows = db.execute(
            "SELECT * FROM skill_proficiency_history WHERE student_pk=? ORDER BY assessment_date,id",
            (student_pk,),
        ).fetchall()
    history = []
    for row in rows:
        item = dict(row)
        item["improvement"] = item["current_proficiency"] - item["previous_proficiency"] if item["previous_proficiency"] is not None else None
        history.append(item)
    return jsonify({"items": history})


@career.get("/career-analytics/<int:student_pk>")
def career_analytics(student_pk):
    with get_db() as db:
        student=db.execute("SELECT * FROM students WHERE id=?",(student_pk,)).fetchone()
        if not student:return jsonify({"error":"Student not found."}),404
        jobs=db.execute("SELECT * FROM jobs").fetchall(); matches=[{**dict(j),**_match(dict(student),dict(j))} for j in jobs]
        skill_demand = Counter()
        skill_names = {}
        for match in matches:
            for skill in match["missing_skills"]:
                key = normalize_skill(skill).casefold()
                skill_demand[key] += 1
                skill_names.setdefault(key, normalize_skill(skill))
        analysis_rows = db.execute(
            """SELECT id,job_record_id,job_title,company_name,role_category,predicted_label,
                      selected_model,class_probabilities_json,model_notice,created_at
               FROM analyses
               WHERE student_record_id=? OR student_id=?
               ORDER BY created_at DESC,id DESC LIMIT 200""",
            (student_pk, student["student_id"]),
        ).fetchall()
        latest_analyses = []
        seen_jobs = set()
        for row in analysis_rows:
            item = dict(row)
            job_key = (
                f"record:{item['job_record_id']}"
                if item["job_record_id"] is not None
                else f"title:{(item['job_title'] or '').casefold()}|{(item['company_name'] or '').casefold()}"
            )
            if job_key in seen_jobs:
                continue
            seen_jobs.add(job_key)
            item["class_probabilities"] = json.loads(item.pop("class_probabilities_json") or "{}")
            latest_analyses.append(item)
        roads=db.execute("SELECT * FROM career_roadmaps WHERE student_pk=? ORDER BY updated_at DESC",(student_pk,)).fetchall()
        total=done=0; road_data=[]
        for road in roads:
            acts=db.execute("SELECT is_completed FROM roadmap_activities WHERE roadmap_id=?",(road["id"],)).fetchall(); total+=len(acts); done+=sum(a[0] for a in acts)
            road_data.append({"id":road["id"],"job_title":json.loads(road["snapshot_json"])["job_title"],"completed":sum(a[0] for a in acts),"total":len(acts)})
        history = [dict(row) for row in db.execute(
            "SELECT skill,previous_proficiency,current_proficiency,assessment_date,learning_progress_pct FROM skill_proficiency_history WHERE student_pk=? ORDER BY assessment_date,id",
            (student_pk,),
        )]
        fields=["student_name","email","degree","branch","specialization","graduation_year","cgpa","student_skills","projects","certifications","areas_of_interest","preferred_job_roles"]
        filled=sum(bool(student[f]) for f in fields); skills=_split(student["student_skills"])
        latest_by_skill = {}
        for item in history:
            key = normalize_skill(item["skill"]).casefold()
            latest_by_skill.setdefault(key, {"skill": normalize_skill(item["skill"]), "first": item})
            latest_by_skill[key]["latest"] = item
        proficiency = [{
            "skill": values["skill"], "current_proficiency": values["latest"]["current_proficiency"],
            "previous_proficiency": values["latest"]["previous_proficiency"],
            "improvement": values["latest"]["current_proficiency"] - values["first"]["current_proficiency"],
            "assessment_date": values["latest"]["assessment_date"],
            "learning_progress_pct": values["latest"]["learning_progress_pct"],
        } for values in latest_by_skill.values()]
        interview_count = db.execute("SELECT COUNT(*) FROM mock_interview_attempts WHERE student_pk=? AND submitted_at IS NOT NULL", (student_pk,)).fetchone()[0]
    return jsonify({"student":dict(student),"profile_completeness_pct":round(filled*100/len(fields)),"profile_fields_filled":filled,"profile_fields_total":len(fields),"skill_count":len(skills),"job_count":len(matches),"match_categories":{k:sum(1 for m in matches if m["match_category"]==k) for k in ("strong_match","potential_match","not_eligible")},"jobs":matches,"skill_demand":[{"skill":skill_names[key],"missing_from_jobs":count} for key,count in sorted(skill_demand.items(),key=lambda item:(-item[1],skill_names[item[0]].casefold()))],"latest_analyses":latest_analyses,"roadmaps":road_data,"roadmap_progress_pct":round(done*100/total) if total else None,"activities_completed":done,"activities_total":total,"certifications_recorded":len(_split(student["certifications"])),"projects_recorded":len([p for p in (student["projects"] or "").splitlines() if p.strip()]),"proficiency_history":history,"proficiency_by_skill":proficiency,"proficiency_skills_tracked":len(proficiency),"average_proficiency":round(sum(p["current_proficiency"] for p in proficiency)/len(proficiency),2) if proficiency else None,"mock_interviews_completed":interview_count,"proficiency":"Proficiency is self-assessed on a 1–5 scale; progress is student-reported and does not constitute a validated assessment.","calculation":"Profile completeness is the share of 12 listed profile fields with non-empty values. Skill coverage is case-insensitive skill overlap per job. Skill demand counts saved jobs where each skill remains missing. Roadmap progress is completed activities divided by persisted roadmap activities. Proficiency change is the latest minus first saved self-assessment for each skill."})
