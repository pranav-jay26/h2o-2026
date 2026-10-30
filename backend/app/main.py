"""FastAPI entrypoint. Run with: `uvicorn app.main:app --reload --port 8000` from backend/."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import BASINS
from .mcp_server import mcp as mcp_server
from .routers import (
    alerts,
    events,
    forecast,
    met,
    reservoirs,
    snapshot,
    timeseries,
    zip_release,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # FastMCP's StreamableHTTPSessionManager owns an anyio task group that must
    # be running while the MCP HTTP endpoint serves requests. Mounting alone
    # doesn't start it — we have to enter its lifespan from ours.
    async with mcp_server.session_manager.run():
        yield


app = FastAPI(title="H2O Predictive Water Intelligence", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(snapshot.router, prefix="/api")
app.include_router(timeseries.router, prefix="/api")
app.include_router(forecast.router, prefix="/api")
app.include_router(alerts.router, prefix="/api")
app.include_router(reservoirs.router, prefix="/api")
app.include_router(met.router, prefix="/api")
app.include_router(zip_release.router, prefix="/api")
app.include_router(events.router, prefix="/api")

# MCP JSON-RPC server for the ElevenLabs voice agent. FastMCP exposes its
# Streamable HTTP endpoint at `/mcp` within its sub-app, so the public URL is
# `<host>/mcp/mcp`. Auth-less in dev; tunnel via ngrok for ElevenLabs.
app.mount("/mcp", mcp_server.streamable_http_app())


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/basins")
def list_basins() -> dict:
    return {
        "basins": [
            {
                "id": b.id,
                "name": b.name,
                "watershed": b.watershed,
                "cdec_station": b.cdec_station,
                "capacity_af": b.capacity_af,
                "lat": b.lat,
                "lon": b.lon,
                "has_history": b.has_history,
            }
            for b in BASINS.values()
        ]
    }
