from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime
from typing import Dict, List, Sequence, Tuple

from app.schemas.resume import (
    ParsedResume,
    ResumeBasics,
    ResumeEducation,
    ResumeExperience,
    ResumeLink,
    ResumeLocation,
    ResumeMeta,
    ResumeProject,
    ResumeSkills,
    ResumeSummary,
)

from app.services.jobs.common.skills_taxonomy import (
    extract_skills_from_text,
    categorize_skills,
)

EMAIL_REGEX = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_REGEX = re.compile(
    r"(?:(?:\+?1[\s.-]*)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]*\d{4})"
)
URL_REGEX = re.compile(
    r"(https?://[^\s]+|www\.[^\s]+|linkedin\.com/[^\s]+|github\.com/[^\s]+|gitlab\.com/[^\s]+)",
    re.IGNORECASE,
)
DATE_RANGE_REGEX = re.compile(
    r"(?P<start>(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{4}|\d{4})"
    r"\s*(?:-|–|—|to)\s*"
    r"(?P<end>present|current|now|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+\d{4}|\d{4})",
    re.IGNORECASE,
)

SECTION_PATTERNS: Dict[str, re.Pattern[str]] = {
    "education": re.compile(r"^\s*(education|academic background)\s*$", re.IGNORECASE),
    "experience": re.compile(
        r"^\s*(experience|work experience|professional experience|employment)\s*$",
        re.IGNORECASE,
    ),
    "projects": re.compile(r"^\s*(projects|project experience)\s*$", re.IGNORECASE),
    "skills": re.compile(r"^\s*(skills|technical skills|technologies)\s*$", re.IGNORECASE),
}

SECTION_HEADING_CANONICAL = [
    "professional summary",
    "summary",
    "education",
    "experience",
    "work experience",
    "professional experience",
    "employment",
    "projects",
    "project experience",
    "skills",
    "technical skills",
    "technologies",
]

HEADER_SPLIT_REGEX = re.compile(r"\s+[•|]\s+")

DEGREE_HINTS = [
    "b.s",
    "bs",
    "bachelor",
    "b.a",
    "ba",
    "master",
    "m.s",
    "ms",
    "phd",
    "computer science",
    "software engineering",
    "information systems",
    "cybersecurity",
    "engineering",
]

ROLE_SIGNAL_KEYWORDS = {
    "frontend": {"react", "javascript", "typescript", "css", "frontend", "ui"},
    "backend": {"python", "fastapi", "java", "sql", "backend", "api"},
    "full_stack": {"react", "javascript", "typescript", "python", "sql", "api"},
    "data": {"python", "sql", "pandas", "numpy", "data"},
    "product": {"product", "analytics", "experimentation"},
}

SKILL_ALIASES = {
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "typescript": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "react": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "py": "python",
    "python": "python",
    "postgres": "postgresql",
    "postgresql": "postgresql",
    "aws cloud": "aws",
    "amazon web services": "aws",
    "aws": "aws",
    "html5": "html",
    "css3": "css",
    "fast api": "fastapi",
    "fastapi": "fastapi",
    "rest api": "rest",
    "restful api": "rest",
    "sql": "sql",
    "docker": "docker",
    "git": "git",
    "github": "github",
    "pandas": "pandas",
    "numpy": "numpy",
    "java": "java",
    "spring boot": "spring boot",
    "supabase": "supabase",
    "figma": "figma",
    "terraform": "terraform",
    "jenkins": "jenkins",
    "powerbi": "power bi",
    "power bi": "power bi",
    "servicenow": "servicenow",
}

CANONICAL_SKILL_LABELS = {
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "node.js": "Node.js",
    "python": "Python",
    "postgresql": "PostgreSQL",
    "aws": "AWS",
    "html": "HTML",
    "css": "CSS",
    "fastapi": "FastAPI",
    "rest": "REST",
    "sql": "SQL",
    "docker": "Docker",
    "git": "Git",
    "github": "GitHub",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "java": "Java",
    "spring boot": "Spring Boot",
    "supabase": "Supabase",
    "figma": "Figma",
    "terraform": "Terraform",
    "jenkins": "Jenkins",
    "power bi": "Power BI",
    "servicenow": "ServiceNow",
}

