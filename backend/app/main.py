import os
import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import auth, score, findings, disputes, accounts, public, payments, employer, admin, compliance, scan, partner

logger = logging.getLogger("cloakhaven")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# ── Sentry error monitoring ─────────────────────────────────────────────
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        release=settings.APP_VERSION,
    )
    logger.info("Sentry error monitoring enabled")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(application: FastAPI):
    from app.middleware.rate_limit import public_limiter, auth_limiter, partner_limiter, audit_limiter

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

    # Background task to periodically clean up stale rate limit entries
    async def _cleanup_rate_limiters():
        while True:
            await asyncio.sleep(3600)  # Every hour
            for limiter in (public_limiter, auth_limiter, partner_limiter, audit_limiter):
                limiter.cleanup(max_age=7200)

    cleanup_task = asyncio.create_task(_cleanup_rate_limiters())
    yield
    rescan_task.cancel()
    cleanup_task.cancel()


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
app.include_router(partner.router)


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



# ── Server-side OG meta tags for scorecard sharing ──────────────────────
async def _scorecard_og_html(user_id: str) -> HTMLResponse | None:
    """Return HTML with dynamic OG meta tags for a scorecard page.

    Social-media crawlers (Open Graph) don't execute JS, so we inject the
    meta tags server-side when the path matches /scorecard/<uuid>.
    """
    try:
        import uuid as _uuid
        _uuid.UUID(user_id)  # validate
    except (ValueError, AttributeError):
        return None

    from app.database import async_session_maker as _asm
    from app.models.user import User as _User
    from app.models.score import Score as _Score
    from sqlalchemy import select as _sel
    from app.services.scoring_engine import get_score_label

    try:
        async with _asm() as db:
            user = await db.get(_User, _uuid.UUID(user_id))
            if not user or user.profile_visibility != "public":
                return None
            result = await db.execute(_sel(_Score).where(_Score.user_id == user.id))
            sc = result.scalar_one_or_none()
            if not sc:
                return None

        name = user.display_name or user.full_name or "Anonymous"
        score_val = sc.overall_score
        label = get_score_label(score_val)
        url = f"{settings.FRONTEND_URL}/scorecard/{user_id}"
        title = f"{name}'s Cloak Haven Score: {score_val} ({label})"
        desc = "Digital reputation score powered by Cloak Haven — the global standard for online reputation."

        # Read the SPA index.html and inject OG tags
        index_html = (STATIC_DIR / "index.html").read_text()
        og_tags = f"""
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="{desc}" />
    <meta property="og:url" content="{url}" />
    <meta property="og:type" content="profile" />
    <meta property="og:site_name" content="Cloak Haven" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="{title}" />
    <meta name="twitter:description" content="{desc}" />"""
        # Insert OG tags right before </head>
        html = index_html.replace("</head>", f"{og_tags}\n  </head>")
        return HTMLResponse(content=html)
    except Exception:
        return None


# Serve frontend static files (if built)
if STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve the React SPA for any non-API route.

        For /scorecard/<uuid> paths, injects dynamic OG meta tags so social
        media previews show the user's score.
        """
        # Dynamic OG tags for scorecard pages
        if full_path.startswith("scorecard/"):
            uid = full_path.removeprefix("scorecard/").split("/")[0].split("?")[0]
            og_response = await _scorecard_og_html(uid)
            if og_response:
                return og_response

        file_path = STATIC_DIR / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(STATIC_DIR / "index.html"))
