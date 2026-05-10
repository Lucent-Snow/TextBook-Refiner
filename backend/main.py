"""FastAPI application entry point."""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import ask, build, chat, decisions, graph, materials, projects, report
from backend.core.config import settings
from backend.core.storage import StoragePathError

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="TextBook Refiner",
    description="Knowledge Integration Agent — build, integrate, and compress textbook knowledge graphs",
    version="0.1.0",
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = (time.monotonic() - start) * 1000
    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round(duration_ms, 1),
        },
    )
    return response


# Global error handler
@app.exception_handler(StoragePathError)
async def storage_path_error_handler(request: Request, exc: StoragePathError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": "invalid_storage_id",
                "message": str(exc),
            }
        },
    )


@app.exception_handler(Exception)
async def global_error_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled exception",
        extra={
            "method": request.method,
            "path": request.url.path,
            "error_type": type(exc).__name__,
        },
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "An internal error occurred",
            }
        },
    )


# Register routers
app.include_router(projects.router)
app.include_router(materials.router)
app.include_router(build.router)
app.include_router(graph.router)
app.include_router(decisions.router)
app.include_router(chat.router)
app.include_router(ask.router)
app.include_router(report.router)


@app.on_event("startup")
async def on_startup():
    """Seed demo project with pre-loaded textbooks on first run."""
    try:
        from backend.seed_data import seed_demo_project

        result = seed_demo_project()
        if result:
            logger.info(
                "Demo project seeded: %s (%s)",
                result["name"],
                result["id"],
            )
    except Exception:
        logger.exception("Failed to seed demo project")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )
