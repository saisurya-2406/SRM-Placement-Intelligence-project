"""SQLite schema and connection helpers."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

try:
    from .config import DATABASE_PATH
except ImportError:
    from config import DATABASE_PATH


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT NOT NULL UNIQUE,
    student_name TEXT NOT NULL,
    email TEXT UNIQUE,
    branch TEXT NOT NULL,
    cgpa REAL NOT NULL,
    coding_skill_score REAL NOT NULL,
    aptitude_score REAL NOT NULL,
    communication_skill_score REAL NOT NULL,
    logical_reasoning_score REAL NOT NULL,
    mock_interview_score REAL NOT NULL,
    backlogs INTEGER NOT NULL DEFAULT 0,
    github_repos INTEGER NOT NULL DEFAULT 0,
    internships_count INTEGER NOT NULL DEFAULT 0,
    projects_count INTEGER NOT NULL DEFAULT 0,
    student_skills TEXT NOT NULL DEFAULT '',
    degree TEXT NOT NULL DEFAULT '',
    specialization TEXT NOT NULL DEFAULT '',
    graduation_year INTEGER,
    experience_years REAL NOT NULL DEFAULT 0,
    areas_of_interest TEXT NOT NULL DEFAULT '',
    preferred_job_roles TEXT NOT NULL DEFAULT '',
    certifications TEXT NOT NULL DEFAULT '',
    projects TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_job_id TEXT UNIQUE,
    company_name TEXT NOT NULL,
    job_title TEXT NOT NULL,
    job_description TEXT NOT NULL DEFAULT '',
    required_skills TEXT NOT NULL DEFAULT '',
    optional_skills TEXT NOT NULL DEFAULT '',
    experience_min_yrs REAL,
    experience_max_yrs REAL,
    is_fresher_friendly INTEGER,
    location TEXT NOT NULL DEFAULT '',
    work_mode TEXT NOT NULL DEFAULT '',
    role_category TEXT NOT NULL DEFAULT '',
    job_url TEXT NOT NULL DEFAULT '',
    min_cgpa REAL,
    eligible_branches TEXT NOT NULL DEFAULT '',
    required_certifications TEXT NOT NULL DEFAULT '',
    required_degree TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_record_id INTEGER REFERENCES students(id) ON DELETE SET NULL,
    job_record_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    student_id TEXT NOT NULL DEFAULT '',
    student_name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    job_id TEXT NOT NULL DEFAULT '',
    job_title TEXT NOT NULL DEFAULT '',
    role_category TEXT NOT NULL DEFAULT '',
    company_name TEXT NOT NULL DEFAULT '',
    skill_match_pct REAL,
    matched_skills_json TEXT NOT NULL DEFAULT '[]',
    missing_skills_json TEXT NOT NULL DEFAULT '[]',
    additional_skills_json TEXT NOT NULL DEFAULT '[]',
    predicted_label INTEGER,
    selected_model TEXT NOT NULL DEFAULT '',
    class_probabilities_json TEXT NOT NULL DEFAULT '{}',
    input_snapshot_json TEXT NOT NULL DEFAULT '{}',
    model_notice TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS skill_gaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'Other',
    importance TEXT NOT NULL DEFAULT 'Unranked',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS learning_recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    learning_activity TEXT NOT NULL,
    project_idea TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Unranked',
    is_completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS career_roadmaps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_pk INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    job_pk INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS roadmap_activities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roadmap_id INTEGER NOT NULL REFERENCES career_roadmaps(id) ON DELETE CASCADE,
    skill TEXT NOT NULL DEFAULT '',
    stage INTEGER NOT NULL,
    title TEXT NOT NULL,
    objective TEXT NOT NULL DEFAULT '',
    topics_json TEXT NOT NULL DEFAULT '[]',
    duration_label TEXT NOT NULL DEFAULT 'Self-paced',
    difficulty TEXT NOT NULL DEFAULT 'Beginner',
    resource_id TEXT NOT NULL DEFAULT '',
    project_idea TEXT NOT NULL DEFAULT '',
    is_completed INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS saved_learning_resources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_pk INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    resource_id TEXT NOT NULL,
    roadmap_id INTEGER REFERENCES career_roadmaps(id) ON DELETE SET NULL,
    saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(student_pk, resource_id)
);
CREATE TABLE IF NOT EXISTS learning_resource_catalog (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    skill TEXT NOT NULL,
    domain TEXT NOT NULL,
    provider TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    relevant_roles_json TEXT NOT NULL DEFAULT '[]',
    verification_status TEXT NOT NULL DEFAULT 'unverified',
    cost TEXT NOT NULL DEFAULT '',
    duration TEXT NOT NULL DEFAULT '',
    is_builtin INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS mock_interview_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_pk INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    job_pk INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    answers_json TEXT NOT NULL DEFAULT '[]',
    score_pct REAL,
    feedback_json TEXT NOT NULL DEFAULT '[]',
    suggestions_json TEXT NOT NULL DEFAULT '[]',
    scoring_method TEXT NOT NULL DEFAULT 'transparent_rule_based',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    submitted_at TEXT
);
CREATE TABLE IF NOT EXISTS skill_proficiency_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_pk INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    previous_proficiency INTEGER,
    current_proficiency INTEGER NOT NULL,
    assessment_date TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    learning_progress_pct REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_students_branch ON students(branch);
CREATE INDEX IF NOT EXISTS idx_jobs_role ON jobs(role_category);
CREATE INDEX IF NOT EXISTS idx_analyses_student ON analyses(student_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_gaps_analysis ON skill_gaps(analysis_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_analysis ON learning_recommendations(analysis_id);
CREATE INDEX IF NOT EXISTS idx_interview_attempts_student ON mock_interview_attempts(student_pk, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_skill_history_student ON skill_proficiency_history(student_pk, assessment_date, id);
CREATE INDEX IF NOT EXISTS idx_resource_catalog_skill ON learning_resource_catalog(skill COLLATE NOCASE);
"""