KNOWN_SKILLS = sorted(set(SKILL_ALIASES.values()))

CITY_PREFIX_WORDS = {
    "new",
    "los",
    "las",
    "san",
    "saint",
    "st",
    "fort",
    "el",
}


def normalize_whitespace(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def preprocess_resume_text(text: str) -> str:
    text = normalize_whitespace(text)
    text = HEADER_SPLIT_REGEX.sub("\n", text)

    for heading in sorted(SECTION_HEADING_CANONICAL, key=len, reverse=True):
        pattern = re.compile(rf"\s+({re.escape(heading)})\b", re.IGNORECASE)
        text = pattern.sub(r"\n\1", text)

    for heading in sorted(SECTION_HEADING_CANONICAL, key=len, reverse=True):
        pattern = re.compile(rf"\b({re.escape(heading)})\s+", re.IGNORECASE)
        text = pattern.sub(r"\1\n", text)

    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)

    return normalize_whitespace(text)


def split_lines(text: str) -> List[str]:
    return [line.strip() for line in normalize_whitespace(text).split("\n") if line.strip()]


def extract_sections(lines: Sequence[str]) -> Dict[str, List[str]]:
    sections: Dict[str, List[str]] = {
        "header": [],
        "education": [],
        "experience": [],
        "projects": [],
        "skills": [],
        "other": [],
    }

    current_section = "header"

    for line in lines:
        matched_section = None
        for section_name, pattern in SECTION_PATTERNS.items():
            if pattern.match(line):
                matched_section = section_name
                break

        if matched_section:
            current_section = matched_section
            continue

        sections[current_section].append(line)

    return sections


def dedupe_preserve_order(values: Sequence[str]) -> List[str]:
    seen = set()
    result: List[str] = []

    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        if normalized.lower() in seen:
            continue
        seen.add(normalized.lower())
        result.append(normalized)

    return result


def normalize_skill_token(token: str) -> str | None:
    cleaned = re.sub(r"[^a-zA-Z0-9.+# ]", " ", token).strip().lower()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        return None

    if cleaned in SKILL_ALIASES:
        return SKILL_ALIASES[cleaned]

    if cleaned in KNOWN_SKILLS:
        return cleaned

    return None


def canonicalize_skill_label(skill: str) -> str:
    normalized = normalize_skill_token(skill) or skill.strip().lower()
    return CANONICAL_SKILL_LABELS.get(normalized, skill.strip())


def _extract_skills_in_order(text: str) -> List[str]:
    if not text:
        return []

    ordered_matches: List[tuple[int, str]] = []

    for alias, canonical in SKILL_ALIASES.items():
        pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", re.IGNORECASE)
        for match in pattern.finditer(text):
            ordered_matches.append((match.start(), canonical))

    ordered_matches.sort(key=lambda item: item[0])

    return dedupe_preserve_order(
        canonicalize_skill_label(skill_name)
        for _, skill_name in ordered_matches
    )


