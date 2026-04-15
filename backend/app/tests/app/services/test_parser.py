from __future__ import annotations

from app.services import parser


def test_preprocess_resume_text_splits_header_tokens_and_inline_sections():
    raw_text = (
        "Ericka Smiley James Atlanta, GA • james@example.com • github.com/ericka "
        "PROFESSIONAL SUMMARY Software Engineer with 2+ years of experience "
        "SKILLS Python, React"
    )

    result = parser.preprocess_resume_text(raw_text)

    assert "Atlanta, GA\njames@example.com" in result
    assert "github.com/ericka\nPROFESSIONAL SUMMARY" in result
    assert "PROFESSIONAL SUMMARY\nSoftware Engineer with 2+ years of experience" in result
    assert "SKILLS\nPython, React" in result


def test_infer_name_extracts_name_from_header_with_trailing_location():
    header_lines = [
        "Ericka Smiley James Atlanta, GA",
        "james7.ericka@gmail.com",
    ]

    result = parser.infer_name(header_lines)

    assert result == "Ericka Smiley James"


def test_infer_location_extracts_trailing_city_state_from_header():
    header_lines = [
        "Ericka Smiley James Atlanta, GA",
        "james7.ericka@gmail.com",
    ]

    result = parser.infer_location(header_lines)

    assert result.raw == "Atlanta, GA"
    assert result.city == "Atlanta"
    assert result.region == "GA"
    assert result.country == "US"


def test_normalize_city_from_trailing_words_handles_two_word_city_prefix():
    result = parser.normalize_city_from_trailing_words(["Ericka", "James", "New", "York"])

    assert result == "New York"


def test_normalize_city_from_trailing_words_handles_single_word_city():
    result = parser.normalize_city_from_trailing_words(["Ericka", "James", "Atlanta"])

    assert result == "Atlanta"


def test_extract_links_labels_linkedin_and_github_and_portfolio():
    text = (
        "linkedin.com/in/erickasmileyjames "
        "github.com/ericka-7james "
        "www.myportfolio.dev"
    )

    result = parser.extract_links(text)

    assert len(result) == 3
    assert result[0].label == "LinkedIn"
    assert result[0].url == "https://linkedin.com/in/erickasmileyjames"
    assert result[1].label == "GitHub"
    assert result[1].url == "https://github.com/ericka-7james"
    assert result[2].label == "Portfolio"
    assert result[2].url == "https://www.myportfolio.dev"


def test_parse_date_range_handles_present_range():
    start, end, is_current = parser.parse_date_range("Jan 2022 - Present")

    assert start == "2022-01"
    assert end is None
    assert is_current is True


def test_parse_date_range_returns_empty_tuple_for_non_date_text():
    start, end, is_current = parser.parse_date_range("Built APIs and dashboards")

    assert start is None
    assert end is None
    assert is_current is False


def test_normalize_date_token_handles_year_only_and_month_year():
    assert parser.normalize_date_token("2021") == "2021"
    assert parser.normalize_date_token("Sept. 2023") == "2023-09"
    assert parser.normalize_date_token("nonsense") is None


def test_parse_education_extracts_degree_and_field_of_study():
    section_lines = [
        "Spelman College",
        "Bachelor of Science in Computer Science",
        "Aug 2021 - May 2025",
    ]

    result = parser.parse_education(section_lines)

    assert len(result) == 1
    assert result[0].school == "Spelman College"
    assert "Bachelor of Science" in result[0].degree
    assert result[0].field_of_study == "Computer Science"
    assert result[0].start_date == "2021-08"
    assert result[0].end_date == "2025-05"


def test_parse_experience_extracts_role_company_dates_and_skills():
    section_lines = [
        "Software Engineer | JPMorgan Chase",
        "Jan 2024 - Present",
        "- Built React and Python features",
        "- Worked with SQL APIs",
    ]

    result = parser.parse_experience(section_lines, ["react", "python", "sql"])

    assert len(result) == 1
    assert result[0].role == "Software Engineer"
    assert result[0].company == "JPMorgan Chase"
    assert result[0].start_date == "2024-01"
    assert result[0].end_date is None
    assert result[0].is_current is True
    assert "Built React and Python features" in result[0].bullet_points
    assert result[0].normalized_skills == ["react", "python", "sql"]


