from __future__ import annotations

from collections import OrderedDict

DOMAIN_SKILL_BANKS: dict[str, list[str]] = {
    "software": [
        "python",
        "java",
        "javascript",
        "typescript",
        "react",
        "node",
        "node.js",
        "html",
        "css",
        "sql",
        "postgres",
        "mysql",
        "mongodb",
        "graphql",
        "rest",
        "api",
        "git",
        "github",
        "docker",
        "kubernetes",
        "aws",
        "azure",
        "gcp",
        "fastapi",
        "django",
        "flask",
        "spring",
        "c#",
        ".net",
        "go",
        "rust",
        "c++",
        "testing",
        "pytest",
        "jest",
        "ci/cd",
    ],
    "it_support": [
        "active directory",
        "windows",
        "macos",
        "linux",
        "office 365",
        "microsoft 365",
        "azure ad",
        "intune",
        "vpn",
        "ticketing",
        "help desk",
        "service desk",
        "desktop support",
        "hardware",
        "software support",
        "troubleshooting",
        "networking",
        "tcp/ip",
        "dns",
        "dhcp",
        "jamf",
        "okta",
        "sso",
    ],
    "data": [
        "sql",
        "python",
        "excel",
        "tableau",
        "power bi",
        "pandas",
        "numpy",
        "etl",
        "data visualization",
        "dashboarding",
        "reporting",
        "analytics",
        "statistics",
        "bigquery",
        "snowflake",
        "redshift",
        "spark",
    ],
    "cloud_devops": [
        "aws",
        "azure",
        "gcp",
        "docker",
        "kubernetes",
        "terraform",
        "ansible",
        "jenkins",
        "github actions",
        "gitlab ci",
        "linux",
        "bash",
        "shell scripting",
        "monitoring",
        "prometheus",
        "grafana",
        "ci/cd",
        "infrastructure as code",
    ],
    "cybersecurity": [
        "siem",
        "splunk",
        "sentinel",
        "iam",
        "identity access management",
        "vulnerability management",
        "incident response",
        "threat detection",
        "soc",
        "security+",
        "network security",
        "cloud security",
        "risk assessment",
        "compliance",
        "nist",
        "zero trust",
    ],
    "product_business_systems": [
        "jira",
        "confluence",
        "agile",
        "scrum",
        "stakeholder management",
        "requirements gathering",
        "business analysis",
        "user stories",
        "roadmapping",
        "excel",
        "powerpoint",
        "visio",
        "salesforce",
        "servicenow",
        "peoplesoft",
        "workday",
        "hris",
        "crm",
    ],
}

ROLE_TYPE_TO_DOMAINS: dict[str, list[str]] = {
    "software": ["software"],
    "it_support": ["it_support"],
    "data": ["data"],
    "cloud_devops": ["cloud_devops", "software"],
    "security": ["cybersecurity", "cloud_devops"],
    "analyst": ["data", "product_business_systems"],
    "ops": ["product_business_systems", "it_support"],
    "customer_success": ["it_support", "product_business_systems"],
    "product": ["product_business_systems", "software"],
    "unknown": [
        "software",
        "it_support",
        "data",
        "cloud_devops",
        "cybersecurity",
        "product_business_systems",
    ],
}


def get_skill_bank_for_role_type(role_type: str | None) -> list[str]:
    key = str(role_type or "unknown").strip().lower()
    domains = ROLE_TYPE_TO_DOMAINS.get(key, ROLE_TYPE_TO_DOMAINS["unknown"])

    ordered: OrderedDict[str, None] = OrderedDict()
    for domain in domains:
        for skill in DOMAIN_SKILL_BANKS.get(domain, []):
            ordered.setdefault(skill.casefold(), None)

    # Return original-cased-ish values from the banks in stable order.
    seen: set[str] = set()
    result: list[str] = []
    for domain in domains:
        for skill in DOMAIN_SKILL_BANKS.get(domain, []):
            folded = skill.casefold()
            if folded in seen:
                continue
            seen.add(folded)
            result.append(skill)

    return result


def extract_skill_hints(
    text: str,
    *,
    role_type: str | None = None,
    limit: int = 12,
) -> list[str]:
    lowered = str(text or "").casefold()
    if not lowered:
        return []

    skill_bank = get_skill_bank_for_role_type(role_type)
    matches: list[str] = []

    for skill in skill_bank:
        if skill.casefold() in lowered:
            matches.append(skill)

    deduped: list[str] = []
    seen: set[str] = set()
    for skill in matches:
        folded = skill.casefold()
        if folded in seen:
            continue
        seen.add(folded)
        deduped.append(skill)

    return deduped[:limit]