def _skill_present_in_text(skill: str, text: str) -> bool:
    if not skill or not text:
        return False

    canonical = normalize_skill_token(skill) or skill.strip().lower()
    alias_candidates = {canonical}

    for alias, alias_canonical in SKILL_ALIASES.items():
        if alias_canonical == canonical:
            alias_candidates.add(alias)

    for candidate in alias_candidates:
        pattern = re.compile(
            rf"(?<![A-Za-z0-9]){re.escape(candidate)}(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        if pattern.search(text):
            return True

    return False


def extract_skills(raw_text: str, skill_lines: Sequence[str]) -> ResumeSkills:
    focused_text = "\n".join(skill_lines) if skill_lines else ""

    sanitized_raw_text = URL_REGEX.sub(" ", raw_text)
    sanitized_focused_text = URL_REGEX.sub(" ", focused_text)

    merged_text = f"{sanitized_focused_text}\n{sanitized_raw_text}".strip()

    taxonomy_skills = [
        canonicalize_skill_label(skill)
        for skill in extract_skills_from_text(merged_text)
    ]
    ordered_line_skills = _extract_skills_in_order(sanitized_focused_text)
    ordered_raw_skills = _extract_skills_in_order(sanitized_raw_text)

    normalized = dedupe_preserve_order(
        [*ordered_line_skills, *ordered_raw_skills, *taxonomy_skills]
    )
    raw = list(normalized)
    categorized = categorize_skills(normalized)

    return ResumeSkills(
        raw=raw,
        normalized=normalized,
        categorized=categorized,
    )

def extract_email(text: str) -> str | None:
    match = EMAIL_REGEX.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> str | None:
    match = PHONE_REGEX.search(text)
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(0)).strip()


def extract_links(text: str) -> List[ResumeLink]:
    links: List[ResumeLink] = []

    for url in dedupe_preserve_order(URL_REGEX.findall(text)):
        lowered = url.lower()
        label = "Website"

        if "linkedin" in lowered:
            label = "LinkedIn"
        elif "github" in lowered:
            label = "GitHub"
        elif "portfolio" in lowered:
            label = "Portfolio"

        normalized_url = url if url.startswith("http") else f"https://{url}"
        links.append(ResumeLink(label=label, url=normalized_url))

    return links


def infer_name(header_lines: Sequence[str]) -> str | None:
    if not header_lines:
        return None

    blocked_phrases = {
        "professional summary",
        "summary",
        "experience",
        "skills",
        "education",
        "projects",
    }

    location_pattern = re.compile(r"\b([A-Z][a-zA-Z]+),\s*([A-Z]{2})\b$")

    for line in header_lines[:5]:
        candidate = line.strip()
        if not candidate:
            continue

        candidate = EMAIL_REGEX.sub("", candidate)
        candidate = PHONE_REGEX.sub("", candidate)
        candidate = URL_REGEX.sub("", candidate)
        candidate = HEADER_SPLIT_REGEX.sub(" ", candidate)
        candidate = re.sub(r"\s+", " ", candidate).strip(" ,|-•")

        lowered = candidate.lower()
        if lowered in blocked_phrases:
            continue

        if not candidate or re.search(r"\d", candidate):
            continue

        location_match = location_pattern.search(candidate)
        if location_match:
            city_start = location_match.start()
            prefix = candidate[:city_start].strip(" ,|-•")
            if prefix:
                candidate = prefix

        words = [w for w in candidate.split() if w]

        if 2 <= len(words) <= 4 and all(
            re.fullmatch(r"[A-Z][a-zA-Z'’-]*", word) for word in words
        ):
            return " ".join(words)

    return None


def normalize_city_from_trailing_words(words: Sequence[str]) -> str | None:
    cleaned = [word.strip() for word in words if word.strip()]
    if not cleaned:
        return None

    if len(cleaned) == 1:
        return cleaned[0]

    if len(cleaned) >= 2 and cleaned[-2].lower() in CITY_PREFIX_WORDS:
        return f"{cleaned[-2]} {cleaned[-1]}"

    return cleaned[-1]


def infer_location(header_lines: Sequence[str]) -> ResumeLocation:
    state_suffix_pattern = re.compile(r"\b([A-Z][a-zA-Z\s]+),\s*([A-Z]{2})\b$")

    for line in header_lines[:5]:
        cleaned = EMAIL_REGEX.sub("", line)
        cleaned = PHONE_REGEX.sub("", cleaned)
        cleaned = URL_REGEX.sub("", cleaned)
        cleaned = HEADER_SPLIT_REGEX.sub(" ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,|-•")

        if not cleaned:
            continue

        match = state_suffix_pattern.search(cleaned)
        if not match:
            continue

        left_side = match.group(1).strip()
        region = match.group(2).strip()

        words = [word for word in left_side.split() if word]
        if not words:
            continue

        city = normalize_city_from_trailing_words(words)
        if not city:
            continue

        return ResumeLocation(
            raw=f"{city}, {region}",
            city=city,
            region=region,
            country="US",
        )

    return ResumeLocation()


