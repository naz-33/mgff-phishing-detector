"""FastAPI Application entrypoint for ZanderEtAlFishing Dashboard."""

from datetime import datetime, timezone
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import BASE_DIR, DATABASE_PATH
from backend.routers.analytics_routes import router as analytics_router
from backend.routers.auth_routes import router as auth_router
from backend.routers.dashboard_routes import router as dashboard_router
from backend.routers.emails_routes import router as emails_router
from backend.routers.model_routes import router as model_router
from backend.routers.monitor_routes import router as monitor_router
from database.connection import init_db

# Initialize database tables on startup
init_db(DATABASE_PATH)

app = FastAPI(
    title="ZanderEtAlFishing API",
    description="Web Dashboard Backend for Automated Phishing Email Detection and Monitoring",
    version="1.0.0",
)

# CORS configuration to allow local React frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows requests from Vite development server and production builds
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(emails_router)
app.include_router(analytics_router)
app.include_router(monitor_router)
app.include_router(model_router)


@app.get("/api/health", tags=["Health"])
def health_check():
    """Unauthenticated health status probe for uptime monitoring."""
    db_exists = os.path.exists(DATABASE_PATH)
    return {
        "status": "healthy",
        "service": "ZanderEtAlFishing Dashboard Backend",
        "version": "1.0.0",
        "database_connected": db_exists,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# Serve built React frontend assets if dist folder is present
frontend_dist_dir = BASE_DIR / "frontend" / "dist"
if frontend_dist_dir.exists():
    from fastapi.staticfiles import StaticFiles
    from starlette.responses import FileResponse

    assets_dir = frontend_dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Do not intercept API routes
        if full_path.startswith("api"):
            return None
        file_path = frontend_dist_dir / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist_dir / "index.html"))

