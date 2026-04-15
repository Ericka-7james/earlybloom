from __future__ import annotations

import re
from collections import OrderedDict, defaultdict


CANONICAL_SKILLS: list[str] = [
    # languages
    "Python",
    "Java",
    "JavaScript",
    "TypeScript",
    "SQL",
    "Bash",
    "PowerShell",
    "HTML",
    "CSS",
    "C#",
    "C++",
    "Go",
    "Rust",

    # frameworks / libraries
    "React",
    "Node.js",
    "FastAPI",
    "Django",
    "Flask",
    ".NET",
    "Spring",
    "Express",
    "Pandas",
    "NumPy",

    # cloud / infra
    "AWS",
    "Azure",
    "GCP",
    "Docker",
    "Kubernetes",
    "Terraform",
    "Ansible",

    # databases / data platforms
    "PostgreSQL",
    "MySQL",
    "MongoDB",
    "Snowflake",
    "BigQuery",
    "Redshift",
    "Spark",
    "Excel",
    "Tableau",
    "Power BI",

    # dev tools
    "Git",
    "GitHub",
    "GitHub Actions",
    "GitLab CI",
    "Jenkins",
    "Linux",
    "REST APIs",
    "GraphQL",
    "CI/CD",
    "Testing",
    "Pytest",
    "Jest",

    # IT / support / identity / business tools
    "Jira",
    "Confluence",
    "ServiceNow",
    "Salesforce",
    "Active Directory",
    "Azure AD",
    "Microsoft 365",
    "Office 365",
    "Intune",
    "Jamf",
    "Okta",
    "SSO",
    "VPN",
    "DNS",
    "DHCP",
    "TCP/IP",
    "Troubleshooting",

    # security
    "IAM",
    "SIEM",
    "Splunk",
    "Microsoft Sentinel",
    "Incident Response",
    "Vulnerability Management",
    "Risk Assessment",
    "NIST",
    "Zero Trust",

    # certifications
    "Security+",
    "AWS Certified Cloud Practitioner",
    "AWS Certified Solutions Architect",
    "CompTIA A+",
    "Network+",

    # soft skills
    "Communication",
    "Stakeholder Management",
    "Customer Service",
    "Problem Solving",
    "Collaboration",
    "Agile",
    "Scrum",
]


