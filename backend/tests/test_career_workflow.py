"""Isolated API integration coverage for career intelligence and legacy inference."""
import os
import json
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

# Configure a throwaway database before importing the Flask app/config module.
_test_db_dir = tempfile.TemporaryDirectory(prefix="srm-placement-tests-")
os.environ["PLACEMENT_DB_PATH"] = str(Path(_test_db_dir.name) / "test.sqlite3")

from backend.app import app, models  # noqa: E402
from backend.career_intelligence import RESOURCES  # noqa: E402
from backend.config import DATABASE_PATH, DATABASE_PATH_SOURCE  # noqa: E402


class CareerWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.suffix = uuid.uuid4().hex[:10]
        response = self.client.post("/api/students", json={
            "student_id": f"TEST-{self.suffix}", "student_name": "Test Student",
            "email": f"{self.suffix}@example.test", "branch": "CSE", "degree": "B.Tech",
            "specialization": "Data Science", "graduation_year": 2027, "experience_years": 0,
            "areas_of_interest": "Analytics", "preferred_job_roles": "Data Analyst",
            "projects": "CSV analysis project", "certifications": "Data fundamentals",
            "cgpa": 8.2, "coding_skill_score": 70, "aptitude_score": 72,
            "communication_skill_score": 74, "logical_reasoning_score": 71,
            "mock_interview_score": 68, "backlogs": 0, "github_repos": 2,
            "internships_count": 0, "projects_count": 1, "student_skills": "Python, SQL",
        })
        self.assertEqual(response.status_code, 201, response.json)
        self.student_id = response.json["id"]
        response = self.client.post("/api/jobs", json={
            "company_name": f"Test Co {self.suffix}", "job_title": "Data Analyst",
            "role_category": "Data Analyst", "work_mode":"Hybrid", "required_skills": "Python, SQL, Power BI",
            "required_degree": "B.Tech", "min_cgpa": 7.0, "eligible_branches": "CSE, IT",
            "experience_min_yrs": None, "is_fresher_friendly": True,
            "required_certifications": "",
        })
        self.assertEqual(response.status_code, 201, response.json)
        self.job_id = response.json["id"]

    def test_health_reports_the_selected_isolated_database_path(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["database_path"], str(DATABASE_PATH))
        self.assertEqual(response.json["database_path_source"], DATABASE_PATH_SOURCE)
        self.assertEqual(DATABASE_PATH_SOURCE, "PLACEMENT_DB_PATH")

    def test_personalized_persisted_learning_workflow(self):
        match = self.client.get(f"/api/job-matches?student_id={self.student_id}").json["items"][0]
        self.assertEqual(match["eligibility_status"], "eligible")
        self.assertIsInstance(match["required_skills"], str)
        self.assertEqual(match["normalized_required_skills"], ["Power BI", "Python", "SQL"])
        self.assertEqual(match["missing_skills"], ["Power BI"])
        self.assertEqual(match["skill_match_pct"], 66.67)
        self.assertIn("exact phrase overlap", match["method"])

        response = self.client.post("/api/roadmaps", json={"student_id": self.student_id, "job_id": self.job_id})
        self.assertEqual(response.status_code, 201, response.json)
        roadmap = response.json
        self.assertTrue(any(a["skill"] == "Power BI" for a in roadmap["activities"]))
        self.assertTrue(any(a["stage"] == 6 for a in roadmap["activities"]))
        cert = next(a for a in roadmap["activities"] if a["stage"] == 4)
        self.assertEqual(cert["resource_id"], "pl300-cert")

        activity = roadmap["activities"][0]
        self.assertEqual(self.client.patch(f"/api/roadmap-activities/{activity['id']}", json={"is_completed": True}).status_code, 200)
        reloaded = self.client.get(f"/api/roadmaps/{roadmap['id']}").json
        self.assertEqual(next(a for a in reloaded["activities"] if a["id"] == activity["id"])["is_completed"], 1)
        self.assertEqual(self.client.post(f"/api/roadmaps/{roadmap['id']}/recalculate").status_code, 200)

        prep = self.client.get(f"/api/interview-prep?student_id={self.student_id}&job_id={self.job_id}").json
        self.assertIn("not actual company interview questions", prep["method"])
        self.assertGreater(len(prep["sections"]), 0)
        analytics = self.client.get(f"/api/career-analytics/{self.student_id}").json
        self.assertEqual(analytics["activities_completed"], 1)
        self.assertEqual(analytics["skill_count"], 2)
        self.assertEqual(analytics["profile_completeness_pct"], 100)

        resources = self.client.get("/api/resources?skill=Power%20BI").json["items"]
        self.assertTrue(any(r["id"] == "pl300-cert" for r in resources))
        self.assertEqual(self.client.post("/api/resources/pl300-cert/save", json={"student_id": self.student_id,"roadmap_id":roadmap["id"]}).status_code, 200)
        self.assertTrue(self.client.get(f"/api/saved-resources?student_id={self.student_id}").json["items"])
        self.assertEqual(self.client.get(f"/api/roadmaps/{roadmap['id']}").json["saved_resources"][0]["id"], "pl300-cert")

    def test_skill_overlap_duplicates_case_whitespace_and_aliases(self):
        result = self.client.post("/api/match-skills", json={
            "student_skills":" python ; SQL, Excel, excel ",
            "required_skills":" Python , sql, Power BI, Excel, Statistics ",
        })
        self.assertEqual(result.status_code, 200, result.json)
        self.assertEqual(result.json["matched_skill_count"], 3)
        self.assertEqual(result.json["missing_skills"], ["Power BI", "Statistics"])
        self.assertEqual(result.json["skill_match_pct"], 60.0)
        alias = self.client.post("/api/match-skills", json={"student_skills":"PowerBI", "required_skills":"Power BI"})
        self.assertEqual(alias.status_code, 200, alias.json)
        self.assertEqual(alias.json["matched_skill_count"], 1)

    def test_skill_aliases_deduplication_empty_lists_and_unrelated_terms(self):
        response = self.client.post("/api/match-skills", json={
            "student_skills": "PowerBI; MS Excel, Structured Query Language, ML, PostgreSQL, machine   learning, Excel",
            "required_skills": "Power BI, Excel, SQL, Machine Learning, PostgreSQL",
        })
        self.assertEqual(response.status_code, 200, response.json)
        self.assertEqual(response.json["student_skills"], ["Excel", "Machine Learning", "PostgreSQL", "Power BI", "SQL"])
        self.assertEqual(response.json["matched_skill_count"], 5)
        self.assertEqual(response.json["required_skill_count"], 5)
        self.assertEqual(response.json["skill_match_pct"], 100.0)

        unrelated = self.client.post("/api/match-skills", json={
            "student_skills": "ML Engineer", "required_skills": "Machine Learning",
        })
        self.assertEqual(unrelated.json["matched_skill_count"], 0)
        empty = self.client.post("/api/match-skills", json={"student_skills": [], "required_skills": []})
        self.assertEqual(empty.json["matched_skills"], [])
        self.assertIsNone(empty.json["skill_match_pct"])

    def test_role_relevant_resource_catalog(self):
        result = self.client.get("/api/resources?role=Data%20Analyst&missing_skills=PowerBI%2CSQL")
        self.assertEqual(result.status_code, 200, result.json)
        items = result.json["items"]
        self.assertTrue(any(item["id"] == "powerbi-path" and item["recommended"] for item in items))
        self.assertEqual(
            [item["id"] for item in items if item["recommended"] and item["skill"] == "Power BI"],
            ["powerbi-path"],
        )
        self.assertTrue(all("Data Analyst" in item["relevant_roles"] for item in items))
        tableau = self.client.get("/api/resources?role=Data%20Analyst&missing_skills=Tableau").json["items"]
        self.assertTrue(any(item["id"] == "tableau-training" and item["recommended"] for item in tableau))
        for item in items:
            for key in ("title", "skill", "provider", "type", "url", "description", "relevant_roles"):
                self.assertTrue(item.get(key), f"{item['id']} is missing {key}")
        alias = self.client.get("/api/resources?skill=PowerBI").json["items"]
        self.assertTrue(any(item["skill"] == "Power BI" for item in alias))
        self.assertEqual(len({item["url"] for item in RESOURCES}), len(RESOURCES))

        self.assertEqual(self.client.post("/api/skill-proficiency", json={
            "student_id": self.student_id, "skill": "PowerBI", "current_proficiency": 5,
            "learning_progress_pct": 100,
        }).status_code, 201)
        mastered = self.client.get(
            f"/api/resources?role=Data%20Analyst&missing_skills=PowerBI&student_id={self.student_id}",
        ).json["items"]
        self.assertFalse(any(item["recommended"] for item in mastered if item["skill"] == "Power BI"))

    def test_role_independent_recommendations_custom_catalog_and_optional_persistence(self):
        resource = self.client.post("/api/resources", json={
            "title": "Cloud Security Foundations", "skill": "Cloud Security",
            "domain": "Cloud Security", "provider": "Example Learning Provider",
            "resource_type": "Documentation", "difficulty": "Beginner",
            "url": f"https://example.test/cloud-security/{self.suffix}",
            "description": "A test catalogue entry used to verify custom-skill recommendations.",
            "relevant_roles": "Custom Risk Auditor", "url_verified": True,
        })
        self.assertEqual(resource.status_code, 201, resource.json)
        self.assertEqual(resource.json["verification_status"], "admin_confirmed")
        self.assertEqual(resource.json["skill"], "Cloud Security")
        self.assertEqual(self.client.post("/api/resources", json={
            **resource.json, "url_verified": True,
        }).status_code, 409)

        domain_jobs = []
        for company, title, role, required in [
            ("Web Co", "Software Developer", "Software Developer", "JavaScript"),
            ("Cloud Co", "Cloud Engineer", "Cloud Engineer", "Kubernetes"),
            ("Security Co", "Security Analyst", "Cybersecurity Analyst", "Cybersecurity"),
            ("Business Co", "Business Analyst", "Business Analyst", "Business Analysis"),
            ("Custom Co", "Risk Auditor", "Custom Risk Auditor", "Cloud Security"),
        ]:
            response = self.client.post("/api/jobs", json={
                "company_name": f"{company} {self.suffix}", "job_title": title,
                "role_category": role, "required_skills": required,
                "optional_skills": "Tableau, Custom Compliance Framework" if role == "Custom Risk Auditor" else "",
            })
            self.assertEqual(response.status_code, 201, response.json)
            domain_jobs.append(response.json)
        selected_ids = [self.job_id, *(item["id"] for item in domain_jobs)]
        result = self.client.get(
            f"/api/resources?student_id={self.student_id}&job_ids={','.join(map(str, selected_ids))}",
        )
        self.assertEqual(result.status_code, 200, result.json)
        analysis = result.json["job_comparison"]
        self.assertEqual(len(analysis["jobs"]), 6)
        recommended_skills = {
            item["skill"] for item in result.json["recommendations"] if item["resource"]
        }
        self.assertTrue({
            "Power BI", "JavaScript", "Kubernetes", "Cybersecurity",
            "Business Analysis", "Cloud Security", "Tableau",
        }.issubset(recommended_skills))
        custom = next(
            item for item in result.json["recommendations"]
            if item["skill"] == "Cloud Security"
        )
        optional = next(
            item for item in result.json["recommendations"]
            if item["skill"] == "Tableau"
        )
        self.assertEqual(custom["resource"]["id"], resource.json["id"])
        self.assertEqual(custom["requirement_type"], "mandatory")
        self.assertEqual(optional["requirement_type"], "optional")
        self.assertIn("Custom Compliance Framework", result.json["unmatched_skills"])
        self.assertEqual(len({item["resource"]["id"] for item in result.json["recommendations"] if item["resource"]}),
                         sum(item["resource"] is not None for item in result.json["recommendations"]))

        saved = self.client.post("/api/analyze", json={
            "student_record_id": self.student_id,
            "job_record_id": domain_jobs[-1]["id"],
        })
        self.assertEqual(saved.status_code, 201, saved.json)
        saved_recommendations = self.client.get(
            f"/api/learning-recommendations?student_record_id={self.student_id}"
            f"&job_record_id={domain_jobs[-1]['id']}",
        ).json["items"]
        self.assertEqual(
            {item["requirement_type"] for item in saved_recommendations},
            {"mandatory", "optional"},
        )
        self.assertTrue(any(
            item["resource"]["id"] == resource.json["id"]
            for item in saved_recommendations
        ))

        second = self.client.post("/api/students", json={
            "student_id": f"ROLE-READY-{self.suffix}", "student_name": "Role Ready Student",
            "branch": "CSE", "cgpa": 8, "coding_skill_score": 70, "aptitude_score": 70,
            "communication_skill_score": 70, "logical_reasoning_score": 70,
            "mock_interview_score": 70, "backlogs": 0,
            "github_repos": 1, "internships_count": 0, "projects_count": 1,
            "student_skills": "Python, SQL, Power BI, JavaScript, Kubernetes, Cybersecurity, Business Analysis, Cloud Security, Tableau, Custom Compliance Framework",
        })
        self.assertEqual(second.status_code, 201, second.json)
        isolated = self.client.get(
            f"/api/resources?student_id={second.json['id']}&job_ids={domain_jobs[-1]['id']}",
        ).json
        self.assertFalse(any(item["recommended"] for item in isolated["items"]))
        self.assertEqual(isolated["recommendations"], [])

    def test_recommendations_deduplicate_by_student_job_and_skill(self):
        payload = {"student_record_id": self.student_id, "job_record_id": self.job_id}
        first = self.client.post("/api/analyze", json=payload)
        second = self.client.post("/api/analyze", json=payload)
        self.assertEqual(first.status_code, 201, first.json)
        self.assertEqual(second.status_code, 201, second.json)

        other = self.client.post("/api/students", json={
            "student_id": f"OTHER-{self.suffix}", "student_name": "Other Student",
            "branch": "CSE", "cgpa": 8, "coding_skill_score": 60, "aptitude_score": 60,
            "communication_skill_score": 60, "logical_reasoning_score": 60,
            "mock_interview_score": 60, "backlogs": 0, "github_repos": 1,
            "internships_count": 0, "projects_count": 1, "student_skills": "Python, SQL",
        })
        self.assertEqual(other.status_code, 201, other.json)
        other_analysis = self.client.post("/api/analyze", json={
            "student_record_id": other.json["id"], "job_record_id": self.job_id,
        })
        self.assertEqual(other_analysis.status_code, 201, other_analysis.json)

        first_items = self.client.get(
            f"/api/learning-recommendations?student_record_id={self.student_id}&job_record_id={self.job_id}",
        ).json
        self.assertEqual(len(first_items["items"]), 1)
        self.assertEqual(first_items["duplicate_rows_suppressed"], 1)
        self.assertEqual(first_items["items"][0]["duplicate_count"], 2)
        self.assertEqual(first_items["items"][0]["resource"]["id"], "powerbi-path")
        self.assertEqual(first_items["items"][0]["priority"], "Required")

        second_items = self.client.get(
            f"/api/learning-recommendations?student_record_id={other.json['id']}&job_record_id={self.job_id}",
        ).json
        self.assertEqual(len(second_items["items"]), 1)
        self.assertEqual(second_items["items"][0]["duplicate_count"], 1)

        recommendation_id = first_items["items"][0]["id"]
        updated = self.client.patch(
            f"/api/learning-recommendations/{recommendation_id}", json={"is_completed": True},
        )
        self.assertEqual(updated.status_code, 200, updated.json)
        self.assertEqual(updated.json["duplicate_count"], 2)
        self.assertEqual(self.client.get(
            f"/api/learning-recommendations?student_record_id={self.student_id}&job_record_id={self.job_id}&completed=true",
        ).json["items"][0]["duplicate_count"], 2)
        self.assertEqual(self.client.get(
            f"/api/learning-recommendations?student_record_id={other.json['id']}&job_record_id={self.job_id}&completed=false",
        ).json["total"], 1)

        analytics = self.client.get(f"/api/career-analytics/{self.student_id}").json
        self.assertEqual(analytics["student"]["student_id"], f"TEST-{self.suffix}")
        self.assertEqual(len(analytics["latest_analyses"]), 1)
        self.assertEqual(analytics["latest_analyses"][0]["job_record_id"], self.job_id)

    def test_mock_interview_scoring_history_and_student_isolation(self):
        attempt = self.client.post("/api/mock-interviews", json={
            "student_id": self.student_id, "job_id": self.job_id,
        })
        self.assertEqual(attempt.status_code, 201, attempt.json)
        self.assertEqual(len(attempt.json["questions"]), 5)
        self.assertIn("not an expert or human assessment", attempt.json["notice"])
        answer = (
            "For example, in my Python project I built a Power BI dashboard and used SQL queries to validate "
            "the results. I measured the impact, documented the trade-off, and improved the final analysis "
            "after testing the approach with sample data."
        )
        result = self.client.post(f"/api/mock-interviews/{attempt.json['id']}/submit", json={
            "answers": [
                {"question_id": question["id"], "answer": answer if question["id"] < 5 else "I'm not sure yet."}
                for question in attempt.json["questions"]
            ],
        })
        self.assertEqual(result.status_code, 200, result.json)
        self.assertGreater(result.json["score_pct"], 0)
        self.assertEqual(len(result.json["feedback"]), 5)
        self.assertTrue(result.json["suggestions"])
        self.assertEqual(self.client.post(f"/api/mock-interviews/{attempt.json['id']}/submit", json={"answers":[]}).status_code, 409)

        second = self.client.post("/api/students", json={
            "student_id": f"ISOLATED-{self.suffix}", "student_name": "Isolated Student",
            "email": f"isolated-{self.suffix}@example.test", "branch": "ECE",
            "cgpa": 7, "coding_skill_score": 50, "aptitude_score": 50,
            "communication_skill_score": 50, "logical_reasoning_score": 50,
            "mock_interview_score": 50, "backlogs": 0, "github_repos": 0,
            "internships_count": 0, "projects_count": 0, "student_skills": "",
        })
        self.assertEqual(second.status_code, 201, second.json)
        self.assertEqual(self.client.get(f"/api/mock-interviews?student_id={second.json['id']}").json["items"], [])
        own_history = self.client.get(f"/api/mock-interviews?student_id={self.student_id}").json["items"]
        self.assertEqual(len(own_history), 1)
        self.assertEqual(own_history[0]["id"], attempt.json["id"])
        self.assertEqual(own_history[0]["status"], "completed")
        probe = """
import json, os
from backend.app import app
c=app.test_client()
print(json.dumps(c.get('/api/mock-interviews?student_id='+os.environ['SRM_TEST_STUDENT_ID']).json))
"""
        restart_env = os.environ.copy()
        restart_env["SRM_TEST_STUDENT_ID"] = str(self.student_id)
        restarted = subprocess.run(
            [sys.executable, "-c", probe], cwd=Path(__file__).resolve().parents[2],
            env=restart_env, check=True, capture_output=True, text=True,
        )
        persisted = json.loads(restarted.stdout.strip().splitlines()[-1])
        self.assertEqual(persisted["items"][0]["id"], attempt.json["id"])
        self.assertEqual(persisted["items"][0]["score_pct"], result.json["score_pct"])

    def test_proficiency_history_and_readiness_analytics(self):
        first = self.client.post("/api/skill-proficiency", json={
            "student_id": self.student_id, "skill": "PowerBI", "current_proficiency": 2,
            "learning_progress_pct": 20, "assessment_date": "2026-01-10",
        })
        self.assertEqual(first.status_code, 201, first.json)
        self.assertEqual(first.json["skill"], "Power BI")
        self.assertIsNone(first.json["improvement"])
        second = self.client.post("/api/skill-proficiency", json={
            "student_id": self.student_id, "skill": "Power BI", "current_proficiency": 4,
            "learning_progress_pct": 75, "assessment_date": "2026-02-10",
        })
        self.assertEqual(second.status_code, 201, second.json)
        self.assertEqual(second.json["previous_proficiency"], 2)
        self.assertEqual(second.json["improvement"], 2)
        history = self.client.get(f"/api/skill-proficiency?student_id={self.student_id}").json["items"]
        self.assertEqual(len(history), 2)
        self.assertEqual(history[-1]["assessment_date"], "2026-02-10")
        self.assertEqual(history[-1]["learning_progress_pct"], 75)
        analytics = self.client.get(f"/api/career-analytics/{self.student_id}").json
        self.assertEqual(analytics["proficiency_skills_tracked"], 1)
        self.assertEqual(analytics["average_proficiency"], 4)
        self.assertEqual(analytics["proficiency_by_skill"][0]["improvement"], 2)
        probe = """
import json, os
from backend.app import app
c=app.test_client()
print(json.dumps(c.get('/api/skill-proficiency?student_id='+os.environ['SRM_TEST_STUDENT_ID']).json))
"""
        restart_env = os.environ.copy()
        restart_env["SRM_TEST_STUDENT_ID"] = str(self.student_id)
        restarted = subprocess.run(
            [sys.executable, "-c", probe], cwd=Path(__file__).resolve().parents[2],
            env=restart_env, check=True, capture_output=True, text=True,
        )
        persisted = json.loads(restarted.stdout.strip().splitlines()[-1])
        self.assertEqual(len(persisted["items"]), 2)
        self.assertEqual(persisted["items"][-1]["current_proficiency"], 4)
        self.assertEqual(self.client.post("/api/skill-proficiency", json={
            "student_id": self.student_id, "skill": "Python", "current_proficiency": 6,
        }).status_code, 400)

    def test_validation_and_prediction_fallback_errors(self):
        self.assertEqual(self.client.post("/api/students", json={}).status_code, 400)
        self.assertEqual(self.client.put(f"/api/students/{self.student_id}", json={"cgpa":11}).status_code, 400)
        self.assertEqual(self.client.put(f"/api/jobs/{self.job_id}", json={"min_cgpa":7.5}).status_code, 200)
        self.assertEqual(self.client.get(f"/api/jobs/{self.job_id}").json["min_cgpa"], 7.5)
        row={"cgpa":"","coding_skill_score":70,"aptitude_score":70,"communication_skill_score":70,
             "logical_reasoning_score":70,"mock_interview_score":70,"backlogs":0,"github_repos":1,
             "internships_count":0,"projects_count":1,"branch":"CSE","role_category":"Data Analyst","work_mode":"Hybrid","algorithm":"SVM"}
        self.assertEqual(self.client.post("/api/predict",json=row).status_code,200)
        self.assertEqual(self.client.post("/api/predict",json={**row,"branch":"UNKNOWN"}).status_code,400)
        model=models.models.pop("SVM")
        try:
            unavailable=self.client.post("/api/predict",json=row)
            self.assertEqual(unavailable.status_code,503)
        finally:
            models.models["SVM"]=model

    def test_mandatory_eligibility_failures_are_separate(self):
        job = self.client.post("/api/jobs", json={
            "company_name": f"Restricted Co {self.suffix}", "job_title": "Restricted Analyst",
            "required_skills": "Python, SQL", "required_degree": "M.Tech", "min_cgpa": 9.0,
            "eligible_branches": "IT", "experience_min_yrs": 2,
            "required_certifications": "PL-300",
        }).json
        matches = self.client.get(f"/api/job-matches?student_id={self.student_id}").json["items"]
        match = next(x for x in matches if x["id"] == job["id"])
        self.assertEqual(match["eligibility_status"], "not_currently_eligible")
        self.assertEqual(match["match_category"], "not_eligible")
        self.assertEqual(len(match["eligibility_reasons"]), 5)
        self.assertEqual(match["matched_skills"], ["Python", "SQL"])
        self.assertIn("degree", match["method"])

    def test_job_and_student_delete_routes(self):
        changed=self.client.put(f"/api/jobs/{self.job_id}",json={"required_degree":"B.Tech"})
        self.assertEqual(changed.status_code,200)
        self.assertEqual(self.client.get(f"/api/jobs/{self.job_id}").json["required_degree"],"B.Tech")
        self.assertEqual(self.client.delete(f"/api/jobs/{self.job_id}").status_code,200)
        self.assertEqual(self.client.get(f"/api/jobs/{self.job_id}").status_code,404)
        self.assertEqual(self.client.delete(f"/api/students/{self.student_id}").status_code,200)
        self.assertEqual(self.client.get(f"/api/students/{self.student_id}").status_code,404)

    def test_two_saved_students_keep_independent_predictions_and_analysis(self):
        second = self.client.post("/api/students", json={
            "student_id": f"SECOND-{self.suffix}", "student_name": "Second Student",
            "email": f"second-{self.suffix}@example.test", "branch": "ECE", "degree": "B.Tech",
            "cgpa": 6.8, "coding_skill_score": 30, "aptitude_score": 35,
            "communication_skill_score": 40, "logical_reasoning_score": 32,
            "mock_interview_score": 28, "backlogs": 1, "github_repos": 0,
            "internships_count": 0, "projects_count": 0, "student_skills": "Excel",
        })
        self.assertEqual(second.status_code, 201, second.json)
        second_pk = second.json["id"]
        self.assertNotEqual(second_pk, self.student_id)

        update = self.client.put(f"/api/students/{second_pk}", json={"student_name":"Updated Second"})
        self.assertEqual(update.status_code, 200)
        self.assertEqual(self.client.get(f"/api/students/{second_pk}").json["student_name"], "Updated Second")
        self.assertEqual(self.client.get(f"/api/students/{self.student_id}").json["student_name"], "Test Student")

        # A separate Flask process uses the same throwaway DB to model backend restart.
        restart_probe = """
import json
from backend.app import app
c=app.test_client()
ids=[int(value) for value in __import__('os').environ['SRM_TEST_STUDENT_IDS'].split(',')]
print(json.dumps([c.get(f'/api/students/{value}').json for value in ids]))
"""
        restart_env = os.environ.copy()
        restart_env["SRM_TEST_STUDENT_IDS"] = f"{self.student_id},{second_pk}"
        restarted = subprocess.run(
            [sys.executable, "-c", restart_probe], cwd=Path(__file__).resolve().parents[2],
            env=restart_env, check=True, capture_output=True, text=True,
        )
        after_restart = json.loads(restarted.stdout.strip().splitlines()[-1])
        self.assertEqual([row["student_name"] for row in after_restart], ["Test Student", "Updated Second"])

        results = []
        for student_pk in (self.student_id, second_pk):
            response = self.client.post("/api/analyze", json={
                "student_record_id":student_pk,"job_record_id":self.job_id,
                "request_prediction":True,"algorithm":"SVM",
            })
            self.assertEqual(response.status_code, 201, response.json)
            results.append(response.json)
        first, second_result = results
        self.assertEqual(first["report"]["student_id"], f"TEST-{self.suffix}")
        self.assertEqual(second_result["report"]["student_id"], f"SECOND-{self.suffix}")
        self.assertEqual(first["matching"]["matched_skills"], ["Python", "SQL"])
        self.assertEqual(second_result["matching"]["matched_skills"], [])
        self.assertEqual(first["report"]["input_snapshot"]["cgpa"], 8.2)
        self.assertEqual(second_result["report"]["input_snapshot"]["cgpa"], 6.8)
        self.assertEqual(first["report"]["selected_model"], "SVM")
        self.assertEqual(second_result["report"]["selected_model"], "SVM")
        self.assertIn("SVM", first["predictions"])
        self.assertIn("SVM", second_result["predictions"])
        self.assertEqual(self.client.get(f"/api/analysis-history?student_id=TEST-{self.suffix}").json["total"], 1)
        self.assertEqual(self.client.get(f"/api/analysis-history?student_id=SECOND-{self.suffix}").json["total"], 1)

    def test_all_available_models_and_legacy_reports(self):
        feature_set = {
            "cgpa": 8.2, "coding_skill_score": 70, "aptitude_score": 72,
            "communication_skill_score": 74, "logical_reasoning_score": 71,
            "mock_interview_score": 68, "backlogs": 0, "github_repos": 2,
            "internships_count": 0, "projects_count": 1, "branch": "CSE",
            "role_category": "Data Analyst", "work_mode": "Hybrid",
        }
        algorithms = self.client.get("/api/model-info").json["available_algorithms"]
        self.assertEqual(len(algorithms), 5)
        for algorithm in algorithms:
            result = self.client.post("/api/predict", json={**feature_set, "algorithm": algorithm})
            self.assertEqual(result.status_code, 200, f"{algorithm}: {result.json}")
            self.assertIn("predictions", result.json)

        analysis = self.client.post("/api/analyze", json={
            **feature_set, "student_id": f"ANALYSIS-{self.suffix}",
            "student_name": "Report Student", "student_skills": "Python, SQL",
            "job_title": "Data Analyst", "company_name": "Report Co",
            "required_skills": "Python, SQL, Power BI", "request_prediction": True,
            "algorithm": "SVM",
        })
        self.assertEqual(analysis.status_code, 201, analysis.json)
        recs=self.client.get("/api/learning-recommendations?completed=false").json["items"]
        self.assertTrue(recs)
        self.assertEqual(self.client.patch(f"/api/learning-recommendations/{recs[0]['id']}",json={"is_completed":True}).status_code,200)
        pdf = self.client.post("/api/generate-report", json={"analysis_id": analysis.json["analysis_id"]})
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.data.startswith(b"%PDF"))
        csv = self.client.get("/api/export-analysis.csv")
        self.assertEqual(csv.status_code, 200)
        self.assertIn(b"ANALYSIS-", csv.data)


if __name__ == "__main__":
    unittest.main()
