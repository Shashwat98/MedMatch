"""
FastAPI application for the MedMatch agent pipeline.

Endpoints:
  GET  /health        — liveness check
  GET  /candidates    — full synthetic candidate pool
  POST /match         — run pipeline, return shortlist + trace (non-streaming)
  WS   /ws/match      — stream execution trace live, then return final result
"""

from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import candidate_store
import supervisor as _supervisor

# Configurable via ALLOWED_ORIGINS env var (comma-separated).
# Set this in Render to your Vercel deployment URL.
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS: list[str] = (
    [o.strip() for o in _raw_origins.split(",") if o.strip()]
    or ["http://localhost:5173", "http://localhost:3000"]
)


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    candidates = candidate_store.get_all()
    print(f"[startup] {len(candidates)} candidates loaded")
    _ = _supervisor.pipeline  # graph already compiled at import; this confirms it
    print("[startup] Pipeline ready")
    yield


app = FastAPI(
    title="MedMatch API",
    description="Multi-agent healthcare staffing intelligence",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow localhost dev origins; add your Vercel deployment URL here before shipping
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class MatchRequest(BaseModel):
    requirement: str = Field(min_length=10)


class MatchResponse(BaseModel):
    shortlist: List[Dict[str, Any]]
    execution_trace: List[str]
    shift_requirement: Optional[Dict[str, Any]]
    total_candidates_evaluated: int
    error: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_response(state: dict) -> MatchResponse:
    return MatchResponse(
        shortlist=state.get("ranked_shortlist", []),
        execution_trace=state.get("execution_trace", []),
        shift_requirement=state.get("parsed_requirement"),
        total_candidates_evaluated=len(state.get("available_candidates", [])),
        error=state.get("error"),
    )


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/candidates")
async def get_candidates():
    return {"candidates": [c.model_dump(mode="json") for c in candidate_store.get_all()]}


@app.post("/match", response_model=MatchResponse)
async def match(req: MatchRequest):
    """Run the full agent pipeline and return the complete result."""
    state = await _supervisor.run_pipeline_streaming(req.requirement)
    return _to_response(state)


# ---------------------------------------------------------------------------
# WebSocket — live execution trace
# ---------------------------------------------------------------------------

@app.websocket("/ws/match")
async def ws_match(websocket: WebSocket):
    """
    Stream pipeline execution trace to the client in real time.

    Protocol:
      Client → server : {"requirement": "<free-text>"}
      Server → client : {"type": "trace",  "message": "<agent log line>"}  (×N)
                        {"type": "done",   "result": <MatchResponse dict>}
                        {"type": "error",  "message": "<description>"}
    """
    await websocket.accept()
    task: asyncio.Task | None = None

    try:
        data = await websocket.receive_json()
        requirement: str = data.get("requirement", "").strip()

        if not requirement:
            await websocket.send_json({"type": "error", "message": "requirement is empty"})
            return

        queue: asyncio.Queue = asyncio.Queue()
        task = asyncio.create_task(
            _supervisor.run_pipeline_streaming(requirement, queue)
        )

        while True:
            msg = await queue.get()

            if msg["type"] == "done":
                final_state = await task
                await websocket.send_json({
                    "type": "done",
                    "result": _to_response(final_state).model_dump(),
                })
                break

            await websocket.send_json(msg)

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if task and not task.done():
            task.cancel()
