"""Small dependency-free PDF report writer for stored analyses."""

from __future__ import annotations

import io
import textwrap
from datetime import datetime
from typing import Any


def _pdf_escape(value: Any) -> bytes:
    text = str(value).encode("latin-1", errors="replace").decode("latin-1")
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text.encode("latin-1")


def _lines(report: dict[str, Any]) -> list[str]:
    lines = [
        "PLACEMENT INTELLIGENCE - ANALYSIS REPORT",
        f"Generated: {datetime.now().astimezone().strftime('%Y-%m-%d %H:%M %Z')}",
        "",
        f"Student: {report.get('student_name') or 'Not provided'}",
        f"Student ID: {report.get('student_id') or 'Not provided'}",
        f"Target job: {report.get('job_title') or 'Not provided'}",
        f"Company: {report.get('company_name') or 'Not provided'}",
        f"Role category: {report.get('role_category') or 'Not provided'}",
        f"Skill match: {report.get('skill_match_pct') if report.get('skill_match_pct') is not None else 'Not analyzed'}%",
        f"Synthetic suitability label: {'Suitable (1)' if report.get('predicted_label') == 1 else 'Unsuitable (0)' if report.get('predicted_label') == 0 else 'Unavailable'}",
        f"Selected model: {report.get('selected_model') or 'None'}",
        f"Model note: {report.get('model_notice') or 'No runtime model output was saved.'}",
        "",
        "SUBMITTED PROFILE AND JOB DETAILS",
    ]
    scores = report.get("class_probabilities") or {}
    if scores:
        lines.append("Model class scores (not calibrated employment probabilities):")
        lines.extend([f"  Class {label}: {float(value) * 100:.2f}%" for label, value in scores.items()])
    snapshot = report.get("input_snapshot") or {}
    detail_fields = [
        ("Student email", "email"), ("Branch", "branch"), ("CGPA", "cgpa"),
        ("Coding score", "coding_skill_score"), ("Aptitude score", "aptitude_score"),
        ("Communication score", "communication_skill_score"), ("Logical reasoning score", "logical_reasoning_score"),
        ("Mock interview score", "mock_interview_score"), ("Backlogs", "backlogs"),
        ("GitHub repositories", "github_repos"), ("Internships", "internships_count"),
        ("Projects", "projects_count"), ("Student skills", "student_skills"),
        ("Job ID", "job_id"), ("Role category", "role_category"), ("Location", "location"),
        ("Work mode", "work_mode"), ("Required skills", "required_skills"),
        ("Fresher friendly", "is_fresher_friendly"), ("Minimum experience (years)", "experience_min_yrs"),
        ("Maximum experience (years)", "experience_max_yrs"), ("Job URL", "job_url"),
        ("Job description", "job_description"),
    ]
    for label, key in detail_fields:
        value = snapshot.get(key)
        if value not in (None, ""):
            if key == "is_fresher_friendly":
                value = "Yes" if value is True or value == 1 else "No"
            lines.append(f"{label}: {value}")
    lines += [
        "",
        "MATCHED SKILLS",
    ]
    lines.extend([f"  - {skill}" for skill in report.get("matched_skills", [])] or ["  None recorded"])
    lines += ["", "MISSING SKILLS"]
    lines.extend([f"  - {skill}" for skill in report.get("missing_skills", [])] or ["  None recorded"])
    lines += ["", "ADDITIONAL STUDENT SKILLS"]
    lines.extend([f"  - {skill}" for skill in report.get("additional_skills", [])] or ["  None recorded"])
    lines += ["", "LEARNING ACTIVITIES"]
    for item in report.get("recommendations", []):
        lines.append(f"  {item.get('skill')} [{item.get('category') or 'Uncategorized'}] — {item.get('priority') or 'Unranked'}")
        if item.get("why_it_matters"):
            lines.append(f"    Why it matters: {item['why_it_matters']}")
        lines.append(f"    Activity: {item.get('learning_activity')}")
        lines.append(f"    Project: {item.get('project_idea')}")
    if not report.get("recommendations"):
        lines.append("  No skill-gap recommendations recorded.")
    lines += [
        "",
        "LIMITATION",
        "The suitability target is synthetic. This report is not a hiring decision,",
        "verified placement outcome, or guarantee of employment.",
    ]
    wrapped: list[str] = []
    for line in lines:
        wrapped.extend(textwrap.wrap(line, width=90) or [""])
    return wrapped


def generate_pdf(report: dict[str, Any]) -> bytes:
    lines = _lines(report)
    page_chunks = [lines[i:i + 48] for i in range(0, len(lines), 48)] or [[]]
    objects: list[bytes] = []
    page_ids = [4 + i * 2 for i in range(len(page_chunks))]
    content_ids = [page_id + 1 for page_id in page_ids]
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    for page_id, content_id, chunk in zip(page_ids, content_ids, page_chunks):
        commands = [b"BT /F1 10 Tf 48 790 Td 14 TL"]
        for line in chunk:
            commands.append(b"(" + _pdf_escape(line) + b") Tj T*")
        commands.append(b"ET")
        stream = b"\n".join(commands)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>".encode()
        )
        objects.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")

    output = io.BytesIO()
    output.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(output.tell())
        output.write(f"{number} 0 obj\n".encode())
        output.write(body + b"\nendobj\n")
    xref_at = output.tell()
    output.write(f"xref\n0 {len(objects) + 1}\n".encode())
    output.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode())
    output.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_at}\n%%EOF".encode())
    return output.getvalue()
