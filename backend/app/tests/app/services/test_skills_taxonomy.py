from __future__ import annotations

from app.services.jobs.common.skills_taxonomy import (
    categorize_skills,
    dedupe_preserve_order,
    extract_skills_from_text,
    normalize_skill,
)


def test_dedupe_preserve_order_removes_blanks_and_duplicates_case_insensitively() -> None:
    items = ["Python", " python ", "", "AWS", "aws", "React", "react", "  "]

    assert dedupe_preserve_order(items) == ["Python", "AWS", "React"]


def test_normalize_skill_returns_none_for_empty_or_unknown_values() -> None:
    assert normalize_skill("") is None
    assert normalize_skill("   ") is None
    assert normalize_skill("made up skill") is None


def test_normalize_skill_maps_aliases_to_canonical_values() -> None:
    assert normalize_skill("js") == "JavaScript"
    assert normalize_skill("typescript") == "TypeScript"
    assert normalize_skill("amazon web services") == "AWS"
    assert normalize_skill("postgres") == "PostgreSQL"
    assert normalize_skill("powerbi") == "Power BI"
    assert normalize_skill("react.js") == "React"
    assert normalize_skill("nodejs") == "Node.js"
    assert normalize_skill("service now") == "ServiceNow"


def test_normalize_skill_accepts_canonical_values_case_insensitively() -> None:
    assert normalize_skill("python") == "Python"
    assert normalize_skill("PYTHON") == "Python"
    assert normalize_skill("GitHub Actions") == "GitHub Actions"
    assert normalize_skill("github actions") == "GitHub Actions"


def test_extract_skills_from_text_returns_empty_list_for_blank_text() -> None:
    assert extract_skills_from_text("") == []
    assert extract_skills_from_text("   ") == []


def test_extract_skills_from_text_extracts_skills_in_appearance_order() -> None:
    text = """
    Built internal dashboards in Excel and Tableau.
    Automated reporting with Python and SQL.
    Deployed services to AWS using Docker.
    """

    assert extract_skills_from_text(text) == [
        "Excel",
        "Tableau",
        "Python",
        "SQL",
        "AWS",
        "Docker",
    ]


def test_extract_skills_from_text_normalizes_aliases_and_dedupes_results() -> None:
    text = """
    Strong experience with js, JavaScript, react.js, React, postgres, PostgreSQL,
    amazon web services, AWS, powerbi, and Power BI.
    """

    assert extract_skills_from_text(text) == [
        "JavaScript",
        "React",
        "PostgreSQL",
        "AWS",
        "Power BI",
    ]


def test_extract_skills_from_text_matches_multiword_and_symbol_skills() -> None:
    text = """
    Supported Azure AD and Active Directory environments.
    Worked with GitHub Actions, CI/CD, TCP/IP, and C# services.
    """

    assert extract_skills_from_text(text) == [
        "Azure AD",
        "Active Directory",
        "GitHub Actions",
        "CI/CD",
        "TCP/IP",
        "C#",
    ]


def test_extract_skills_from_text_respects_word_boundaries_for_short_terms() -> None:
    text = """
    We value communication and collaboration.
    This role is not about goal setting or restoring old systems.
    """

    extracted = extract_skills_from_text(text)

    assert "Go" not in extracted
    assert "REST APIs" not in extracted
    assert extracted == ["Communication", "Collaboration"]


def test_extract_skills_from_text_detects_rest_api_variants() -> None:
    text = """
    Built integrations using REST APIs and GraphQL.
    Also documented each REST API for internal teams.
    """

    assert extract_skills_from_text(text) == ["REST APIs", "GraphQL"]


def test_categorize_skills_groups_by_category_and_dedupes_normalized_values() -> None:
    skills = [
        "python",
        "js",
        "react",
        "aws",
        "postgres",
        "excel",
        "docker",
        "jira",
        "salesforce",
        "security+",
        "communication",
        "React",
    ]

    assert categorize_skills(skills) == {
        "languages": ["Python", "JavaScript"],
        "frameworks": ["React"],
        "cloud": ["AWS"],
        "databases": ["PostgreSQL"],
        "data_tools": ["Excel"],
        "dev_tools": ["Docker"],
        "it_tools": ["Jira"],
        "crm_tools": ["Salesforce"],
        "certifications": ["Security+"],
        "soft_skills": ["Communication"],
    }


def test_categorize_skills_skips_unknown_values() -> None:
    skills = ["Python", "unknown thing", "AWS", "   ", "NotASkill"]

    assert categorize_skills(skills) == {
        "languages": ["Python"],
        "cloud": ["AWS"],
    }


def test_categorize_skills_places_uncategorized_canonical_skill_in_other() -> None:
    skills = ["GitHub"]

    assert categorize_skills(skills) == {
        "dev_tools": ["GitHub"],
    }