"""Constants used by job normalization, parsing, and Layer 1 ingestion."""

from __future__ import annotations

COMMON_REQUIRED_SKILLS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node",
    "node.js",
    "fastapi",
    "django",
    "flask",
    "sql",
    "postgresql",
    "mysql",
    "mongodb",
    "redis",
    "aws",
    "azure",
    "gcp",
    "docker",
    "kubernetes",
    "terraform",
    "git",
    "github",
    "ci/cd",
    "jenkins",
    "linux",
    "rest",
    "graphql",
    "html",
    "css",
    "sass",
    "tailwind",
    "figma",
    "agile",
    "scrum",
    "pandas",
    "numpy",
    "pytorch",
    "spark",
    "airflow",
    "tableau",
    "power bi",
    "supabase",
}

COMMON_PREFERRED_MARKERS = {
    "nice to have",
    "preferred",
    "bonus",
    "plus",
    "would be great",
    "good to have",
    "preferred qualifications",
}

COMMON_RESPONSIBILITY_HEADERS = {
    "responsibilities",
    "what you'll do",
    "what you will do",
    "what you’ll do",
    "duties",
    "day-to-day",
    "your impact",
    "in this role you will",
}

COMMON_QUALIFICATION_HEADERS = {
    "qualifications",
    "requirements",
    "basic qualifications",
    "minimum qualifications",
    "what we're looking for",
    "what we are looking for",
    "skills and experience",
    "experience",
}

COMMON_BENEFIT_HEADERS = {
    "benefits",
    "perks",
    "why join us",
    "what we offer",
    "compensation and benefits",
}

REMOTE_KEYWORDS = {
    "remote",
    "work from home",
    "wfh",
    "telework",
    "distributed",
}

HYBRID_KEYWORDS = {
    "hybrid",
}

ONSITE_KEYWORDS = {
    "on-site",
    "onsite",
    "in office",
    "in-office",
}

US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}

US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
}

NON_US_LOCATION_KEYWORDS = {
    "canada",
    "united kingdom",
    "uk",
    "london",
    "germany",
    "berlin",
    "france",
    "paris",
    "india",
    "bengaluru",
    "bangalore",
    "mumbai",
    "delhi",
    "singapore",
    "australia",
    "sydney",
    "melbourne",
    "ireland",
    "dublin",
    "netherlands",
    "amsterdam",
    "poland",
    "warsaw",
    "spain",
    "barcelona",
    "madrid",
    "mexico",
    "brazil",
    "philippines",
}

PROVIDER_SOURCE_PRIORITY = {
    "usajobs": 100,
    "remotive": 90,
    "jsearch": 70,
    "arbeitnow": 60,
    "jobicy": 50,
    "remoteok": 20,
    "greenhouse": 10,
    "mock": 0,
}

URL_IGNORED_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gh_jid",
    "gh_src",
    "ref",
    "refs",
    "source",
    "src",
    "trk",
    "tracking",
}