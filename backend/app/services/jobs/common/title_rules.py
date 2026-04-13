from __future__ import annotations

import re

SENIOR_EXCLUSION_TOKENS = {
    "senior",
    "sr",
    "sr.",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "architect",
    "distinguished",
    "head",
    "vp",
    "vice president",
    "chief",
    "supervisor",
}

EARLY_CAREER_POSITIVE_SIGNALS = {
    "junior",
    "entry",
    "entry level",
    "associate",
    "recent graduate",
    "recent graduates",
    "new grad",
    "new graduate",
    "apprentice",
    "trainee",
    "rotational",
    "rotation program",
    "fellowship",
    "intern",
    "internship",
    "early career",
    "campus",
    "graduate program",
}

AMBIGUOUS_BUT_KEEP_SIGNALS = {
    "analyst",
    "specialist",
    "coordinator",
    "support",
    "technician",
    "administrator",
    "operator",
    "representative",
    "consultant",
    "engineer",
    "developer",
    "qa",
    "tester",
    "systems",
    "it",
    "help desk",
    "service desk",
    "implementation",
    "customer success",
    "product",
    "security",
    "cybersecurity",
    "data",
}

TITLE_NORMALIZATION_PATTERN = re.compile(r"[^a-z0-9+/#.\- ]+")


def normalize_title(title: str) -> str:
    value = str(title or "").strip().lower()
    value = value.replace("&", " and ")
    value = TITLE_NORMALIZATION_PATTERN.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def title_contains_token(title: str, token: str) -> bool:
    normalized_title = f" {normalize_title(title)} "
    normalized_token = f" {normalize_title(token)} "
    return normalized_token in normalized_title


def contains_any_token(title: str, tokens: set[str]) -> bool:
    return any(title_contains_token(title, token) for token in tokens)


def is_obviously_senior_title(title: str) -> bool:
    normalized = normalize_title(title)

    if not normalized:
        return False

    if contains_any_token(normalized, SENIOR_EXCLUSION_TOKENS):
        return True

    # Extra guardrails for common senior phrasing.
    extra_patterns = [
        r"\bteam lead\b",
        r"\btech lead\b",
        r"\blead software\b",
        r"\blead engineer\b",
        r"\blead developer\b",
        r"\bsenior[- ]level\b",
        r"\bpeople manager\b",
        r"\bengineering manager\b",
        r"\bsolution architect\b",
        r"\benterprise architect\b",
    ]

    return any(re.search(pattern, normalized) for pattern in extra_patterns)


def is_early_career_title(title: str) -> bool:
    normalized = normalize_title(title)
    return contains_any_token(normalized, EARLY_CAREER_POSITIVE_SIGNALS)


def is_ambiguous_but_keep_title(title: str) -> bool:
    normalized = normalize_title(title)
    return contains_any_token(normalized, AMBIGUOUS_BUT_KEEP_SIGNALS)


def should_keep_title_for_earlybloom(title: str) -> bool:
    """
    Broad Layer 1 keep rule:
    - reject obvious senior roles
    - keep clearly early-career titles
    - keep ambiguous but relevant tech/ops/support titles
    - otherwise keep if it still smells like a likely technical role
    """
    normalized = normalize_title(title)

    if not normalized:
        return False

    if is_obviously_senior_title(normalized):
        return False

    if is_early_career_title(normalized):
        return True

    if is_ambiguous_but_keep_title(normalized):
        return True

    fallback_patterns = [
        r"\bsoftware\b",
        r"\bdeveloper\b",
        r"\bengineer\b",
        r"\bit\b",
        r"\binformation technology\b",
        r"\bdata\b",
        r"\bcyber\b",
        r"\bcloud\b",
        r"\bdevops\b",
        r"\bplatform\b",
        r"\bapplication\b",
        r"\bsystems?\b",
        r"\bnetwork\b",
        r"\btechnical\b",
        r"\bproduct\b",
    ]

    return any(re.search(pattern, normalized) for pattern in fallback_patterns)