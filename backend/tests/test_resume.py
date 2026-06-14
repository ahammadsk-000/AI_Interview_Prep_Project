"""Integration tests for the Resume Analyzer + ATS Optimization API (Phase 2)."""
from __future__ import annotations

import io

import pytest
from httpx import AsyncClient

API = "/api/v1"

RESUME_TEXT = (
    "Jane Doe\n"
    "jane.doe@example.com | +1 415 555 0199 | linkedin.com/in/janedoe\n"
    "Summary\nSenior ML Engineer building GenAI systems.\n"
    "Experience\n"
    "- Led a team that built a RAG platform with Python, FastAPI and pgvector, "
    "reducing latency by 40%.\n"
    "- Deployed Kubernetes microservices on AWS, improving throughput 3x.\n"
    "Skills\nPython, PyTorch, Docker, Kubernetes, PostgreSQL, FastAPI\n"
    "Education\nB.Tech Computer Science\n"
    "Projects\n- Built an LLM evaluation harness.\n"
)


def _txt_upload(name: str = "resume.txt"):
    return {"file": (name, io.BytesIO(RESUME_TEXT.encode()), "text/plain")}


def _docx_upload(name: str = "resume.docx"):
    from docx import Document

    doc = Document()
    for line in RESUME_TEXT.splitlines():
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return {"file": (name, io.BytesIO(buf.getvalue()),
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}


async def _upload(client: AsyncClient, headers: dict, files) -> str:
    resp = await client.post(f"{API}/resumes", headers=headers, files=files)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_upload_txt_resume_parses(client: AsyncClient, auth_headers):
    resp = await client.post(f"{API}/resumes", headers=auth_headers, files=_txt_upload())
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "parsed"
    assert body["parsed_chars"] > 0


@pytest.mark.asyncio
async def test_upload_docx_resume_parses(client: AsyncClient, auth_headers):
    resp = await client.post(f"{API}/resumes", headers=auth_headers, files=_docx_upload())
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "parsed"


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_extension(client: AsyncClient, auth_headers):
    files = {"file": ("malware.exe", io.BytesIO(b"MZ..."), "application/octet-stream")}
    resp = await client.post(f"{API}/resumes", headers=auth_headers, files=files)
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


@pytest.mark.asyncio
async def test_upload_rejects_fake_pdf(client: AsyncClient, auth_headers):
    files = {"file": ("resume.pdf", io.BytesIO(b"not really a pdf"), "application/pdf")}
    resp = await client.post(f"{API}/resumes", headers=auth_headers, files=files)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient):
    resp = await client.post(f"{API}/resumes", files=_txt_upload())
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_and_get_resume(client: AsyncClient, auth_headers):
    resume_id = await _upload(client, auth_headers, _txt_upload())
    lst = await client.get(f"{API}/resumes", headers=auth_headers)
    assert lst.status_code == 200
    assert any(r["id"] == resume_id for r in lst.json())
    got = await client.get(f"{API}/resumes/{resume_id}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["id"] == resume_id


@pytest.mark.asyncio
async def test_cannot_access_other_users_resume(client: AsyncClient, auth_headers, other_user_headers):
    resume_id = await _upload(client, auth_headers, _txt_upload())
    resp = await client.get(f"{API}/resumes/{resume_id}", headers=other_user_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_analyze_without_jd(client: AsyncClient, auth_headers):
    resume_id = await _upload(client, auth_headers, _txt_upload())
    resp = await client.post(
        f"{API}/resumes/{resume_id}/analyze", headers=auth_headers, json={}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    for key in ("ats_score", "recruiter_score", "tech_score", "comm_score", "readiness"):
        assert 0 <= body[key] <= 100
    assert isinstance(body["suggestions"], list)
    assert "Python" in body["matched_keywords"]


@pytest.mark.asyncio
async def test_analyze_against_inline_jd_reports_gaps(client: AsyncClient, auth_headers):
    resume_id = await _upload(client, auth_headers, _txt_upload())
    jd = "We need Python, Kubernetes, Terraform and Go experience for this SRE role."
    resp = await client.post(
        f"{API}/resumes/{resume_id}/analyze",
        headers=auth_headers,
        json={"jd_text": jd},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "Terraform" in body["missing_keywords"]
    assert "Python" in body["matched_keywords"]


@pytest.mark.asyncio
async def test_create_job_description_extracts_skills(client: AsyncClient, auth_headers):
    resp = await client.post(
        f"{API}/job-descriptions",
        headers=auth_headers,
        json={"title": "ML Engineer", "company": "Acme",
              "raw_text": "Seeking an ML Engineer skilled in Python, PyTorch and AWS."},
    )
    assert resp.status_code == 201, resp.text
    skills = resp.json()["extracted_skills"]
    assert {"Python", "PyTorch", "AWS"} <= set(skills)


@pytest.mark.asyncio
async def test_analyze_with_saved_jd(client: AsyncClient, auth_headers):
    resume_id = await _upload(client, auth_headers, _txt_upload())
    jd_resp = await client.post(
        f"{API}/job-descriptions",
        headers=auth_headers,
        json={"raw_text": "Role requires Python, Kubernetes, Terraform and Spark."},
    )
    jd_id = jd_resp.json()["id"]
    resp = await client.post(
        f"{API}/resumes/{resume_id}/analyze",
        headers=auth_headers,
        json={"job_description_id": jd_id},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["job_description_id"] == jd_id
    assert "Terraform" in resp.json()["missing_keywords"]


@pytest.mark.asyncio
async def test_optimize_returns_improved_resume(client: AsyncClient, auth_headers):
    resume_id = await _upload(client, auth_headers, _txt_upload())
    resp = await client.post(
        f"{API}/ats/optimize",
        headers=auth_headers,
        json={"resume_id": resume_id,
              "jd_text": "Need Python, Terraform, Go and Kubernetes."},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert 0 <= body["ats_compatibility"] <= 100
    assert "Terraform" in body["missing_keywords"]
    assert body["improved_resume_text"]
    assert body["recruiter_insights"]


@pytest.mark.asyncio
async def test_optimize_rejects_other_users_resume(client: AsyncClient, auth_headers, other_user_headers):
    resume_id = await _upload(client, auth_headers, _txt_upload())
    resp = await client.post(
        f"{API}/ats/optimize",
        headers=other_user_headers,
        json={"resume_id": resume_id},
    )
    assert resp.status_code == 404