def parse_date_range(line: str) -> Tuple[str | None, str | None, bool]:
    match = DATE_RANGE_REGEX.search(line)
    if not match:
        return None, None, False

    start = normalize_date_token(match.group("start"))
    end_raw = match.group("end")
    is_current = end_raw.lower() in {"present", "current", "now"}
    end = None if is_current else normalize_date_token(end_raw)

    return start, end, is_current


def normalize_date_token(token: str) -> str | None:
    token = token.strip().lower().replace(".", "")
    month_map = {
        "jan": "01",
        "january": "01",
        "feb": "02",
        "february": "02",
        "mar": "03",
        "march": "03",
        "apr": "04",
        "april": "04",
        "may": "05",
        "jun": "06",
        "june": "06",
        "jul": "07",
        "july": "07",
        "aug": "08",
        "august": "08",
        "sep": "09",
        "sept": "09",
        "september": "09",
        "oct": "10",
        "october": "10",
        "nov": "11",
        "november": "11",
        "dec": "12",
        "december": "12",
    }

    if re.fullmatch(r"\d{4}", token):
        return token

    parts = token.split()
    if len(parts) == 2 and parts[0] in month_map and re.fullmatch(r"\d{4}", parts[1]):
        return f"{parts[1]}-{month_map[parts[0]]}"

    return None


def parse_education(section_lines: Sequence[str]) -> List[ResumeEducation]:
    items: List[ResumeEducation] = []
    chunks = chunk_section(section_lines)

    for chunk in chunks:
        text = " ".join(chunk)
        if not any(hint in text.lower() for hint in DEGREE_HINTS):
            continue

        school = chunk[0] if chunk else None
        degree = None
        field_of_study = None
        start_date = None
        end_date = None
        is_current = False

        for line in chunk:
            lowered = line.lower()
            if any(hint in lowered for hint in DEGREE_HINTS):
                degree = degree or line

            parsed_start, parsed_end, parsed_current = parse_date_range(line)
            if parsed_start or parsed_end or parsed_current:
                start_date = start_date or parsed_start
                end_date = parsed_end if parsed_end else end_date
                is_current = is_current or parsed_current

            if "computer science" in lowered:
                field_of_study = "Computer Science"
            elif "software engineering" in lowered:
                field_of_study = "Software Engineering"
            elif "cybersecurity" in lowered:
                field_of_study = "Cybersecurity"
            elif "information systems" in lowered:
                field_of_study = "Information Systems"

        items.append(
            ResumeEducation(
                school=school,
                degree=degree,
                field_of_study=field_of_study,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
            )
        )

    return items[:5]


def parse_experience(
    section_lines: Sequence[str],
    normalized_skills: Sequence[str],
) -> List[ResumeExperience]:
    items: List[ResumeExperience] = []
    chunks = chunk_section(section_lines)

    for chunk in chunks:
        if not chunk:
            continue

        first_line = chunk[0]
        if len(first_line) > 140:
            continue

        company = None
        role = None
        start_date = None
        end_date = None
        is_current = False
        bullet_points: List[str] = []

        if "|" in first_line:
            parts = [part.strip() for part in first_line.split("|") if part.strip()]
            role = parts[0] if parts else None
            company = parts[1] if len(parts) > 1 else None
        elif " at " in first_line.lower():
            role_part, company_part = re.split(
                r"\bat\b",
                first_line,
                maxsplit=1,
                flags=re.IGNORECASE,
            )
            role = role_part.strip() or None
            company = company_part.strip() or None
        else:
            role = first_line

        for line in chunk[1:]:
            parsed_start, parsed_end, parsed_current = parse_date_range(line)
            if parsed_start or parsed_end or parsed_current:
                start_date = start_date or parsed_start
                end_date = parsed_end if parsed_end else end_date
                is_current = is_current or parsed_current
                continue

            if line.startswith(("-", "•", "*")):
                bullet_points.append(clean_bullet(line))
            elif len(line) <= 120 and company is None and not re.search(r"\d", line):
                company = line
            else:
                bullet_points.append(clean_bullet(line))

        bullet_points = dedupe_preserve_order(bullet_points)
        bullet_text = "\n".join(bullet_points)

        matched_skills = [
            canonicalize_skill_label(skill)
            for skill in normalized_skills
            if _skill_present_in_text(skill, bullet_text)
        ]

        if role or company or bullet_points:
            items.append(
                ResumeExperience(
                    company=company,
                    role=role,
                    start_date=start_date,
                    end_date=end_date,
                    is_current=is_current,
                    bullet_points=bullet_points[:10],
                    normalized_skills=dedupe_preserve_order(matched_skills),
                )
            )

    return items[:10]


