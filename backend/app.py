"""Flask API for Placement Intelligence. Notebook metrics are historical; prediction needs matching Colab artifacts."""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import csv
import io
from datetime import datetime, timezone
from typing import Any

from flask import Flask, jsonify, make_response, request
from flask_cors import CORS

try:
    from .config import API_ORIGINS, DATABASE_PATH, DATABASE_PATH_SOURCE
    from .database import get_db, init_db
    from .dataset_support import dataset_index, suggest_profile
    from .job_analyzer import analyze_job_description
    from .model import ModelRegistry
    from .recommendation import recommendations_for
    from .report_generator import generate_pdf
    from .skill_matching import analyze_gap, categorize_skill, match_skills, normalize_skill, parse_skills
    from .career_intelligence import RESOURCES, _catalog_resources, career, recommendations_for_student, skill_job_counts_for_student
except ImportError:
    from config import API_ORIGINS, DATABASE_PATH, DATABASE_PATH_SOURCE
    from database import get_db, init_db
    from dataset_support import dataset_index, suggest_profile
    from job_analyzer import analyze_job_description
    from model import ModelRegistry
    from recommendation import recommendations_for
    from report_generator import generate_pdf
    from skill_matching import analyze_gap, categorize_skill, match_skills, normalize_skill, parse_skills
    from career_intelligence import RESOURCES, _catalog_resources, career, recommendations_for_student, skill_job_counts_for_student

app = Flask(__name__)
app.register_blueprint(career)
app.config["MAX_CONTENT_LENGTH"] = 1_000_000
CORS(app, resources={r"/api/*": {"origins": API_ORIGINS}})
app.logger.setLevel(logging.INFO)
try:
    app.logger.info("SQLite database path (%s): %s", DATABASE_PATH_SOURCE, DATABASE_PATH)
    if DATABASE_PATH_SOURCE == "PLACEMENT_DB_PATH":
        app.logger.warning("PLACEMENT_DB_PATH overrides the project default; verify this path is intentional.")
    init_db()
    DATABASE_READY = True
except Exception:
    DATABASE_READY = False
    app.logger.exception("SQLite initialization failed")
models = ModelRegistry()

NUMERIC_FIELDS = {
    "cgpa": (0, 10, False),
    "coding_skill_score": (0, 100, False),
    "aptitude_score": (0, 100, False),
    "communication_skill_score": (0, 100, False),
    "logical_reasoning_score": (0, 100, False),
    "mock_interview_score": (0, 100, False),
    "backlogs": (0, 100, True),
    "github_repos": (0, 100000, True),
    "internships_count": (0, 100, True),
    "projects_count": (0, 1000, True),
}


def api_error(message: str, status: int = 400, **extra: Any):
    return jsonify({"error": message, **extra}), status


def body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else None


def parse_bool(value: Any, field: str) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if value in (0, 1):
        return int(value)
    if isinstance(value, str):
        if value.casefold() in {"true", "yes", "1"}:
            return 1
        if value.casefold() in {"false", "no", "0"}:
            return 0
    raise ValueError(f"{field} must be yes or no.")