SKILL_ALIASES: dict[str, str] = {
    # languages
    "python": "Python",
    "java": "Java",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "typescript": "TypeScript",
    "ts": "TypeScript",
    "sql": "SQL",
    "bash": "Bash",
    "shell": "Bash",
    "shell scripting": "Bash",
    "powershell": "PowerShell",
    "html": "HTML",
    "css": "CSS",
    "c#": "C#",
    "csharp": "C#",
    "c++": "C++",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",

    # frameworks / libraries
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "node": "Node.js",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    ".net": ".NET",
    "dotnet": ".NET",
    "asp.net": ".NET",
    "spring": "Spring",
    "express": "Express",
    "pandas": "Pandas",
    "numpy": "NumPy",

    # cloud / infra
    "amazon web services": "AWS",
    "aws": "AWS",
    "microsoft azure": "Azure",
    "azure": "Azure",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "gcp": "GCP",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "terraform": "Terraform",
    "ansible": "Ansible",

    # databases / data
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "mongo": "MongoDB",
    "snowflake": "Snowflake",
    "bigquery": "BigQuery",
    "redshift": "Redshift",
    "spark": "Spark",
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "excel": "Excel",
    "tableau": "Tableau",
    "power bi": "Power BI",
    "powerbi": "Power BI",

    # dev tools
    "git": "Git",
    "github": "GitHub",
    "github actions": "GitHub Actions",
    "gitlab ci": "GitLab CI",
    "jenkins": "Jenkins",
    "linux": "Linux",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "api": "REST APIs",
    "apis": "REST APIs",
    "graphql": "GraphQL",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "testing": "Testing",
    "pytest": "Pytest",
    "jest": "Jest",

    # IT / support / business tools
    "jira": "Jira",
    "confluence": "Confluence",
    "servicenow": "ServiceNow",
    "service now": "ServiceNow",
    "salesforce": "Salesforce",
    "active directory": "Active Directory",
    "azure ad": "Azure AD",
    "entra id": "Azure AD",
    "office 365": "Office 365",
    "microsoft 365": "Microsoft 365",
    "o365": "Office 365",
    "intune": "Intune",
    "jamf": "Jamf",
    "okta": "Okta",
    "sso": "SSO",
    "single sign-on": "SSO",
    "vpn": "VPN",
    "dns": "DNS",
    "dhcp": "DHCP",
    "tcp/ip": "TCP/IP",
    "tcpip": "TCP/IP",
    "troubleshooting": "Troubleshooting",

    # security
    "iam": "IAM",
    "identity and access management": "IAM",
    "identity access management": "IAM",
    "siem": "SIEM",
    "splunk": "Splunk",
    "sentinel": "Microsoft Sentinel",
    "microsoft sentinel": "Microsoft Sentinel",
    "incident response": "Incident Response",
    "vulnerability management": "Vulnerability Management",
    "risk assessment": "Risk Assessment",
    "nist": "NIST",
    "zero trust": "Zero Trust",

    # certifications
    "security+": "Security+",
    "comptia security+": "Security+",
    "aws certified cloud practitioner": "AWS Certified Cloud Practitioner",
    "aws cloud practitioner": "AWS Certified Cloud Practitioner",
    "aws certified solutions architect": "AWS Certified Solutions Architect",
    "solutions architect associate": "AWS Certified Solutions Architect",
    "comptia a+": "CompTIA A+",
    "a+": "CompTIA A+",
    "network+": "Network+",
    "comptia network+": "Network+",

    # soft skills
    "communication": "Communication",
    "stakeholder management": "Stakeholder Management",
    "customer service": "Customer Service",
    "problem solving": "Problem Solving",
    "collaboration": "Collaboration",
    "agile": "Agile",
    "scrum": "Scrum",
}


SKILL_CATEGORIES: dict[str, str] = {
    # languages
    "Python": "languages",
    "Java": "languages",
    "JavaScript": "languages",
    "TypeScript": "languages",
    "SQL": "languages",
    "Bash": "languages",
    "PowerShell": "languages",
    "HTML": "languages",
    "CSS": "languages",
    "C#": "languages",
    "C++": "languages",
    "Go": "languages",
    "Rust": "languages",

    # frameworks / libraries
    "React": "frameworks",
    "Node.js": "frameworks",
    "FastAPI": "frameworks",
    "Django": "frameworks",
    "Flask": "frameworks",
    ".NET": "frameworks",
    "Spring": "frameworks",
    "Express": "frameworks",
    "Pandas": "data_tools",
    "NumPy": "data_tools",

    # cloud / infra
    "AWS": "cloud",
    "Azure": "cloud",
    "GCP": "cloud",
    "Docker": "dev_tools",
    "Kubernetes": "dev_tools",
    "Terraform": "dev_tools",
    "Ansible": "dev_tools",

    # databases / data
    "PostgreSQL": "databases",
    "MySQL": "databases",
    "MongoDB": "databases",
    "Snowflake": "databases",
    "BigQuery": "databases",
    "Redshift": "databases",
    "Spark": "data_tools",
    "Excel": "data_tools",
    "Tableau": "data_tools",
    "Power BI": "data_tools",

    # dev tools
    "Git": "dev_tools",
    "GitHub": "dev_tools",
    "GitHub Actions": "dev_tools",
    "GitLab CI": "dev_tools",
    "Jenkins": "dev_tools",
    "Linux": "dev_tools",
    "REST APIs": "dev_tools",
    "GraphQL": "dev_tools",
    "CI/CD": "dev_tools",
    "Testing": "dev_tools",
    "Pytest": "dev_tools",
    "Jest": "dev_tools",

    # IT / support / business tools
    "Jira": "it_tools",
    "Confluence": "it_tools",
    "ServiceNow": "it_tools",
    "Salesforce": "crm_tools",
    "Active Directory": "it_tools",
    "Azure AD": "it_tools",
    "Microsoft 365": "it_tools",
    "Office 365": "it_tools",
    "Intune": "it_tools",
    "Jamf": "it_tools",
    "Okta": "it_tools",
    "SSO": "it_tools",
    "VPN": "it_tools",
    "DNS": "it_tools",
    "DHCP": "it_tools",
    "TCP/IP": "it_tools",
    "Troubleshooting": "it_tools",

    # security
    "IAM": "security",
    "SIEM": "security",
    "Splunk": "security",
    "Microsoft Sentinel": "security",
    "Incident Response": "security",
    "Vulnerability Management": "security",
    "Risk Assessment": "security",
    "NIST": "security",
    "Zero Trust": "security",

    # certifications
    "Security+": "certifications",
    "AWS Certified Cloud Practitioner": "certifications",
    "AWS Certified Solutions Architect": "certifications",
    "CompTIA A+": "certifications",
    "Network+": "certifications",

    # soft skills
    "Communication": "soft_skills",
    "Stakeholder Management": "soft_skills",
    "Customer Service": "soft_skills",
    "Problem Solving": "soft_skills",
    "Collaboration": "soft_skills",
    "Agile": "soft_skills",
    "Scrum": "soft_skills",
}


