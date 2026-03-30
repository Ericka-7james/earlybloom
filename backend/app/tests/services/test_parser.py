from app.services.parser import build_empty_parsed_resume, parse_resume_text


def test_build_empty_parsed_resume_returns_expected_shape() -> None:
    parsed = build_empty_parsed_resume()

    assert "basics" in parsed
    assert "education" in parsed
    assert "experience" in parsed
    assert "projects" in parsed
    assert "skills" in parsed
    assert "summary" in parsed
    assert "meta" in parsed

    assert parsed["basics"]["name"] is None
    assert parsed["education"] == []
    assert parsed["experience"] == []
    assert parsed["projects"] == []
    assert parsed["skills"]["raw"] == []
    assert parsed["skills"]["normalized"] == []
    assert parsed["summary"]["estimated_years_experience"] == 0
    assert parsed["summary"]["seniority"] == "early_career"
    assert parsed["meta"]["parser_version"] == "v1"
    assert parsed["meta"]["source_file_type"] == "application/pdf"


def test_parse_resume_text_extracts_core_fields() -> None:
    raw_text = """
    Jane Doe
    Atlanta, GA
    jane.doe@example.com
    (404) 555-1212
    https://linkedin.com/in/janedoe
    https://github.com/janedoe

    Education
    Spelman College
    Bachelor of Science in Computer Science
    2021 - 2025

    Experience
    Software Engineer Intern at Acme Corp
    Jun 2024 - Aug 2024
    - Built React features for internal dashboard
    - Worked with Python APIs and SQL queries

    Projects
    EarlyBloom
    Built a job-matching app with React, JavaScript, and Supabase.

    Skills
    React, JavaScript, Python, SQL, Supabase
    """.strip()

    parsed, warnings = parse_resume_text(raw_text)

    assert parsed["basics"]["name"] == "Jane Doe"
    assert parsed["basics"]["email"] == "jane.doe@example.com"
    assert parsed["basics"]["phone"] is not None
    assert parsed["basics"]["location"]["city"] == "Atlanta"
    assert parsed["basics"]["location"]["region"] == "GA"

    assert len(parsed["education"]) >= 1
    assert parsed["education"][0]["school"] == "Spelman College"

    assert len(parsed["experience"]) >= 1
    assert parsed["experience"][0]["role"] is not None

    assert len(parsed["projects"]) >= 1
    assert parsed["projects"][0]["title"] == "EarlyBloom"

    normalized_skills = parsed["skills"]["normalized"]
    assert "react" in normalized_skills
    assert "javascript" in normalized_skills
    assert "python" in normalized_skills
    assert "sql" in normalized_skills
    assert "supabase" in normalized_skills

    assert parsed["summary"]["seniority"] == "early_career"
    assert "frontend" in parsed["summary"]["primary_role_signals"] or "full_stack" in parsed["summary"]["primary_role_signals"]

    assert isinstance(warnings, list)


def test_parse_resume_text_handles_sparse_resume() -> None:
    raw_text = """
    Test Person
    test.person@example.com

    Skills
    Python, SQL
    """.strip()

    parsed, warnings = parse_resume_text(raw_text)

    assert parsed["basics"]["name"] == "Test Person"
    assert parsed["basics"]["email"] == "test.person@example.com"
    assert parsed["skills"]["normalized"] == ["python", "sql"]

    assert len(warnings) >= 1
    assert any("education" in warning.lower() for warning in warnings)