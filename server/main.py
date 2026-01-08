from contextlib import asynccontextmanager
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from db.models import Base, engine
from api import auth, devices, hostgroups, templates, triggers, actions, users, alerts, maintenance, discovery, commands, maps
import os

from workers.alerting_worker import alerting_loop

logger = logging.getLogger(__name__)

# Warn if deployment secrets are left at defaults.
if settings.SECRET_KEY == "your-secret-key-change-in-production-minimum-32-characters":
    logger.warning("SECRET_KEY is still the default placeholder. Set SECRET_KEY in server/.env before production use.")
if settings.ALERT_WEBHOOK_REQUIRE_TOKEN and not settings.ALERT_WEBHOOK_TOKEN:
    logger.warning("ALERT_WEBHOOK_TOKEN is empty. Webhook ingestion will reject requests until it is set.")
if settings.DEVICE_REGISTRATION_REQUIRE_TOKEN and not settings.DEVICE_REGISTRATION_TOKEN:
    logger.warning(
        "DEVICE_REGISTRATION_TOKEN is empty. Device registration will be rejected until it is set "
        "(or set DEVICE_REGISTRATION_REQUIRE_TOKEN=false for local dev)."
    )

# Create database tables
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan with background workers."""
    logger.info("Starting background alerting worker...")
    
    # Start alerting worker as background task
    task = asyncio.create_task(alerting_loop())
    
    yield  # Application runs here
    
    # Shutdown: cancel worker
    logger.info("Shutting down alerting worker...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(devices.router, prefix=settings.API_V1_PREFIX)
app.include_router(hostgroups.router, prefix=settings.API_V1_PREFIX)
app.include_router(templates.router, prefix=settings.API_V1_PREFIX)
app.include_router(triggers.router, prefix=settings.API_V1_PREFIX)
app.include_router(actions.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(alerts.router, prefix=settings.API_V1_PREFIX)
app.include_router(maintenance.router, prefix=settings.API_V1_PREFIX)
app.include_router(discovery.router, prefix=settings.API_V1_PREFIX)
app.include_router(commands.router, prefix=settings.API_V1_PREFIX)
app.include_router(maps.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def root():
    return {"message": "Health Monitor API", "version": "1.0.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8001"))
    reload = os.getenv("UVICORN_RELOAD", "").strip().lower() in {"1", "true", "yes"}
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload)
