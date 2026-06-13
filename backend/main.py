"""
Telco Discovery Platform — FastAPI Backend
"""

import json
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from parsers import load_preloaded_assets, parse_asset
from models import ParsedAsset, AnalysisState, DiscoveryOutput, RiskOutput, AIOpportunityOutput
from agents.discovery import run_discovery_agent
from agents.risk import run_risk_agent
from agents.ai_opportunities import run_ai_opportunities_agent
from agents.roadmap import run_roadmap_agent


# ── App State ─────────────────────────────────────────────────────────────────

state = AnalysisState()
preloaded_assets: list[ParsedAsset] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global preloaded_assets, state
    print(f"[startup] Working directory: {Path.cwd()}")
    print(f"[startup] __file__: {Path(__file__).resolve()}")
    print("[startup] Loading pre-built telco assets...")
    preloaded_assets = load_preloaded_assets()
    state.assets = preloaded_assets.copy()
    print(f"[startup] Loaded {len(preloaded_assets)} assets")
    yield


app = FastAPI(title="Telco Discovery Platform API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── SSE Helpers ───────────────────────────────────────────────────────────────

def sse_event(event_type: str, data: dict) -> str:
    payload = json.dumps({"event": event_type, **data})
    return f"data: {payload}\n\n"

def sse_keepalive() -> str:
    """SSE comment — keeps connection alive through Railway's proxy."""
    return ": keepalive\n\n"


# ── Assets Endpoints ──────────────────────────────────────────────────────────

@app.get("/api/assets")
def get_assets():
    return {
        "assets": [
            {
                "filename": a.filename,
                "asset_type": a.asset_type,
                "system_name": a.system_name,
                "metadata": a.metadata,
                "preloaded": a.filename in [p.filename for p in preloaded_assets]
            }
            for a in state.assets
        ],
        "total": len(state.assets)
    }


@app.post("/api/assets/upload")
async def upload_asset(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="replace")
    asset = parse_asset(file.filename, content)
    state.assets = [a for a in state.assets if a.filename != file.filename]
    state.assets.append(asset)
    return {"message": f"Uploaded and parsed: {file.filename}",
            "asset": {"filename": asset.filename, "asset_type": asset.asset_type,
                      "system_name": asset.system_name, "metadata": asset.metadata}}


@app.delete("/api/assets/{filename}")
def remove_asset(filename: str):
    preloaded_names = [p.filename for p in preloaded_assets]
    if filename in preloaded_names:
        raise HTTPException(status_code=400, detail="Cannot remove pre-loaded assets")
    before = len(state.assets)
    state.assets = [a for a in state.assets if a.filename != filename]
    if len(state.assets) == before:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": f"Removed: {filename}"}


@app.post("/api/reset")
def reset_state():
    global state
    state = AnalysisState(assets=preloaded_assets.copy())
    return {"message": "State reset to pre-loaded assets"}


# ── Full Orchestrated Analysis ────────────────────────────────────────────────

@app.get("/api/analyze/full")
async def stream_full_analysis():
    """
    Orchestrates all 4 agents sequentially, streaming SSE.
    Sends keepalive pings between chunks to prevent Railway timeout.
    """
    async def generate():
        # ── Agent 1: Discovery ──────────────────────────────────────────
        yield sse_event("agent_start", {"agent": "discovery", "label": "Discovery & Dependency Mapping"})
        yield sse_keepalive()

        async for event in run_discovery_agent(state.assets):
            if event["type"] == "chunk":
                yield sse_event("chunk", {"text": event["text"], "agent": "discovery"})
            elif event["type"] == "result":
                state.discovery = DiscoveryOutput(**event["data"])
                yield sse_event("result", {"agent": "discovery", "data": event["data"]})
            elif event["type"] == "error":
                yield sse_event("error", {"agent": "discovery", "message": event["message"]})

        yield sse_event("agent_done", {"agent": "discovery"})
        yield sse_keepalive()

        # ── Agent 2: Risk ───────────────────────────────────────────────
        yield sse_event("agent_start", {"agent": "risk", "label": "Risk & Architecture Analysis"})
        yield sse_keepalive()

        async for event in run_risk_agent(state.assets, state.discovery):
            if event["type"] == "chunk":
                yield sse_event("chunk", {"text": event["text"], "agent": "risk"})
            elif event["type"] == "result":
                state.risk = RiskOutput(**event["data"])
                yield sse_event("result", {"agent": "risk", "data": event["data"]})
            elif event["type"] == "error":
                yield sse_event("error", {"agent": "risk", "message": event["message"]})

        yield sse_event("agent_done", {"agent": "risk"})
        yield sse_keepalive()

        # ── Agent 3: AI Opportunities ───────────────────────────────────
        yield sse_event("agent_start", {"agent": "ai_opportunities", "label": "AI Opportunity Identification"})
        yield sse_keepalive()

        async for event in run_ai_opportunities_agent(state.assets, state.discovery, state.risk):
            if event["type"] == "chunk":
                yield sse_event("chunk", {"text": event["text"], "agent": "ai_opportunities"})
            elif event["type"] == "result":
                state.ai_opportunities = AIOpportunityOutput(**event["data"])
                yield sse_event("result", {"agent": "ai_opportunities", "data": event["data"]})
            elif event["type"] == "error":
                yield sse_event("error", {"agent": "ai_opportunities", "message": event["message"]})

        yield sse_event("agent_done", {"agent": "ai_opportunities"})
        yield sse_keepalive()

        # ── Agent 4: Roadmap ────────────────────────────────────────────
        yield sse_event("agent_start", {"agent": "roadmap", "label": "Migration Roadmap Generation"})
        yield sse_keepalive()

        async for event in run_roadmap_agent(
            state.assets, state.discovery, state.risk, state.ai_opportunities
        ):
            if event["type"] == "chunk":
                yield sse_event("chunk", {"text": event["text"], "agent": "roadmap"})
            elif event["type"] == "result":
                from models import RoadmapOutput
                state.roadmap = RoadmapOutput(**event["data"])
                yield sse_event("result", {"agent": "roadmap", "data": event["data"]})
            elif event["type"] == "error":
                yield sse_event("error", {"agent": "roadmap", "message": event["message"]})

        yield sse_event("agent_done", {"agent": "roadmap"})
        yield sse_keepalive()
        yield sse_event("analysis_complete", {"message": "All agents completed successfully"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",       # Disables Nginx buffering
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        }
    )


# ── Individual Agent Endpoints ────────────────────────────────────────────────

@app.get("/api/analyze/discovery")
async def stream_discovery():
    async def generate():
        async for event in run_discovery_agent(state.assets):
            if event["type"] == "chunk":
                yield sse_event("chunk", {"text": event["text"], "agent": "discovery"})
            elif event["type"] == "result":
                state.discovery = DiscoveryOutput(**event["data"])
                yield sse_event("result", {"agent": "discovery", "data": event["data"]})
            elif event["type"] == "error":
                yield sse_event("error", {"agent": "discovery", "message": event["message"]})
        yield sse_event("done", {"agent": "discovery"})
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── State & Health ────────────────────────────────────────────────────────────

@app.get("/api/state")
def get_state():
    return {
        "assets_loaded": len(state.assets),
        "discovery": state.discovery.model_dump() if state.discovery else None,
        "risk": state.risk.model_dump() if state.risk else None,
        "ai_opportunities": state.ai_opportunities.model_dump() if state.ai_opportunities else None,
        "roadmap": state.roadmap.model_dump() if state.roadmap else None,
    }


@app.get("/health")
def health():
    return {"status": "ok", "assets_loaded": len(state.assets)}
