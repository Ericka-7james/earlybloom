from __future__ import annotations

from app.services.jobs.common.role_taxonomy import infer_role_type_from_text


def test_infer_role_type_returns_unknown_when_no_match_exists() -> None:
    assert infer_role_type_from_text(
        title="Community Volunteer",
        description="Helped organize neighborhood events and outreach.",
        tags=["people", "community"],
    ) == "unknown"


def test_infer_role_type_detects_software_from_title() -> None:
    assert infer_role_type_from_text(
        title="Software Engineer",
    ) == "software"


def test_infer_role_type_detects_software_from_description() -> None:
    assert infer_role_type_from_text(
        title="Engineer",
        description="Build frontend features and support full-stack web development.",
    ) == "software"


def test_infer_role_type_detects_it_support_from_title() -> None:
    assert infer_role_type_from_text(
        title="Help Desk Technician",
    ) == "it_support"


def test_infer_role_type_detects_it_support_from_tags() -> None:
    assert infer_role_type_from_text(
        title="Technician",
        tags=["desktop support", "ticketing"],
    ) == "it_support"


def test_infer_role_type_detects_data_role() -> None:
    assert infer_role_type_from_text(
        title="Business Intelligence Analyst",
        description="Own reporting and analytics dashboards.",
    ) == "data"

def test_infer_role_type_returns_first_match_based_on_pattern_order() -> None:
    assert infer_role_type_from_text(
        title="Business Intelligence Developer",
        description="Own reporting and analytics dashboards.",
    ) == "software"
    
def test_infer_role_type_detects_cloud_devops_role() -> None:
    assert infer_role_type_from_text(
        title="Platform Engineer",
        description="Worked on infrastructure and cloud deployments.",
    ) == "cloud_devops"


def test_infer_role_type_detects_security_role() -> None:
    assert infer_role_type_from_text(
        title="Security Analyst",
        description="Focused on IAM, SOC workflows, and governance risk reviews.",
    ) == "security"


def test_infer_role_type_detects_analyst_role() -> None:
    assert infer_role_type_from_text(
        title="Technical Analyst",
    ) == "analyst"


def test_infer_role_type_detects_ops_role() -> None:
    assert infer_role_type_from_text(
        title="Operations Coordinator",
    ) == "ops"


def test_infer_role_type_detects_customer_success_role() -> None:
    assert infer_role_type_from_text(
        title="Customer Success Associate",
        description="Supported client relationships and escalations.",
    ) == "customer_success"


def test_infer_role_type_detects_product_role() -> None:
    assert infer_role_type_from_text(
        title="Technical Product Associate",
        description="Partnered with teams on product workflows.",
    ) == "product"


def test_infer_role_type_is_case_insensitive() -> None:
    assert infer_role_type_from_text(
        title="FRONTEND DEVELOPER",
    ) == "software"


def test_infer_role_type_uses_first_matching_role_in_defined_order() -> None:
    assert infer_role_type_from_text(
        title="Security Product Analyst",
        description="IAM reviews and product operations support.",
    ) == "security"


def test_infer_role_type_handles_empty_inputs() -> None:
    assert infer_role_type_from_text(
        title="",
        description="",
        tags=[],
    ) == "unknown"


def test_infer_role_type_matches_backend_with_or_without_hyphen() -> None:
    assert infer_role_type_from_text(title="Backend Developer") == "software"
    assert infer_role_type_from_text(title="Back-end Developer") == "software"


def test_infer_role_type_matches_full_stack_with_or_without_hyphen() -> None:
    assert infer_role_type_from_text(title="Full Stack Engineer") == "software"
    assert infer_role_type_from_text(title="Full-Stack Engineer") == "software"


def test_infer_role_type_does_not_match_partial_word_boundaries() -> None:
    assert infer_role_type_from_text(
        title="Specialistically minded generalist",
        description="Strong cooperation and adaptability.",
    ) == "unknown"