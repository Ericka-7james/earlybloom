import pytest

from app.services.jobs.us_filters import (
    detect_spam_or_scam,
    has_non_us_hint,
    has_us_eligibility_hint,
    has_us_timezone_hint,
    is_global_remote_role,
    is_remote_like,
    is_us_remote_role,
    looks_non_us_location,
    looks_us_location,
    should_keep_us_focused_job,
)


def test_looks_us_location_with_state_code():
    assert looks_us_location("Atlanta, GA") is True


def test_looks_us_location_with_united_states():
    assert looks_us_location("Remote, United States") is True


def test_looks_us_location_with_us_remote_phrase():
    assert looks_us_location("Remote - US") is True


def test_looks_non_us_location_for_germany():
    assert looks_non_us_location("Berlin, Germany") is True


def test_looks_non_us_location_for_brazil_argentina():
    assert looks_non_us_location("Brazil, Argentina") is True


def test_has_us_eligibility_hint_for_work_auth():
    assert has_us_eligibility_hint("Must be authorized to work in the US") is True


def test_has_us_eligibility_hint_for_us_only():
    assert has_us_eligibility_hint("Remote, United States only") is True


def test_has_us_timezone_hint_for_est():
    assert has_us_timezone_hint("Candidates must overlap with EST hours") is True


def test_has_non_us_hint_for_europe_only():
    assert has_non_us_hint("Remote role", "Europe only", None) is True


def test_has_non_us_hint_does_not_fail_when_us_eligibility_is_present():
    assert (
        has_non_us_hint(
            "Software Engineer",
            "Must be authorized to work in the US",
            "Remote",
        )
        is False
    )


def test_is_remote_like_from_remote_flag():
    assert is_remote_like(location=None, description=None, remote_flag=True) is True


def test_is_remote_like_from_text():
    assert (
        is_remote_like(
            location="Remote",
            description="Work from home role",
            remote_flag=False,
        )
        is True
    )


def test_is_global_remote_role_for_worldwide():
    assert (
        is_global_remote_role(
            title="Software Engineer",
            location="Remote",
            description="Work from anywhere in the world",
        )
        is True
    )


def test_is_global_remote_role_for_region_limited_remote():
    assert (
        is_global_remote_role(
            title="Software Engineer",
            location="Remote - EMEA",
            description="Open to EMEA candidates only",
        )
        is True
    )


def test_is_us_remote_role_for_explicit_us_remote():
    assert (
        is_us_remote_role(
            title="Software Engineer",
            location="Remote, United States",
            description="Work remotely from the US",
            remote_flag=True,
        )
        is True
    )


def test_is_us_remote_role_for_us_timezone_hint():
    assert (
        is_us_remote_role(
            title="Support Engineer",
            location="Remote",
            description="Must overlap with Eastern Time hours",
            remote_flag=True,
        )
        is True
    )


def test_should_keep_us_focused_job_for_us_onsite_role():
    assert (
        should_keep_us_focused_job(
            title="Junior Software Engineer",
            location="Atlanta, GA",
            description="Entry level role",
            remote_flag=False,
        )
        is True
    )


def test_should_keep_us_focused_job_for_us_remote_role():
    assert (
        should_keep_us_focused_job(
            title="Software Engineer I",
            location="Remote, United States",
            description="Must be authorized to work in the US",
            remote_flag=True,
        )
        is True
    )


def test_should_reject_non_us_location():
    assert (
        should_keep_us_focused_job(
            title="Junior Developer",
            location="Berlin, Germany",
            description="Entry level role",
            remote_flag=False,
        )
        is False
    )


def test_should_reject_non_us_multi_country_location():
    assert (
        should_keep_us_focused_job(
            title="Junior Project Coordinator",
            location="Brazil, Argentina",
            description="Fully remote contractor role",
            remote_flag=True,
        )
        is False
    )


def test_should_reject_global_remote_role():
    assert (
        should_keep_us_focused_job(
            title="Backend Engineer",
            location="Remote",
            description="Work from anywhere in the world",
            remote_flag=True,
        )
        is False
    )


def test_should_reject_region_limited_remote_role():
    assert (
        should_keep_us_focused_job(
            title="Developer",
            location="Remote - Europe",
            description="Europe only",
            remote_flag=True,
        )
        is False
    )


def test_should_keep_remote_role_with_us_work_auth_hint_even_if_location_is_generic():
    assert (
        should_keep_us_focused_job(
            title="Software Engineer",
            location="Remote",
            description="Must be authorized to work in the US",
            remote_flag=True,
        )
        is True
    )


def test_should_keep_remote_role_with_us_timezone_overlap():
    assert (
        should_keep_us_focused_job(
            title="Technical Support Specialist",
            location="Remote",
            description="Must overlap with EST hours",
            remote_flag=True,
        )
        is True
    )


def test_should_reject_remote_role_with_no_us_signal():
    assert (
        should_keep_us_focused_job(
            title="Developer",
            location="Remote",
            description="Remote role for distributed team",
            remote_flag=True,
        )
        is False
    )


def test_detect_spam_or_scam_for_keyword_trick():
    assert (
        detect_spam_or_scam(
            title="Junior Engineer",
            company="Sketchy Co",
            location="Remote",
            description="To prove you read this, mention the word banana.",
            url="https://example.com/job",
        )
        is True
    )


def test_detect_spam_or_scam_for_crypto():
    assert (
        detect_spam_or_scam(
            title="Data Entry",
            company="Fake Crypto LLC",
            location="Remote",
            description="Buy bitcoin and contact us on Telegram.",
            url="https://example.com/job",
        )
        is True
    )


def test_detect_spam_or_scam_for_normal_job_is_false():
    assert (
        detect_spam_or_scam(
            title="IT Support Specialist",
            company="TestCo",
            location="Atlanta, GA",
            description="Provide help desk support and troubleshoot user issues.",
            url="https://example.com/job",
        )
        is False
    )