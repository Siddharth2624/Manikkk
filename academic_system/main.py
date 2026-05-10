"""Main application entry point."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path

from app.infrastructure.config import settings
from app.infrastructure.database import db, init_indexes
from app.domain.exceptions import AuthorizationError, ResourceNotFoundError, ValidationError
from app.adapters.controllers import (
    auth_router,
    admin_router,
    timetable_router,
    attendance_router,
    study_material_router,
    admin_faculty_router,
    faculty_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting Academic Management System...")
    await db.connect()

    # Initialize indexes
    try:
        await init_indexes()
        print("Database indexes initialized.")
    except Exception as e:
        print(f"Warning: Could not initialize indexes: {e}")

    print("Application started successfully!")

    yield

    # Shutdown
    print("Shutting down...")
    await db.disconnect()
    print("Application stopped.")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Scalable Academic Management System with FastAPI + MongoDB",
    lifespan=lifespan
)


# Configure CORS - MUST be before exception handlers to ensure CORS headers on all responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Helper function to add CORS headers to error responses
def get_cors_headers(origin: str | None) -> dict:
    """Get CORS headers for the given origin."""
    if not origin:
        return {}
    # Check if origin is in allowed list
    if origin in settings.cors_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Vary": "Origin"
        }
    return {}


# Exception handlers for custom domain exceptions
@app.exception_handler(AuthorizationError)
async def authorization_error_handler(request, exc: AuthorizationError):
    origin = request.headers.get("origin")
    headers = get_cors_headers(origin)
    return JSONResponse(
        status_code=403,
        content={"detail": exc.message, "code": exc.code, "type": "authorization_error"},
        headers=headers
    )


@app.exception_handler(ResourceNotFoundError)
async def not_found_error_handler(request, exc: ResourceNotFoundError):
    origin = request.headers.get("origin")
    headers = get_cors_headers(origin)
    return JSONResponse(
        status_code=404,
        content={"detail": exc.message, "code": exc.code, "type": "not_found_error"},
        headers=headers
    )


@app.exception_handler(ValidationError)
async def validation_error_handler(request, exc: ValidationError):
    origin = request.headers.get("origin")
    headers = get_cors_headers(origin)
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message, "field": exc.field, "code": exc.code, "type": "validation_error"},
        headers=headers
    )


# Global exception handler for any unexpected errors
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """Handle all unexpected errors with proper response."""
    import traceback
    traceback.print_exc()
    origin = request.headers.get("origin")
    headers = get_cors_headers(origin)
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc) or "Internal server error", "type": "internal_error"},
        headers=headers
    )


# Mount static files for uploads (under /uploads)
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")

# Include routers - each with api/v1 prefix, not nested
app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(timetable_router, prefix=settings.api_prefix)
app.include_router(attendance_router, prefix=settings.api_prefix)
app.include_router(study_material_router, prefix=settings.api_prefix)
app.include_router(admin_faculty_router, prefix=settings.api_prefix)  # Admin: faculty assignment endpoints
app.include_router(faculty_router, prefix=settings.api_prefix)  # Faculty: self-service endpoints


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc",
        "frontend": "Run React dev server: cd frontend && npm run dev",
        "api": settings.api_prefix,
    }

@app.get("/api")
async def api_info():
    """API information endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    db_healthy = await db.ping()
    return {
        "status": "healthy" if db_healthy else "unhealthy",
        "database": "connected" if db_healthy else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False
    )
