from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api.endpoints import imagery

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware Configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API endpoints
app.include_router(
    imagery.router,
    prefix=f"{settings.API_V1_STR}/imagery",
    tags=["imagery"]
)

@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for container probes or status verification."""
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "mode": "production-mvp"
    }

logger.info("FastAPI application loaded successfully.")
