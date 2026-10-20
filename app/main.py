import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1 import ingestion, insights, clients, competitors, orchestration, webhooks, billing, dashboard, auth
from app.core.config import settings
from app.core.logging import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield

app = FastAPI(
    title="Competitive Intelligence AI Agent - Core",
    description="Backend API for managing competitor state and computing deltas.",
    version="1.0.0",
    lifespan=lifespan,
)

# The portal runs on its own origin and calls this API from the browser; without this every call
# failed its preflight (OPTIONS 405) and the portal showed empty pages.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.portal_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")
app.include_router(clients.router, prefix="/api/v1")
app.include_router(competitors.router, prefix="/api/v1")
app.include_router(orchestration.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(billing.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "Competitor Radar Core API is running."}
