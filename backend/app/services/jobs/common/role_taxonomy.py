from __future__ import annotations

import re

ROLE_PATTERNS: dict[str, list[str]] = {
    "software": [
        r"\bsoftware\b",
        r"\bfrontend\b",
        r"\bback[- ]?end\b",
        r"\bfull[- ]?stack\b",
        r"\bweb developer\b",
        r"\bdeveloper\b",
        r"\bapplication engineer\b",
        r"\bsoftware engineer\b",
        r"\bmobile\b",
        r"\bios\b",
        r"\bandroid\b",
        r"\bqa\b",
        r"\btest automation\b",
    ],
    "it_support": [
        r"\bhelp desk\b",
        r"\bservice desk\b",
        r"\bdesktop support\b",
        r"\btechnical support\b",
        r"\bit support\b",
        r"\bsupport technician\b",
        r"\bsystems administrator\b",
        r"\bnetwork support\b",
        r"\bfield technician\b",
        r"\boperator\b",
    ],
    "data": [
        r"\bdata analyst\b",
        r"\bdata engineer\b",
        r"\bbi analyst\b",
        r"\bbusiness intelligence\b",
        r"\breporting\b",
        r"\banalytics\b",
        r"\bdata science\b",
        r"\bmachine learning\b",
    ],
    "cloud_devops": [
        r"\bdevops\b",
        r"\bsite reliability\b",
        r"\bsre\b",
        r"\bcloud\b",
        r"\binfrastructure\b",
        r"\bplatform engineer\b",
        r"\brelease engineer\b",
    ],
    "security": [
        r"\bsecurity\b",
        r"\bcyber\b",
        r"\bsoc\b",
        r"\biam\b",
        r"\bg rc\b",
        r"\bgovernance risk\b",
        r"\bcompliance\b",
        r"\bsecurity analyst\b",
    ],
    "analyst": [
        r"\banalyst\b",
        r"\bbusiness analyst\b",
        r"\bsystems analyst\b",
        r"\boperations analyst\b",
        r"\btechnical analyst\b",
        r"\bimplementation analyst\b",
    ],
    "ops": [
        r"\boperations\b",
        r"\bcoordinator\b",
        r"\bspecialist\b",
        r"\badministrator\b",
        r"\btechnical operations\b",
        r"\bprogram support\b",
    ],
    "customer_success": [
        r"\bcustomer success\b",
        r"\bcustomer support\b",
        r"\bsupport representative\b",
        r"\bclient support\b",
        r"\bservice representative\b",
    ],
    "product": [
        r"\bproduct\b",
        r"\bproduct analyst\b",
        r"\bproduct operations\b",
        r"\btechnical product\b",
        r"\bimplementation\b",
        r"\bbusiness systems\b",
    ],
}


def infer_role_type_from_text(
    *,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
) -> str:
    text = " ".join(
        part for part in [str(title or ""), str(description or ""), " ".join(tags or [])] if part
    ).casefold()

    for role_type, patterns in ROLE_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            return role_type

    return "unknown"