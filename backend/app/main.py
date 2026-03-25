from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, score, findings, disputes, accounts, public, payments, employer


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Cloak Haven API",
    description="Online reputation scoring platform — like FICO for your digital identity",
    version="1.0.0",
    lifespan=lifespan,
)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
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


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}