def parse_projects(
    section_lines: Sequence[str],
    normalized_skills: Sequence[str],
) -> List[ResumeProject]:
    items: List[ResumeProject] = []
    chunks = chunk_section(section_lines)

    for chunk in chunks:
        if not chunk:
            continue

        title = chunk[0]
        description_lines = [clean_bullet(line) for line in chunk[1:]]
        description = " ".join(description_lines).strip() or None
        searchable_text = f"{title}\n{description or ''}"

        tech_stack = [
            canonicalize_skill_label(skill)
            for skill in normalized_skills
            if _skill_present_in_text(skill, searchable_text)
        ]

        links = extract_links(" ".join(chunk))

        items.append(
            ResumeProject(
                title=title,
                description=description,
                tech_stack=dedupe_preserve_order(tech_stack),
                links=links,
            )
        )

    return items[:10]


def chunk_section(lines: Sequence[str]) -> List[List[str]]:
    chunks: List[List[str]] = []
    current_chunk: List[str] = []

    for line in lines:
        is_heading_like = (
            len(line) <= 90
            and not line.startswith(("-", "•", "*"))
            and line == line.title()
            and not DATE_RANGE_REGEX.search(line)
        )

        is_new_chunk = (
            not current_chunk
            or SECTION_PATTERNS["education"].match(line)
            or SECTION_PATTERNS["experience"].match(line)
            or SECTION_PATTERNS["projects"].match(line)
            or SECTION_PATTERNS["skills"].match(line)
        )

        if current_chunk and is_heading_like:
            chunks.append(current_chunk)
            current_chunk = [line]
            continue

        if is_new_chunk:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = [line]
        else:
            current_chunk.append(line)

    if current_chunk:
        chunks.append(current_chunk)

    return [chunk for chunk in chunks if any(item.strip() for item in chunk)]


def clean_bullet(line: str) -> str:
    line = line.strip()
    line = re.sub(r"^[-•*]\s*", "", line)
    return line.strip()


def infer_years_experience(experience: Sequence[ResumeExperience]) -> int:
    total_years = 0

    for item in experience:
        start_year = extract_year(item.start_date)
        end_year = datetime.now(UTC).year if item.is_current else extract_year(item.end_date)

        if start_year and end_year and end_year >= start_year:
            total_years += max(0, end_year - start_year)

    return min(total_years, 50)


def infer_years_experience_from_text(raw_text: str) -> int | None:
    patterns = [
        re.compile(r"\b(\d{1,2})\+?\s+years?\s+of\s+experience\b", re.IGNORECASE),
        re.compile(r"\b(\d{1,2})\+?\s+years?\s+experience\b", re.IGNORECASE),
    ]

    matches: List[int] = []

    for pattern in patterns:
        for match in pattern.finditer(raw_text):
            try:
                matches.append(int(match.group(1)))
            except (TypeError, ValueError):
                continue

    if not matches:
        return None

    return min(max(matches), 50)


