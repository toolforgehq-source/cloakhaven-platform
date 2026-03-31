import os
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
import asyncio
from app.routers import auth, score, findings, disputes, accounts, public, payments, employer, admin, compliance, scan

logger = logging.getLogger("cloakhaven")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_db()

    # Background task: periodic re-scanning of stale profiles
    async def _rescan_stale_profiles():
        """Re-scan public profiles older than 30 days to keep scores fresh."""
        while True:
            await asyncio.sleep(3600 * 6)  # Every 6 hours
            try:
                from app.database import async_session_maker
                from app.models.public_profile import PublicProfile
                from app.services.passive_scanner import run_passive_scan
                from sqlalchemy import select
                from datetime import datetime, timedelta

                async with async_session_maker() as db:
                    cutoff = datetime.utcnow() - timedelta(days=30)
                    result = await db.execute(
                        select(PublicProfile).where(
                            PublicProfile.last_scanned_at < cutoff,
                            PublicProfile.public_score.isnot(None),
                        ).limit(10)  # Process 10 at a time
                    )
                    stale_profiles = result.scalars().all()

                    for profile in stale_profiles:
                        try:
                            await run_passive_scan(
                                db=db,
                                name=profile.lookup_name,
                            )
                            await db.commit()
                            logger.info("Re-scanned stale profile: %s", profile.lookup_name)
                        except Exception as e:
                            await db.rollback()
                            logger.warning("Re-scan failed for '%s': %s", profile.lookup_name, e)
            except Exception as e:
                logger.warning("Stale profile re-scan batch failed: %s", e)

    rescan_task = asyncio.create_task(_rescan_stale_profiles())
    yield
    rescan_task.cancel()


app = FastAPI(
    title="Cloak Haven API",
    description="The global standard for digital reputation — online reputation scoring platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins in development, restrict in production via ALLOWED_ORIGINS env var
_allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(score.router)
app.include_router(findings.router)
app.include_router(disputes.router)
app.include_router(accounts.router)
app.include_router(public.router)
app.include_router(payments.router)
app.include_router(employer.router)
app.include_router(admin.router)
app.include_router(compliance.router)
app.include_router(scan.router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler so unhandled errors return JSON, not HTML."""
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again later."},
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# Serve frontend static files (if built)
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the React SPA for any non-API route."""
        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
