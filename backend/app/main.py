from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.api import images, projects, analysis, enhancement, teams, players, auth, library
import logging
import time
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request logging and timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")

    response = await call_next(request)

    # Log response time
    process_time = time.time() - start_time
    logger.info(f"Completed in {process_time:.2f}s - Status: {response.status_code}")

    response.headers["X-Process-Time"] = str(process_time)
    return response


# Exception handlers
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to UnFuzz API",
        "version": settings.VERSION,
        "docs": "/api/docs"
    }


# Include routers
app.include_router(
    images.router,
    prefix=f"{settings.API_V1_PREFIX}/images",
    tags=["images"]
)
app.include_router(
    projects.router,
    prefix=f"{settings.API_V1_PREFIX}/projects",
    tags=["projects"]
)
app.include_router(
    analysis.router,
    prefix=f"{settings.API_V1_PREFIX}/analysis",
    tags=["analysis"]
)
app.include_router(
    enhancement.router,
    prefix=f"{settings.API_V1_PREFIX}/enhancement",
    tags=["enhancement"]
)
app.include_router(
    teams.router,
    prefix=settings.API_V1_PREFIX
)
app.include_router(
    players.router,
    prefix=settings.API_V1_PREFIX
)
app.include_router(
    auth.router,
    prefix=settings.API_V1_PREFIX
)
app.include_router(
    library.router,
    prefix=settings.API_V1_PREFIX
)

# Mount static files for serving uploads
# Ensure uploads directory exists
os.makedirs(settings.UPLOAD_FOLDER, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_FOLDER), name="uploads")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
