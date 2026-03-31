from app.api.routes.auth import router as auth_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.resume import router as resume_router

__all__ = ["auth_router", "jobs_router", "resume_router"]