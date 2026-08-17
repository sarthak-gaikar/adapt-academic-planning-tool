"""
ADAPT — FastAPI Application Entry Point

Configures middleware, exception handlers, and mounts all API routers.
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.core.exceptions import ADAPTError
from app.core.logging import get_logger, setup_logging

settings = get_settings()
logger = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global logger
    logger = setup_logging()
    logger.info(f"Starting {settings.app_name} ({settings.app_env})")

    # Ensure required directories exist
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path("./exports").mkdir(parents=True, exist_ok=True)

    # Initialize database in development mode
    if settings.app_env == "development":
        try:
            from app.database import init_db
            await init_db()
            logger.info("Database initialized (dev mode)")
        except Exception as e:
            logger.warning(f"Could not auto-create tables: {e}")

    # Initialize task manager
    from app.core.background_tasks import get_task_manager
    get_task_manager()

    yield

    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    """Application factory."""
    app = FastAPI(
        title=settings.app_name,
        description="AI-Driven Academic Planning & Assessment Tool (ADAPT) — End-to-End OBE Platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Exception Handlers ----
    @app.exception_handler(ADAPTError)
    async def adapt_error_handler(request: Request, exc: ADAPTError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        error_logger = get_logger("error")
        error_logger.exception(f"Unhandled error: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": {"type": type(exc).__name__} if settings.debug else {},
            },
        )

    # ---- Register Routers ----
    from app.api.aap import router as aap_router
    from app.api.agent import router as agent_router
    from app.api.answer_keys import router as answer_keys_router
    from app.api.assignments import router as assignments_router
    from app.api.auth import router as auth_router
    from app.api.bloom import router as bloom_router
    from app.api.blueprints import router as blueprints_router
    from app.api.co_po import router as co_po_router
    from app.api.course_outcomes import router as course_outcomes_router
    from app.api.documents import router as documents_router
    from app.api.exams import router as exams_router
    from app.api.export import router as export_router
    from app.api.program_outcomes import router as program_outcomes_router
    from app.api.questions import router as questions_router
    from app.api.subjects import router as subjects_router
    from app.api.syllabus import router as syllabus_router
    from app.api.tasks import router as tasks_router

    app.include_router(auth_router)
    app.include_router(subjects_router)
    app.include_router(documents_router)
    app.include_router(syllabus_router)
    app.include_router(course_outcomes_router)
    app.include_router(program_outcomes_router)
    app.include_router(co_po_router)
    app.include_router(aap_router)
    app.include_router(questions_router)
    app.include_router(assignments_router)
    app.include_router(blueprints_router)
    app.include_router(exams_router)
    app.include_router(answer_keys_router)
    app.include_router(bloom_router)
    app.include_router(export_router)
    app.include_router(agent_router)
    app.include_router(tasks_router)

    # ---- Health Check ----
    @app.get("/api/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "env": settings.app_env,
        }

    return app


app = create_app()