def dedupe_preserve_order(items: list[str]) -> list[str]:
    ordered: OrderedDict[str, str] = OrderedDict()

    for item in items:
        cleaned = str(item or "").strip()
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key not in ordered:
            ordered[key] = cleaned

    return list(ordered.values())


def normalize_skill(term: str) -> str | None:
    cleaned = str(term or "").strip()
    if not cleaned:
        return None

    folded = cleaned.casefold()
    canonical = SKILL_ALIASES.get(folded)
    if canonical:
        return canonical

    for canonical_skill in CANONICAL_SKILLS:
        if folded == canonical_skill.casefold():
            return canonical_skill

    return None


def _build_skill_patterns() -> list[tuple[str, re.Pattern[str]]]:
    searchable_terms = set(CANONICAL_SKILLS) | set(SKILL_ALIASES.keys())
    patterns: list[tuple[str, re.Pattern[str]]] = []

    for raw_term in searchable_terms:
        canonical = normalize_skill(raw_term)
        if not canonical:
            continue

        escaped = re.escape(raw_term)

        if re.fullmatch(r"[a-z0-9.+#/ -]+", raw_term.casefold()):
            pattern = re.compile(rf"(?<!\w){escaped}(?!\w)", re.IGNORECASE)
        else:
            pattern = re.compile(escaped, re.IGNORECASE)

        patterns.append((canonical, pattern))

    return patterns


SKILL_PATTERNS = _build_skill_patterns()


def extract_skills_from_text(text: str) -> list[str]:
    body = str(text or "")
    if not body.strip():
        return []

    matches: list[tuple[int, int, str]] = []

    for canonical, pattern in SKILL_PATTERNS:
        for match in pattern.finditer(body):
            matches.append((match.start(), match.end(), canonical))

    if not matches:
        return []

    # Prefer earlier matches, and for the same start position prefer longer spans.
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2]))

    filtered: list[tuple[int, int, str]] = []
    for start, end, canonical in matches:
        is_contained = any(
            existing_start <= start and end <= existing_end
            for existing_start, existing_end, _ in filtered
        )
        if is_contained:
            continue
        filtered.append((start, end, canonical))

    ordered_skills = [skill for _, _, skill in filtered]
    return dedupe_preserve_order(ordered_skills)

def categorize_skills(skills: list[str]) -> dict[str, list[str]]:
    categorized: defaultdict[str, list[str]] = defaultdict(list)

    for skill in skills:
        canonical = normalize_skill(skill)
        if not canonical:
            continue

        category = SKILL_CATEGORIES.get(canonical, "other")
        categorized[category].append(canonical)

    result: dict[str, list[str]] = {}
    for category, values in categorized.items():
        result[category] = dedupe_preserve_order(values)

    return dict(result)