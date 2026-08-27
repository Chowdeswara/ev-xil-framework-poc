"""FastAPI application factory for the EV XiL REST API server.

Creates and configures the FastAPI application with:
  - CORS middleware (permissive for local React dev server on port 5173)
  - API routes from ev_xil.web.routes
  - Startup/shutdown lifecycle logging
  - OpenAPI docs at /docs (Swagger UI)

Usage:
    Run via run_api_server.py at project root, or directly:
        uvicorn ev_xil.web.app:app --host 127.0.0.1 --port 8001 --reload
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ev_xil.web.routes import router

# Configure root logger for the web server
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def _lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager for startup and shutdown events."""
    logger.info("=" * 70)
    logger.info("  [EV XiL] FastAPI Server -- Starting Up")
    logger.info("  Framework: ev-xil v0.1.0")
    logger.info("  Docs:      http://127.0.0.1:8001/docs")
    logger.info("  Health:    http://127.0.0.1:8001/api/health")
    logger.info("=" * 70)
    yield
    logger.info("  [EV XiL] FastAPI Server -- Shutting Down")


def create_app() -> FastAPI:
    """Application factory: creates and configures the FastAPI instance.

    Returns:
        Fully configured FastAPI application ready for uvicorn.
    """
    application = FastAPI(
        title="EV XiL Test Automation API",
        description=(
            "REST API bridging the React telemetry dashboard (ev-xil-ui) "
            "to the EV X-in-the-Loop (XiL) Python test automation framework. "
            "Supports MIL, SIL, HIL, and VIL simulation profiles with ISO 26262 "
            "cross-level equivalence verification."
        ),
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=_lifespan,
    )

    # -----------------------------------------------------------------------
    # CORS Middleware
    # Allow the React Vite dev server (port 5173) and any localhost origin.
    # In production, replace "*" with your specific frontend domain.
    # -----------------------------------------------------------------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://localhost:5175",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8080",
        ],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Include API router
    # -----------------------------------------------------------------------
    application.include_router(router)

    @application.get("/", include_in_schema=False)
    async def root():
        return {
            "message": "EV XiL Test Automation API is running",
            "docs": "http://127.0.0.1:8001/docs",
            "health": "http://127.0.0.1:8001/api/health",
        }

    return application


# Module-level app instance for uvicorn
app = create_app()
