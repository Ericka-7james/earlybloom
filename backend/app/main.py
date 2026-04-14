from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.resume import router as resume_router
from app.core.auth_settings import auth_settings

# Temp rm - will add back when tracker is ready
# from app.api.routes.tracker import router as tracker_router


def _build_allowed_origins() -> list[str]:
    origins: list[str] = []

    if auth_settings.frontend_origin:
        origins.append(auth_settings.frontend_origin.strip())

    if auth_settings.cors_origins:
        origins.extend(
            origin.strip()
            for origin in auth_settings.cors_origins.split(",")
            if origin.strip()
        )

    origins.extend(
        [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )

    # dedupe while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for origin in origins:
        if origin not in seen:
            seen.add(origin)
            deduped.append(origin)

    return deduped


app = FastAPI(
    title="EarlyBloom API",
    version="0.1.0",
    description="Backend API for EarlyBloom job ingestion, resume parsing, tracking, and auth.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(jobs_router)
app.include_router(resume_router)
# app.include_router(tracker_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "EarlyBloom API is running."}


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}