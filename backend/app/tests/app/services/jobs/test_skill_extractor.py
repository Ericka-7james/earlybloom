from __future__ import annotations

from app.schemas.jobs import NormalizedJob
from app.services.jobs.common.skill_extractor import (
    MAX_JOB_SKILLS,
    attach_normalized_skills,
    build_job_skill_text,
)


def make_job(**overrides) -> NormalizedJob:
    data = {
        "id": "job-1",
        "title": "Junior Software Engineer",
        "company": "EarlyBloom",
        "location": "Atlanta, GA",
        "url": "https://example.com/jobs/1",
        "source": "test",
        "summary": "",
        "description": "",
        "responsibilities": [],
        "qualifications": [],
        "required_skills": [],
        "preferred_skills": [],
        "skills": [],
    }
    data.update(overrides)
    return NormalizedJob(**data)


def test_build_job_skill_text_combines_all_relevant_job_fields() -> None:
    job = make_job(
        title="Junior React Developer",
        summary="Build internal tools with JavaScript.",
        description="Use AWS and SQL in production systems.",
        responsibilities=["Build dashboards in React", "Work with APIs"],
        qualifications=["Experience with Docker"],
        required_skills=["React", "JavaScript"],
        preferred_skills=["AWS"],
    )

    result = build_job_skill_text(job)

    assert "Junior React Developer" in result
    assert "Build internal tools with JavaScript." in result
    assert "Use AWS and SQL in production systems." in result
    assert "Build dashboards in React" in result
    assert "Work with APIs" in result
    assert "Experience with Docker" in result
    assert "React JavaScript" in result
    assert "AWS" in result


def test_build_job_skill_text_skips_empty_fields() -> None:
    job = make_job(
        title="IT Support Specialist",
        summary="",
        description="",
        responsibilities=[],
        qualifications=[],
        required_skills=[],
        preferred_skills=[],
    )

    result = build_job_skill_text(job)

    assert result == "IT Support Specialist"


def test_attach_normalized_skills_extracts_canonical_skills_from_job_fields() -> None:
    job = make_job(
        title="Junior React Developer",
        summary="Build internal tools with JavaScript and React.js.",
        description="Use Amazon Web Services, Postgres, SQL, and Docker.",
        responsibilities=["Work with APIs and Git"],
        qualifications=["Experience with ServiceNow is helpful"],
    )

    result = attach_normalized_skills(job)

    assert result.skills == [
        "React",
        "JavaScript",
        "AWS",
        "PostgreSQL",
        "SQL",
        "Docker",
        "REST APIs",
        "Git",
        "ServiceNow",
    ]


def test_attach_normalized_skills_dedupes_and_preserves_order() -> None:
    job = make_job(
        title="Python Developer",
        summary="Python and React role",
        description="Need python, React.js, Amazon Web Services, and python again.",
        required_skills=["React", "AWS"],
        preferred_skills=["Python"],
    )

    result = attach_normalized_skills(job)

    assert result.skills == ["Python", "React", "AWS"]


def test_attach_normalized_skills_mutates_and_returns_same_job_instance() -> None:
    job = make_job(
        title="Data Analyst",
        description="Strong SQL, Excel, Tableau, and PowerBI experience required.",
    )

    result = attach_normalized_skills(job)

    assert result is job
    assert job.skills == ["SQL", "Excel", "Tableau", "Power BI"]


def test_attach_normalized_skills_returns_empty_list_when_no_known_skills_found() -> None:
    job = make_job(
        title="Operations Coordinator",
        description="Coordinate scheduling, documentation, and general support.",
    )

    result = attach_normalized_skills(job)

    assert result.skills == []


def test_attach_normalized_skills_caps_total_results_at_max_job_skills() -> None:
    job = make_job(
        title="Platform Engineer",
        description=(
            "Python Java JavaScript TypeScript SQL Bash PowerShell HTML CSS C# C++ "
            "Go Rust React Node.js FastAPI Django Flask .NET Spring Express "
            "Pandas NumPy AWS Azure GCP Docker Kubernetes Terraform Ansible "
            "PostgreSQL MySQL MongoDB Snowflake BigQuery Redshift Spark Excel Tableau Power BI "
            "Git GitHub GitHub Actions GitLab CI Jenkins Linux GraphQL CI/CD Pytest Jest "
            "Jira Confluence ServiceNow Salesforce Active Directory Azure AD Microsoft 365 "
            "Office 365 Intune Jamf Okta SSO VPN DNS DHCP TCP/IP Troubleshooting IAM SIEM "
            "Splunk Microsoft Sentinel Incident Response Vulnerability Management Risk Assessment "
            "NIST Zero Trust Security+"
        ),
    )

    result = attach_normalized_skills(job)

    assert len(result.skills) == MAX_JOB_SKILLS


def test_attach_normalized_skills_can_extract_from_required_and_preferred_skill_lists() -> None:
    job = make_job(
        title="Business Systems Analyst",
        required_skills=["Excel", "PowerBI", "Salesforce"],
        preferred_skills=["Jira", "ServiceNow"],
    )

    result = attach_normalized_skills(job)

    assert result.skills == [
        "Excel",
        "Power BI",
        "Salesforce",
        "Jira",
        "ServiceNow",
    ]