def init_db() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    try:
        connection.executescript(SCHEMA)
        migrations_by_table = {
            "students": {
                "degree": "TEXT NOT NULL DEFAULT ''", "specialization": "TEXT NOT NULL DEFAULT ''",
                "graduation_year": "INTEGER", "experience_years": "REAL NOT NULL DEFAULT 0",
                "areas_of_interest": "TEXT NOT NULL DEFAULT ''", "preferred_job_roles": "TEXT NOT NULL DEFAULT ''",
                "certifications": "TEXT NOT NULL DEFAULT ''", "projects": "TEXT NOT NULL DEFAULT ''",
            },
            "jobs": {
                "optional_skills": "TEXT NOT NULL DEFAULT ''",
                "min_cgpa": "REAL", "eligible_branches": "TEXT NOT NULL DEFAULT ''",
                "required_certifications": "TEXT NOT NULL DEFAULT ''",
                "required_degree": "TEXT NOT NULL DEFAULT ''",
            },
        }
        for table, migrations in migrations_by_table.items():
            columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
            for column, declaration in migrations.items():
                if column not in columns:
                    connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
        saved_columns = {row[1] for row in connection.execute("PRAGMA table_info(saved_learning_resources)")}
        if "roadmap_id" not in saved_columns:
            connection.execute("ALTER TABLE saved_learning_resources ADD COLUMN roadmap_id INTEGER REFERENCES career_roadmaps(id) ON DELETE SET NULL")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(analyses)")}
        migrations = {
            "email": "TEXT NOT NULL DEFAULT ''",
            "job_id": "TEXT NOT NULL DEFAULT ''",
            "input_snapshot_json": "TEXT NOT NULL DEFAULT '{}'",
        }
        for column, declaration in migrations.items():
            if column not in columns:
                connection.execute(f"ALTER TABLE analyses ADD COLUMN {column} {declaration}")
        recommendation_columns = {row[1] for row in connection.execute("PRAGMA table_info(learning_recommendations)")}
        recommendation_migrations = {
            "category": "TEXT NOT NULL DEFAULT 'Other / uncategorized'",
            "why_it_matters": "TEXT NOT NULL DEFAULT ''",
            "priority_basis": "TEXT NOT NULL DEFAULT 'Unranked'",
            "requirement_type": "TEXT NOT NULL DEFAULT 'mandatory'",
        }
        for column, declaration in recommendation_migrations.items():
            if column not in recommendation_columns:
                connection.execute(f"ALTER TABLE learning_recommendations ADD COLUMN {column} {declaration}")
        connection.commit()
    finally:
        connection.close()


@contextmanager
def get_db() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