def test_parse_projects_extracts_project_and_tech_stack():
    section_lines = [
        "EarlyBloom",
        "- Built with React, Python, and Supabase",
        "- github.com/ericka-7james/earlybloom",
    ]

    result = parser.parse_projects(section_lines, ["react", "python", "supabase"])

    assert len(result) == 1
    assert result[0].title == "EarlyBloom"
    assert "Built with React, Python, and Supabase" in result[0].description
    assert result[0].tech_stack == ["react", "python", "supabase"]
    assert len(result[0].links) == 1
    assert result[0].links[0].label == "GitHub"


def test_chunk_section_splits_on_title_case_heading_and_not_date_lines():
    lines = [
        "Software Engineer | Company A",
        "Jan 2022 - Present",
        "- Did things",
        "Research Assistant",
        "- Did more things",
    ]

    result = parser.chunk_section(lines)

    assert len(result) == 2
    assert result[0][0] == "Software Engineer | Company A"
    assert result[0][1] == "Jan 2022 - Present"
    assert result[1][0] == "Research Assistant"


def test_clean_bullet_removes_common_bullet_prefixes():
    assert parser.clean_bullet("- Built API") == "Built API"
    assert parser.clean_bullet("• Built UI") == "Built UI"
    assert parser.clean_bullet("* Shipped feature") == "Shipped feature"


def test_infer_years_experience_sums_years_from_structured_experience():
    experience = [
        parser.ResumeExperience(start_date="2020-01", end_date="2022-01", is_current=False),
        parser.ResumeExperience(start_date="2022-01", end_date="2023-01", is_current=False),
    ]

    result = parser.infer_years_experience(experience)

    assert result == 3


def test_infer_years_experience_from_text_extracts_numeric_years():
    text = "Software Engineer with 2+ years of experience building platforms."

    result = parser.infer_years_experience_from_text(text)

    assert result == 2


def test_infer_primary_role_signals_returns_general_software_when_no_matches():
    result = parser.infer_primary_role_signals(["figma"])

    assert result == ["general_software"]


def test_compute_confidence_scores_populated_resume():
    parsed_resume = parser.ParsedResume(
        basics=parser.ResumeBasics(
            name="Ericka Smiley James",
            email="james7.ericka@gmail.com",
            phone="(706) 573-6807",
        ),
        education=[parser.ResumeEducation(school="Spelman College")],
        experience=[parser.ResumeExperience(role="Software Engineer")],
        projects=[parser.ResumeProject(title="EarlyBloom")],
        skills=parser.ResumeSkills(normalized=["python", "react"]),
        summary=parser.ResumeSummary(),
        meta=parser.ResumeMeta(parsed_at=parser.datetime.now(parser.UTC)),
    )

    result = parser.compute_confidence(parsed_resume)

    assert result == 1.0


def test_parse_resume_text_uses_fallback_years_and_extracts_location_and_skills():
    raw_text = """
    Ericka Smiley James Atlanta, GA • james7.ericka@gmail.com • github.com/ericka-7james
    PROFESSIONAL SUMMARY Software Engineer with 2+ years of experience building full-stack apps.
    SKILLS
    Python, JavaScript, HTML, Pandas, Terraform, Docker
    """

    parsed_json, warnings = parser.parse_resume_text(
        raw_text,
        file_type="application/pdf",
        extraction_method="pdfjs_text",
    )

    assert parsed_json["basics"]["name"] == "Ericka Smiley James"
    assert parsed_json["basics"]["email"] == "james7.ericka@gmail.com"
    assert parsed_json["basics"]["location"]["raw"] == "Atlanta, GA"
    assert parsed_json["basics"]["location"]["city"] == "Atlanta"
    assert parsed_json["summary"]["estimated_years_experience"] == 2
    assert parsed_json["summary"]["seniority"] == "early_career"
    assert parsed_json["skills"]["normalized"] == [
        "python",
        "javascript",
        "html",
        "pandas",
        "terraform",
        "docker",
    ]
    assert "Could not confidently infer candidate name." not in warnings
    assert parsed_json["meta"]["source_file_type"] == "application/pdf"
    assert parsed_json["meta"]["extraction_method"] == "pdfjs_text"


def test_build_empty_parsed_resume_returns_default_shape():
    result = parser.build_empty_parsed_resume("application/msword")

    assert result["basics"]["name"] is None
    assert result["education"] == []
    assert result["experience"] == []
    assert result["projects"] == []
    assert result["skills"]["normalized"] == []
    assert result["summary"]["estimated_years_experience"] == 0
    assert result["meta"]["source_file_type"] == "application/msword"
    assert result["meta"]["parser_version"] == "v1"