def extract_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\b(\d{4})\b", value)
    return int(match.group(1)) if match else None


def infer_primary_role_signals(normalized_skills: Sequence[str]) -> List[str]:
    skill_set = {normalize_skill_token(skill) or skill.lower() for skill in normalized_skills}
    matched_roles: List[str] = []

    for role_name, keywords in ROLE_SIGNAL_KEYWORDS.items():
        if skill_set.intersection(keywords):
            matched_roles.append(role_name)

    if not matched_roles:
        matched_roles.append("general_software")

    return matched_roles


def compute_confidence(parsed_resume: ParsedResume) -> float:
    score = 0.0

    if parsed_resume.basics.name:
        score += 0.15
    if parsed_resume.basics.email:
        score += 0.15
    if parsed_resume.basics.phone:
        score += 0.10
    if parsed_resume.education:
        score += 0.15
    if parsed_resume.experience:
        score += 0.20
    if parsed_resume.projects:
        score += 0.10

    skill_count = len(parsed_resume.skills.normalized)

    if skill_count >= 1:
        score += 0.15
    if skill_count >= 5:
        score += 0.03
    if skill_count >= 10:
        score += 0.02

    return round(min(score, 1.0), 2)


def parse_resume_text(
    raw_text: str,
    *,
    file_type: str = "application/pdf",
    extraction_method: str = "text",
) -> tuple[dict, List[str]]:
    cleaned_text = preprocess_resume_text(raw_text)
    lines = split_lines(cleaned_text)
    sections = extract_sections(lines)

    warnings: List[str] = []

    basics = ResumeBasics(
        name=infer_name(sections["header"]),
        email=extract_email(cleaned_text),
        phone=extract_phone(cleaned_text),
        location=infer_location(sections["header"]),
        links=extract_links(cleaned_text),
    )

    skills = extract_skills(cleaned_text, sections["skills"])
    education = parse_education(sections["education"])
    experience = parse_experience(sections["experience"], skills.normalized)
    projects = parse_projects(sections["projects"], skills.normalized)

    years_experience = infer_years_experience(experience)
    if years_experience == 0:
        fallback_years = infer_years_experience_from_text(cleaned_text)
        if fallback_years is not None:
            years_experience = fallback_years

    top_skill_keywords = [skill for skill, _ in Counter(skills.normalized).most_common(10)]
    primary_role_signals = infer_primary_role_signals(skills.normalized)

    summary = ResumeSummary(
        estimated_years_experience=years_experience,
        seniority="early_career" if years_experience <= 3 else "experienced",
        primary_role_signals=primary_role_signals,
        top_skill_keywords=top_skill_keywords,
    )

    parsed_resume = ParsedResume(
        basics=basics,
        education=education,
        experience=experience,
        projects=projects,
        skills=skills,
        summary=summary,
        meta=ResumeMeta(
            parser_version="v1",
            source_file_type=file_type,
            parsed_at=datetime.now(UTC),
            extraction_method=extraction_method,
            confidence=0.0,
        ),
    )

    parsed_resume.meta.confidence = compute_confidence(parsed_resume)

    if not parsed_resume.basics.name:
        warnings.append("Could not confidently infer candidate name.")
    if not parsed_resume.basics.email:
        warnings.append("Could not find email address.")
    if not parsed_resume.education:
        warnings.append("No education section confidently parsed.")
    if not parsed_resume.skills.normalized:
        warnings.append("No normalized skills detected.")
    if not parsed_resume.experience and not parsed_resume.projects:
        warnings.append("No experience or projects were confidently parsed.")

    return parsed_resume.to_jsonb(), warnings


def build_empty_parsed_resume(file_type: str = "application/pdf") -> dict:
    parsed_resume = ParsedResume(
        meta=ResumeMeta(
            parser_version="v1",
            source_file_type=file_type,
            parsed_at=datetime.now(UTC),
            extraction_method="text",
            confidence=0.0,
        )
    )
    return parsed_resume.to_jsonb()