def validate_numbers(data: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    result = {}
    for field, (minimum, maximum, integer) in NUMERIC_FIELDS.items():
        if field not in data:
            if not partial:
                raise ValueError(f"{field} is required.")
            continue
        raw = data[field]
        if raw in (None, ""):
            if not partial:
                raise ValueError(f"{field} is required.")
            result[field] = None
            continue
        if isinstance(raw, bool):
            raise ValueError(f"{field} must be numeric.")
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise ValueError(f"{field} must be numeric.") from None
        if not minimum <= value <= maximum:
            raise ValueError(f"{field} must be between {minimum} and {maximum}.")
        if integer and not value.is_integer():
            raise ValueError(f"{field} must be a whole number.")
        result[field] = int(value) if integer else value
    return result


def validate_student(data: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    result = validate_numbers(data, partial)
    rules = {
        "student_id": (120, True), "student_name": (160, True), "email": (254, False),
        "branch": (80, True), "student_skills": (10000, False),
    }
    for field, (limit, required) in rules.items():
        if field not in data:
            if required and not partial:
                raise ValueError(f"{field} is required.")
            continue
        value = data[field]
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise ValueError(f"{field} must be text.")
        value = value.strip()
        if len(value) > limit:
            raise ValueError(f"{field} must be {limit} characters or fewer.")
        if required and not value and not partial:
            raise ValueError(f"{field} is required.")
        result[field] = (value or None) if field == "email" else value
    if result.get("email") and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", result["email"]):
        raise ValueError("email must be a valid email address.")
    for field, limit in {"degree":160,"specialization":160,"areas_of_interest":3000,"preferred_job_roles":3000,"certifications":10000,"projects":10000}.items():
        if field in data:
            value=data[field] or ""
            if not isinstance(value,str) or len(value)>limit: raise ValueError(f"{field} must be text with at most {limit} characters.")
            result[field]=value.strip()
    if "graduation_year" in data:
        raw=data["graduation_year"]
        if raw in (None,""): result["graduation_year"]=None
        else:
            try: year=int(raw)
            except (TypeError,ValueError): raise ValueError("graduation_year must be a whole year.") from None
            if not 2000<=year<=2100: raise ValueError("graduation_year must be between 2000 and 2100.")
            result["graduation_year"]=year
    if "experience_years" in data:
        try: years=float(data["experience_years"] or 0)
        except (TypeError,ValueError): raise ValueError("experience_years must be numeric.") from None
        if not 0<=years<=60: raise ValueError("experience_years must be between 0 and 60.")
        result["experience_years"]=years
    if result.get("branch"):
        branches = dataset_index().get("branches", [])
        if branches and result["branch"] not in branches:
            raise ValueError("branch must match a branch in the supplied dataset.")
    return result


def validate_job(data: dict[str, Any], partial: bool = False) -> dict[str, Any]:
    result = {}
    required = {"company_name", "job_title"}
    limits = {
        "external_job_id": 120, "company_name": 180, "job_title": 180,
        "job_description": 30000, "location": 500, "work_mode": 80,
        "role_category": 120, "job_url": 2000,
    }
    for field, limit in limits.items():
        if field not in data:
            if field in required and not partial:
                raise ValueError(f"{field} is required.")
            continue
        value = data[field]
        if value is None:
            value = ""
        if not isinstance(value, str):
            raise ValueError(f"{field} must be text.")
        value = value.strip()
        if len(value) > limit:
            raise ValueError(f"{field} must be {limit} characters or fewer.")
        if field in required and not partial and not value:
            raise ValueError(f"{field} is required.")
        result[field] = (value or None) if field == "external_job_id" else value
    if "required_degree" in data:
        value=data["required_degree"] or ""
        if not isinstance(value,str) or len(value)>160: raise ValueError("required_degree must be text with at most 160 characters.")
        result["required_degree"]=value.strip()
    if "required_skills" in data:
        result["required_skills"] = ", ".join(parse_skills(data["required_skills"], "required_skills"))
    if "optional_skills" in data:
        result["optional_skills"] = ", ".join(parse_skills(data["optional_skills"], "optional_skills"))
    for field in ("experience_min_yrs", "experience_max_yrs"):
        if field in data:
            value = data[field]
            if value in (None, ""):
                result[field] = None
            else:
                try:
                    value = float(value)
                except (TypeError, ValueError):
                    raise ValueError(f"{field} must be numeric.") from None
                if not 0 <= value <= 60:
                    raise ValueError(f"{field} must be between 0 and 60.")
                result[field] = value
    low, high = result.get("experience_min_yrs"), result.get("experience_max_yrs")
    if low is not None and high is not None and high < low:
        raise ValueError("experience_max_yrs cannot be lower than experience_min_yrs.")
    if "is_fresher_friendly" in data:
        result["is_fresher_friendly"] = parse_bool(data["is_fresher_friendly"], "is_fresher_friendly")
    if "min_cgpa" in data:
        raw=data["min_cgpa"]
        if raw in (None,""): result["min_cgpa"]=None
        else:
            try: value=float(raw)
            except (TypeError,ValueError): raise ValueError("min_cgpa must be numeric.") from None
            if not 0<=value<=10: raise ValueError("min_cgpa must be between 0 and 10.")
            result["min_cgpa"]=value
    for field in ("eligible_branches","required_certifications"):
        if field in data:
            result[field] = ", ".join(parse_skills(data[field], field))
    return result


def serialize_analysis(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in ("matched_skills_json", "missing_skills_json", "additional_skills_json", "class_probabilities_json", "input_snapshot_json"):
        if key in result:
            target = key.removesuffix("_json")
            fallback = "{}" if "probabilities" in key else "[]"
            result[target] = json.loads(result.pop(key) or fallback)
    return result


def _metric_pct(metric: dict[str, Any], percent_key: str, *fraction_keys: str) -> float | None:
    value = metric.get(percent_key)
    if value is not None:
        return float(value)
    for key in fraction_keys:
        value = metric.get(key)
        if value is not None:
            return round(float(value) * 100, 4)
    return None


def normalized_evaluation_metrics() -> list[dict[str, Any]]:
    """Adapt the notebook's native metric keys for the frontend's percent-based schema."""
    normalized = []
    for metric in models.config.get("evaluation_metrics", []):
        if not isinstance(metric, dict):
            continue
        normalized.append({
            **metric,
            "model": metric.get("model", metric.get("Model", "Unknown")),
            "accuracy_pct": _metric_pct(metric, "accuracy_pct", "Accuracy"),
            "suitable_precision_pct": _metric_pct(metric, "suitable_precision_pct", "Precision"),
            "suitable_recall_pct": _metric_pct(metric, "suitable_recall_pct", "Recall"),
            "suitable_f1_pct": _metric_pct(metric, "suitable_f1_pct", "F1 Score"),
        })
    return normalized


def normalized_cross_validation_metrics() -> list[dict[str, Any]]:
    source = models.config.get("cross_validation_metrics") or models.config.get("cross_validation", [])
    normalized = []
    for metric in source:
        if not isinstance(metric, dict):
            continue
        normalized.append({
            **metric,
            "model": metric.get("model", metric.get("Model", "Unknown")),
            "suitable_f1_pct": _metric_pct(metric, "suitable_f1_pct", "CV suitable F1"),
            "suitable_precision_pct": _metric_pct(metric, "suitable_precision_pct", "CV suitable precision"),
            "suitable_recall_pct": _metric_pct(metric, "suitable_recall_pct", "CV suitable recall"),
        })
    return normalized


def model_row(data: dict[str, Any]) -> dict[str, float]:
    # Numeric inputs may be omitted/blank here because the saved training medians
    # are the inference-time missing-value policy. Record CRUD remains strict.
    numeric = validate_numbers(data, partial=True)
    maps = models.config.get("categorical_features", {})
    row = {name: 0.0 for name in models.features}
    for feature in models.config.get("numeric_features", []):
        row[feature] = float("nan")
    row.update({key: float(value) for key, value in numeric.items() if value is not None})
    for field, mapping in maps.items():
        selected = data.get(field)
        if selected not in mapping:
            raise ValueError(f"{field} must be one of: {', '.join(mapping)}.")
        encoded = mapping[selected]
        if encoded:
            row[encoded] = 1.0
    return row


def save_analysis(db: sqlite3.Connection, data: dict[str, Any], result: dict[str, Any],
                  student_pk: int | None = None, job_pk: int | None = None) -> int:
    selected = (data.get("algorithm") or "").strip()
    output = result.get("predictions", {}).get(selected, {})
    snapshot = {
        key: value for key, value in data.items()
        if key not in {"request_prediction", "algorithm", "student_record_id", "job_record_id",
                       "id", "created_at", "updated_at"}
    }
    cursor = db.execute(
        """INSERT INTO analyses
        (student_record_id,job_record_id,student_id,student_name,email,job_id,job_title,role_category,company_name,
         skill_match_pct,matched_skills_json,missing_skills_json,additional_skills_json,
         predicted_label,selected_model,class_probabilities_json,input_snapshot_json,model_notice)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (student_pk, job_pk, data.get("student_id") or "", data.get("student_name") or "",
         data.get("email") or "", data.get("job_id") or data.get("external_job_id") or "",
         data.get("job_title", ""), data.get("role_category", ""), data.get("company_name", ""),
         result["matching"].get("skill_match_pct"), json.dumps(result["matching"]["matched_skills"]),
         json.dumps(result["matching"]["missing_skills"]), json.dumps(result["matching"]["additional_skills"]),
         output.get("predicted_label"), selected if output else "", json.dumps(output.get("class_probabilities", {})),
         json.dumps(snapshot),
         output.get("notice") or result.get("prediction_error") or "Synthetic target; not a verified placement outcome."),
    )
    analysis_id = int(cursor.lastrowid)
    for skill in result["skill_gap"]["missing_skills"]:
        db.execute("INSERT INTO skill_gaps (analysis_id,skill,category,importance) VALUES (?,?,?,?)",
                   (analysis_id, skill, categorize_skill(skill), "Unranked"))
    for item in result["recommendations"]:
        db.execute("""INSERT INTO learning_recommendations
            (analysis_id,skill,category,why_it_matters,learning_activity,project_idea,priority,priority_basis,requirement_type)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (analysis_id, item["skill"], item["category"], item["why_it_matters"], item["learning_activity"],
             item["project_idea"], item["priority"], item["priority_basis"], item["requirement_type"]))
    return analysis_id


def read_report(db: sqlite3.Connection, analysis_id: int):
    row = db.execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    if row is None:
        return None
    report = serialize_analysis(row)
    report["recommendations"] = [dict(item) for item in db.execute(
        "SELECT skill,category,why_it_matters,learning_activity,project_idea,priority,priority_basis,is_completed FROM learning_recommendations WHERE analysis_id=? ORDER BY id",
        (analysis_id,),
    )]
    return report


@app.get("/")
def home():
    return jsonify({"message": "Placement Intelligence API", "docs": "/api/docs"})


@app.get("/api/docs")
def api_docs():
    return jsonify({"service": "Placement Intelligence API", "endpoints": [
        "GET /api/health", "GET /api/model-info", "GET /api/model-performance", "POST /api/compare-models",
        "GET /api/dataset-info", "GET /api/dashboard", "GET/POST /api/students",
        "GET/PUT/DELETE /api/students/<id>", "GET/POST /api/jobs", "GET/PUT/DELETE /api/jobs/<id>",
        "POST /api/analyze-job-description", "POST /api/match-skills", "POST /api/analyze-skill-gap",
        "POST /api/analyze", "POST /api/predict", "GET /api/analysis-history",
        "POST /api/generate-report", "GET /api/export-analysis.csv",
        "GET /api/learning-recommendations", "PATCH /api/learning-recommendations/<id>",
        "GET /api/job-matches?student_id=<id>", "POST /api/roadmaps", "GET /api/roadmaps?student_id=<id>",
        "GET /api/roadmaps/<id>", "PATCH /api/roadmap-activities/<id>", "POST /api/roadmaps/<id>/recalculate",
        "GET /api/resources", "POST /api/resources/<resource_id>/save", "GET /api/saved-resources?student_id=<id>",
        "GET /api/interview-prep?student_id=<id>&job_id=<id>", "POST /api/mock-interviews",
        "POST /api/mock-interviews/<id>/submit", "GET /api/mock-interviews?student_id=<id>",
        "POST /api/skill-proficiency", "GET /api/skill-proficiency?student_id=<id>",
        "GET /api/career-analytics/<student_id>",
    ]})


@app.get("/api/health")
@app.get("/health")
def health():
    return jsonify({
        "status": "healthy" if DATABASE_READY else "degraded",
        "database_ready": DATABASE_READY,
        "database_path": str(DATABASE_PATH),
        "database_path_source": DATABASE_PATH_SOURCE,
        "model": models.status(),
        "target_notice": "suitability_label_synthetic is synthetic and not a verified placement outcome.",
    })


@app.get("/api/model-info")
def model_info():
    has_final_run = bool(models.config.get("training_rows") and models.config.get("evaluation_rows"))
    return jsonify({
        "model_type": models.config.get("model_type"),
        "target_column": models.config.get("target_column"),
        "features": models.features,
        "preprocessing": models.config.get("preprocessing"),
        "historical": not has_final_run,
        "selected_model": models.config.get("selected_model"),
        "evaluation_metrics": normalized_evaluation_metrics(),
        "cross_validation_metrics": normalized_cross_validation_metrics(),
        "confusion_matrices": models.config.get("confusion_matrices", {}),
        "evaluation_rows": models.config.get("evaluation_rows", models.config.get("testing_rows")),
        "evaluation_split": models.config.get("evaluation_split"),
        **models.status(),
    })


@app.get("/api/dataset-info")
def dataset_info():
    try:
        index = dataset_index()
        return jsonify({key: value for key, value in index.items() if key not in {"profiles", "skill_vocabulary"}})
    except FileNotFoundError as error:
        return api_error(str(error), 404)


@app.post("/api/suggest-profile")
def suggest_similar_profile():
    data = body()
    if data is None or not isinstance(data.get("profile", {}), dict):
        return api_error("Send JSON with a partial profile object.")
    try:
        return jsonify(suggest_profile(data["profile"]))
    except ValueError as error:
        return api_error(str(error))
    except FileNotFoundError as error:
        return api_error(str(error), 404)


@app.get("/api/dashboard")
def dashboard():
    index = dataset_index()
    with get_db() as db:
        students = db.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        jobs = db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
        analyses = db.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        average = db.execute("SELECT AVG(skill_match_pct) FROM analyses WHERE skill_match_pct IS NOT NULL").fetchone()[0]
        suitable = db.execute("SELECT COUNT(*) FROM analyses WHERE predicted_label=1").fetchone()[0]
        unsuitable = db.execute("SELECT COUNT(*) FROM analyses WHERE predicted_label=0").fetchone()[0]
        recent = [serialize_analysis(row) for row in db.execute("SELECT * FROM analyses ORDER BY created_at DESC LIMIT 8")]
        gaps = [dict(row) for row in db.execute(
            "SELECT skill,COUNT(*) AS count FROM skill_gaps GROUP BY skill ORDER BY count DESC LIMIT 10")]
    return jsonify({
        "dataset_records": index["rows"], "dataset_students": index["students"], "dataset_jobs": index["jobs"],
        "managed_students": students, "managed_jobs": jobs, "total_analyses": analyses,
        "average_skill_match_pct": round(average, 2) if average is not None else None,
        "suitable_predictions": suitable, "unsuitable_predictions": unsuitable,
        "recent_analyses": recent, "top_skill_gaps": gaps,
        "role_distribution": index["category_counts"].get("role_category", {}),
        "branch_distribution": index["category_counts"].get("branch", {}),
    })


@app.get("/api/students")
def list_students():
    q, branch = request.args.get("q", "").strip(), request.args.get("branch", "").strip()
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return api_error("limit and offset must be integers.")
    clauses, params = [], []
    if q:
        clauses.append("(student_id LIKE ? OR student_name LIKE ? OR email LIKE ?)")
        params.extend([f"%{q}%"] * 3)
    if branch:
        clauses.append("branch=?")
        params.append(branch)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM students" + where, params).fetchone()[0]
        rows = db.execute(f"SELECT * FROM students{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                          (*params, limit, offset)).fetchall()
    return jsonify({"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset})


@app.post("/api/students")
def create_student():
    data = body()
    if data is None:
        return api_error("Send a JSON object.")
    try:
        student = validate_student(data)
        columns = list(student)
        with get_db() as db:
            cursor = db.execute(f"INSERT INTO students ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                                [student[key] for key in columns])
            row = db.execute("SELECT * FROM students WHERE id=?", (cursor.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201
    except ValueError as error:
        return api_error(str(error))
    except sqlite3.IntegrityError as error:
        return api_error("Student ID or email already exists.", 409, detail=str(error))


@app.get("/api/students/<int:student_pk>")
def get_student(student_pk: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM students WHERE id=?", (student_pk,)).fetchone()
    return jsonify(dict(row)) if row else api_error("Student not found.", 404)


@app.put("/api/students/<int:student_pk>")
def update_student(student_pk: int):
    data = body()
    if data is None:
        return api_error("Send a JSON object.")
    try:
        student = validate_student(data, partial=True)
        if not student:
            return api_error("Provide at least one student field.")
        assigns = ",".join(f"{key}=?" for key in student) + ",updated_at=CURRENT_TIMESTAMP"
        with get_db() as db:
            cursor = db.execute(f"UPDATE students SET {assigns} WHERE id=?", (*student.values(), student_pk))
            if not cursor.rowcount:
                return api_error("Student not found.", 404)
            row = db.execute("SELECT * FROM students WHERE id=?", (student_pk,)).fetchone()
        return jsonify(dict(row))
    except ValueError as error:
        return api_error(str(error))
    except sqlite3.IntegrityError:
        return api_error("Student ID or email already exists.", 409)


@app.delete("/api/students/<int:student_pk>")
def delete_student(student_pk: int):
    with get_db() as db:
        cursor = db.execute("DELETE FROM students WHERE id=?", (student_pk,))
    return (jsonify({"deleted": True, "id": student_pk}), 200) if cursor.rowcount else api_error("Student not found.", 404)


@app.get("/api/jobs")
def list_jobs():
    q, role = request.args.get("q", "").strip(), request.args.get("role_category", "").strip()
    clauses, params = [], []
    if q:
        clauses.append("(job_title LIKE ? OR company_name LIKE ? OR required_skills LIKE ?)")
        params.extend([f"%{q}%"] * 3)
    if role:
        clauses.append("role_category=?")
        params.append(role)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    try:
        limit = min(max(int(request.args.get("limit", 100)), 1), 500)
        offset = max(int(request.args.get("offset", 0)), 0)
    except ValueError:
        return api_error("limit and offset must be integers.")
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) FROM jobs" + where, params).fetchone()[0]
        rows = db.execute(f"SELECT * FROM jobs{where} ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                          (*params, limit, offset)).fetchall()
    return jsonify({"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset})


@app.post("/api/jobs")
def create_job():
    data = body()
    if data is None:
        return api_error("Send a JSON object.")
    try:
        job = validate_job(data)
        if not job.get("required_skills") and job.get("job_description"):
            job["required_skills"] = ", ".join(analyze_job_description(job["job_description"])["extracted_skills"])
        columns = list(job)
        with get_db() as db:
            cursor = db.execute(f"INSERT INTO jobs ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                                [job[key] for key in columns])
            row = db.execute("SELECT * FROM jobs WHERE id=?", (cursor.lastrowid,)).fetchone()
        return jsonify(dict(row)), 201
    except ValueError as error:
        return api_error(str(error))
    except sqlite3.IntegrityError as error:
        return api_error("That external job ID is already stored.", 409, detail=str(error))


@app.get("/api/jobs/<int:job_pk>")
def get_job(job_pk: int):
    with get_db() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job_pk,)).fetchone()
    return jsonify(dict(row)) if row else api_error("Job not found.", 404)


@app.put("/api/jobs/<int:job_pk>")
def update_job(job_pk: int):
    data = body()
    if data is None:
        return api_error("Send a JSON object.")
    try:
        job = validate_job(data, partial=True)
        if not job:
            return api_error("Provide at least one job field.")
        if job.get("job_description") and not job.get("required_skills"):
            job["required_skills"] = ", ".join(analyze_job_description(job["job_description"])["extracted_skills"])
        assigns = ",".join(f"{key}=?" for key in job) + ",updated_at=CURRENT_TIMESTAMP"
        with get_db() as db:
            cursor = db.execute(f"UPDATE jobs SET {assigns} WHERE id=?", (*job.values(), job_pk))
            if not cursor.rowcount:
                return api_error("Job not found.", 404)
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job_pk,)).fetchone()
        return jsonify(dict(row))
    except ValueError as error:
        return api_error(str(error))
    except sqlite3.IntegrityError:
        return api_error("That external job ID is already stored.", 409)


@app.delete("/api/jobs/<int:job_pk>")
def delete_job(job_pk: int):
    with get_db() as db:
        cursor = db.execute("DELETE FROM jobs WHERE id=?", (job_pk,))
    return (jsonify({"deleted": True, "id": job_pk}), 200) if cursor.rowcount else api_error("Job not found.", 404)


@app.post("/api/analyze-job-description")
def analyze_job():
    data = body()
    if data is None:
        return api_error("Send job_description.")
    try:
        return jsonify(analyze_job_description(data.get("job_description")))
    except ValueError as error:
        return api_error(str(error))
    except FileNotFoundError as error:
        return api_error(str(error), 404)


@app.post("/api/match-skills")
def api_match_skills():
    data = body()
    if data is None:
        return api_error("Send student_skills and required_skills.")
    try:
        return jsonify(match_skills(data.get("student_skills"), data.get("required_skills")))
    except ValueError as error:
        return api_error(str(error))


@app.post("/api/analyze-skills")
def legacy_analyze_skills():
    return api_match_skills()


@app.post("/api/analyze-skill-gap")
def api_skill_gap():
    data = body()
    if data is None:
        return api_error("Send student_skills and required_skills.")
    try:
        result = analyze_gap(data.get("student_skills"), data.get("required_skills"))
        result["recommendations"] = recommendations_for(
            result["missing_skills"], data.get("role_category", ""), resources=RESOURCES,
        )
        return jsonify(result)
    except ValueError as error:
        return api_error(str(error))


@app.post("/api/extract-skills")
def legacy_extract_skills():
    data = body()
    if data is None:
        return api_error("Send job_description.")
    try:
        return jsonify(analyze_job_description(data.get("job_description")))
    except ValueError as error:
        return api_error(str(error))


@app.post("/api/analyze")
def analyze_and_save():
    data = body()
    if data is None:
        return api_error("Send a student and job analysis object.")
    student_pk, job_pk = data.get("student_record_id"), data.get("job_record_id")
    try:
        with get_db() as db:
            student = db.execute("SELECT * FROM students WHERE id=?", (student_pk,)).fetchone() if student_pk else None
            job = db.execute("SELECT * FROM jobs WHERE id=?", (job_pk,)).fetchone() if job_pk else None
            if student_pk and student is None:
                return api_error("Selected student was not found.", 404)
            if job_pk and job is None:
                return api_error("Selected job was not found.", 404)
            combined = {**(dict(student) if student else {}), **(dict(job) if job else {}), **data}
            required = combined.get("required_skills", "")
            if not required and combined.get("job_description"):
                required = analyze_job_description(combined["job_description"])["extracted_skills"]
                combined["required_skills"] = required
            gap = analyze_gap(combined.get("student_skills", ""), required, combined.get("optional_skills", ""))
            matching_keys = (
                "student_skills", "required_skills", "matched_skills", "missing_skills",
                "additional_skills", "matched_skill_count", "missing_skill_count", "required_skill_count",
                "skill_match_pct", "matching_method", "matched_optional_skills",
                "missing_optional_skills", "optional_skill_count",
            )
            matching = {key: gap[key] for key in matching_keys}
            prediction_outputs, prediction_error = {}, None
            if data.get("request_prediction"):
                try:
                    prediction_outputs = models.predict(model_row(combined), [data["algorithm"]] if data.get("algorithm") else None)
                except (ValueError, RuntimeError) as error:
                    prediction_error = str(error)
            result = {
                "matching": matching, "skill_gap": gap, "predictions": prediction_outputs,
                "recommendations": recommendations_for_student(
                    db, gap["missing_skills"], combined.get("role_category", ""),
                    student["id"] if student else None, job["id"] if job else None,
                    gap["missing_optional_skills"],
                ),
            }
            if prediction_error:
                result["prediction_error"] = prediction_error
            analysis_id = save_analysis(db, combined, result, student_pk, job_pk)
            report = read_report(db, analysis_id)
        return jsonify({"analysis_id": analysis_id, **result, "prediction_error": prediction_error, "report": report}), 201
    except ValueError as error:
        return api_error(str(error))


@app.post("/api/predict")
def predict():
    data = body()
    if data is None:
        return api_error("Send a JSON object with the student features and job category.")
    try:
        outputs = models.predict(model_row(data), [data["algorithm"]] if data.get("algorithm") else None)
        return jsonify({"predictions": outputs, "notice": "The target is synthetic, not a verified placement outcome."})
    except ValueError as error:
        return api_error(str(error))
    except RuntimeError as error:
        return api_error(str(error), 503, model_status=models.status())


@app.post("/api/compare-models")
def compare_models():
    data = body() or {}
    requested = data.get("algorithms")
    metrics = normalized_evaluation_metrics()
    if requested is not None:
        if not isinstance(requested, list) or not all(isinstance(name, str) for name in requested):
            return api_error("algorithms must be a list of model names.")
        metrics = [item for item in metrics if item.get("model") in requested]
    top_test_f1 = max(metrics, key=lambda item: item.get("suitable_f1_pct") or 0)["model"] if metrics else None
    selected_model = models.config.get("selected_model")
    return jsonify({
        "historical": not bool(models.config.get("training_rows")),
        "source": "Notebook evaluation output; metrics are not recomputed at runtime.",
        "selected_model": selected_model,
        "cross_validation_metrics": normalized_cross_validation_metrics(),
        "metrics": metrics, "best_model": selected_model, "top_test_f1_model": top_test_f1,
        "runtime_models": models.status(),
    })


@app.get("/api/model-performance")
def model_performance():
    metrics = normalized_evaluation_metrics()
    top_test_f1 = max(metrics, key=lambda item: item.get("suitable_f1_pct") or 0)["model"] if metrics else None
    importances = {}
    for name, estimator in models.models.items():
        if hasattr(estimator, "feature_importances_"):
            importances[name] = sorted(
                [{"feature": feature, "importance": float(score)}
                 for feature, score in zip(models.features, estimator.feature_importances_)],
                key=lambda row: row["importance"], reverse=True,
            )[:15]
    return jsonify({
        "historical": not bool(models.config.get("training_rows")), "evaluation_metrics": metrics,
        "confusion_matrices": models.config.get("confusion_matrices", {}),
        "classes": ["Unsuitable (0)", "Suitable (1)"],
        "evaluation_rows": models.config.get("evaluation_rows", models.config.get("testing_rows")),
        "evaluation_split": models.config.get("evaluation_split"),
        "best_model_by_suitable_f1": models.config.get("selected_model"),
        "top_test_f1_model": top_test_f1,
        "selected_model": models.config.get("selected_model"),
        "cross_validation_metrics": normalized_cross_validation_metrics(),
        "unsupervised": models.config.get("historical_unsupervised"),
        "feature_importance": importances,
        "feature_importance_note": None if importances else "Tree feature-importance artifacts are not installed.",
        "runtime_models": models.status(),
    })


@app.get("/api/analysis-history")
def analysis_history():
    q = request.args.get("q", "").strip()
    student_id = request.args.get("student_id", "").strip()
    role = request.args.get("role_category", "").strip()
    clauses, params = [], []
    if q:
        clauses.append("(student_id LIKE ? OR student_name LIKE ? OR job_title LIKE ? OR company_name LIKE ?)")
        params.extend([f"%{q}%"] * 4)
    if student_id:
        clauses.append("student_id=?")
        params.append(student_id)
    if role:
        clauses.append("role_category=?")
        params.append(role)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with get_db() as db:
        rows = db.execute(f"SELECT * FROM analyses{where} ORDER BY created_at DESC LIMIT 500", params).fetchall()
    return jsonify({"items": [serialize_analysis(row) for row in rows], "total": len(rows)})


@app.delete("/api/analysis-history/<int:analysis_id>")
def delete_analysis(analysis_id: int):
    with get_db() as db:
        cursor = db.execute("DELETE FROM analyses WHERE id=?", (analysis_id,))
    return (jsonify({"deleted": True, "id": analysis_id}), 200) if cursor.rowcount else api_error("Analysis not found.", 404)


@app.get("/api/learning-recommendations")
def learning_recommendations():
    completed = request.args.get("completed")
    clauses, params = [], []
    student_record_id = request.args.get("student_record_id")
    job_record_id = request.args.get("job_record_id")
    role_category = request.args.get("role_category", "").strip()
    with get_db() as db:
        if student_record_id:
            try:
                student_pk = int(student_record_id)
            except ValueError:
                return api_error("student_record_id must be an integer.")
            student = db.execute("SELECT student_id FROM students WHERE id=?", (student_pk,)).fetchone()
            if not student:
                return api_error("Student not found.", 404)
            clauses.append("(a.student_record_id=? OR a.student_id=?)")
            params.extend((student_pk, student["student_id"]))
        if job_record_id:
            try:
                job_pk = int(job_record_id)
            except ValueError:
                return api_error("job_record_id must be an integer.")
            job = db.execute(
                "SELECT external_job_id,job_title,company_name FROM jobs WHERE id=?", (job_pk,),
            ).fetchone()
            if not job:
                return api_error("Job not found.", 404)
            if job["external_job_id"]:
                clauses.append(
                    "(a.job_record_id=? OR (a.job_record_id IS NULL AND a.job_id=? "
                    "AND a.job_title=? AND a.company_name=?))"
                )
                params.extend((job_pk, job["external_job_id"], job["job_title"], job["company_name"]))
            else:
                clauses.append(
                    "(a.job_record_id=? OR (a.job_record_id IS NULL "
                    "AND a.job_title=? AND a.company_name=?))"
                )
                params.extend((job_pk, job["job_title"], job["company_name"]))
        if role_category:
            clauses.append("a.role_category=?")
            params.append(role_category)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        sql = """SELECT lr.*,a.student_record_id,a.job_record_id,a.student_id,a.student_name,
                        a.job_id,a.job_title,a.company_name,a.role_category
                 FROM learning_recommendations lr JOIN analyses a ON a.id=lr.analysis_id""" + where + """
                 ORDER BY lr.created_at DESC,lr.id DESC LIMIT 5000"""
        rows = [dict(row) for row in db.execute(sql, params)]
        groups = {}
        for item in rows:
            student_identity = (
                f"record:{item['student_record_id']}" if item["student_record_id"] is not None
                else f"id:{item['student_id']}"
            )
            if item["job_record_id"] is not None:
                job_identity = f"record:{item['job_record_id']}"
            elif item["job_id"]:
                job_identity = f"external:{item['job_id']}|{item['job_title']}|{item['company_name']}"
            else:
                job_identity = f"title:{item['job_title']}|{item['company_name']}"
            canonical_skill = normalize_skill(item["skill"])
            key = (student_identity, job_identity, canonical_skill.casefold())
            existing = groups.get(key)
            if existing is None:
                groups[key] = {**item, "skill": canonical_skill, "duplicate_count": 1}
            else:
                existing["duplicate_count"] += 1
                existing["is_completed"] = max(existing["is_completed"], item["is_completed"])
        items = list(groups.values())
        if completed in {"true", "false"}:
            target = 1 if completed == "true" else 0
            items = [item for item in items if bool(item["is_completed"]) == bool(target)]
        demand_cache = {}
        filtered_items = []
        recommendations_suppressed = 0
        for item in items:
            student_pk = item["student_record_id"]
            if student_pk is None and item["student_id"]:
                student_row = db.execute(
                    "SELECT id FROM students WHERE student_id=?", (item["student_id"],),
                ).fetchone()
                student_pk = student_row["id"] if student_row else None
            job_pk = item["job_record_id"]
            if not item["is_completed"]:
                active_suggestion = recommendations_for_student(
                    db,
                    [] if item["requirement_type"] == "optional" else [item["skill"]],
                    item["role_category"] or "", student_pk, job_pk,
                    [item["skill"]] if item["requirement_type"] == "optional" else [],
                )
                if not active_suggestion:
                    recommendations_suppressed += 1
                    continue
            if student_pk is not None:
                demand_key = (student_pk, job_pk)
                if demand_key not in demand_cache:
                    demand_cache[demand_key] = skill_job_counts_for_student(
                        db, student_pk, [job_pk] if job_pk is not None else None,
                    )
                job_counts = demand_cache[demand_key]
            else:
                job_counts = {}
            suggestion = recommendations_for(
                [] if item["requirement_type"] == "optional" else [item["skill"]],
                item["role_category"] or "",
                optional_skills=[item["skill"]] if item["requirement_type"] == "optional" else [],
                resources=_catalog_resources(db), skill_job_counts=job_counts,
            )
            if suggestion:
                item["priority"] = suggestion[0]["priority"]
                item["priority_rank"] = suggestion[0]["priority_rank"]
                item["priority_basis"] = suggestion[0]["priority_basis"]
                item["resource"] = suggestion[0]["resource"]
            item["recommendation_key"] = "|".join((
                str(item["student_record_id"] or item["student_id"]),
                str(item["job_record_id"] or item["job_id"] or item["job_title"]),
                item["skill"].casefold(),
            ))
            filtered_items.append(item)
        items = filtered_items
        items.sort(key=lambda item: (-item.get("priority_rank", 1), item["skill"].casefold(), item["created_at"]))
        total_groups = len(groups)
        items = items[:500]
    return jsonify({
        "items": items, "total": len(items),
        "duplicate_rows_suppressed": max(0, len(rows) - total_groups),
        "recommendations_suppressed": recommendations_suppressed,
    })


@app.patch("/api/learning-recommendations/<int:recommendation_id>")
def update_learning_recommendation(recommendation_id: int):
    data = body()
    if data is None or not isinstance(data.get("is_completed"), bool):
        return api_error("is_completed must be true or false.")
    completed_at = datetime.now(timezone.utc).isoformat() if data["is_completed"] else None
    with get_db() as db:
        row = db.execute(
            """SELECT lr.id,lr.skill,a.student_record_id,a.job_record_id,a.student_id,
                      a.job_id,a.job_title,a.company_name
               FROM learning_recommendations lr JOIN analyses a ON a.id=lr.analysis_id
               WHERE lr.id=?""",
            (recommendation_id,),
        ).fetchone()
        if not row:
            return api_error("Learning recommendation not found.", 404)
        target_student = (
            f"record:{row['student_record_id']}" if row["student_record_id"] is not None
            else f"id:{row['student_id']}"
        )
        target_job = (
            f"record:{row['job_record_id']}" if row["job_record_id"] is not None
            else f"external:{row['job_id']}|{row['job_title']}|{row['company_name']}"
            if row["job_id"] else f"title:{row['job_title']}|{row['company_name']}"
        )
        candidates = db.execute(
            """SELECT lr.id,lr.skill,a.student_record_id,a.job_record_id,a.student_id,
                      a.job_id,a.job_title,a.company_name
               FROM learning_recommendations lr JOIN analyses a ON a.id=lr.analysis_id
               WHERE (a.student_record_id=? OR a.student_id=?)
                 AND (a.job_record_id=? OR a.job_id=? OR
                      (a.job_title=? AND a.company_name=?))""",
            (
                row["student_record_id"], row["student_id"], row["job_record_id"],
                row["job_id"] or "", row["job_title"], row["company_name"],
            ),
        ).fetchall()
        grouped_ids = []
        target_skill = normalize_skill(row["skill"]).casefold()
        for candidate in candidates:
            candidate_student = (
                f"record:{candidate['student_record_id']}" if candidate["student_record_id"] is not None
                else f"id:{candidate['student_id']}"
            )
            candidate_job = (
                f"record:{candidate['job_record_id']}" if candidate["job_record_id"] is not None
                else f"external:{candidate['job_id']}|{candidate['job_title']}|{candidate['company_name']}"
                if candidate["job_id"] else f"title:{candidate['job_title']}|{candidate['company_name']}"
            )
            if (
                candidate_student == target_student and candidate_job == target_job
                and normalize_skill(candidate["skill"]).casefold() == target_skill
            ):
                grouped_ids.append(candidate["id"])
        if not grouped_ids:
            grouped_ids = [row["id"]]
        placeholders = ",".join("?" for _ in grouped_ids)
        db.execute(
            f"UPDATE learning_recommendations SET is_completed=?,completed_at=? WHERE id IN ({placeholders})",
            [int(data["is_completed"]), completed_at, *grouped_ids],
        )
    return jsonify({
        "id": recommendation_id, "is_completed": data["is_completed"],
        "duplicate_count": len(grouped_ids),
    })


@app.post("/api/generate-report")
def generate_report_route():
    data = body()
    if data is None or not isinstance(data.get("analysis_id"), int):
        return api_error("analysis_id is required for a saved analysis report.")
    with get_db() as db:
        report = read_report(db, data["analysis_id"])
    if report is None:
        return api_error("Analysis not found.", 404)
    response = make_response(generate_pdf(report))
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename=placement-analysis-{data['analysis_id']}.pdf"
    return response


@app.get("/api/export-analysis.csv")
def export_analysis_csv():
    columns = [
        "id", "student_name", "student_id", "email", "branch", "cgpa", "coding_skill_score",
        "aptitude_score", "communication_skill_score", "logical_reasoning_score", "mock_interview_score",
        "backlogs", "github_repos", "internships_count", "projects_count", "student_skills", "job_id",
        "job_title", "company_name", "role_category", "location", "work_mode", "required_skills",
        "is_fresher_friendly", "experience_min_yrs", "experience_max_yrs", "job_url", "matched_skills",
        "missing_skills", "additional_skills", "skill_match_pct", "synthetic_suitability_label",
        "selected_model", "class_probabilities", "model_notice", "created_at",
    ]
    with get_db() as db:
        records = [serialize_analysis(row) for row in db.execute(
            "SELECT * FROM analyses ORDER BY created_at DESC LIMIT 500"
        )]
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for record in records:
        snapshot = record.get("input_snapshot") or {}
        row = {key: record.get(key, snapshot.get(key, "")) for key in columns}
        label = record.get("predicted_label")
        row["synthetic_suitability_label"] = (
            "" if label is None else "Synthetic suitable (1)" if label == 1 else "Synthetic unsuitable (0)"
        )
        for key in ("matched_skills", "missing_skills", "additional_skills", "class_probabilities"):
            row[key] = json.dumps(row.get(key) or ([] if key.endswith("skills") else {}), ensure_ascii=False)
        writer.writerow(row)
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=placement-analysis-history.csv"
    return response


if __name__ == "__main__":
    app.run(debug=True)
