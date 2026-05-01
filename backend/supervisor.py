"""
Supervisor: builds the LangGraph StateGraph that wires all agent nodes into a
sequential pipeline and exposes sync + async streaming execution interfaces.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from langgraph.graph import END, StateGraph

from agents.availability_agent import availability_node
from agents.credential_verifier import credential_verifier_node
from agents.matcher_agent import matcher_node
from agents.ranking_agent import ranking_node
from agents.requirement_parser import requirement_parser_node
from candidate_store import get_all
from models import AgentState


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _route(state: AgentState) -> str:
    """Short-circuit to END if any node set an error."""
    return "end" if state.get("error") else "continue"


def _build_pipeline():
    g = StateGraph(AgentState)

    g.add_node("requirement_parser", requirement_parser_node)
    g.add_node("candidate_matcher", matcher_node)
    g.add_node("credential_verifier", credential_verifier_node)
    g.add_node("availability_agent", availability_node)
    g.add_node("ranking_agent", ranking_node)

    g.set_entry_point("requirement_parser")

    # Sequential edges with error short-circuit
    for src, dst in [
        ("requirement_parser", "candidate_matcher"),
        ("candidate_matcher", "credential_verifier"),
        ("credential_verifier", "availability_agent"),
        ("availability_agent", "ranking_agent"),
    ]:
        g.add_conditional_edges(src, _route, {"continue": dst, "end": END})

    g.add_edge("ranking_agent", END)

    return g.compile()


# Compiled once at import time; reused across all requests
pipeline = _build_pipeline()


# ---------------------------------------------------------------------------
# State factory
# ---------------------------------------------------------------------------

def create_initial_state(raw_requirement: str) -> AgentState:
    """Build the initial AgentState with the candidate pool pre-loaded."""
    return {
        "raw_requirement": raw_requirement,
        "parsed_requirement": None,
        "candidate_pool": [c.model_dump(mode="json") for c in get_all()],
        "matched_candidates": [],
        "verified_candidates": [],
        "available_candidates": [],
        "ranked_shortlist": [],
        "execution_trace": [],
        "current_step": "start",
        "error": None,
    }


# ---------------------------------------------------------------------------
# Execution interfaces
# ---------------------------------------------------------------------------

def run_pipeline(raw_requirement: str) -> AgentState:
    """Synchronous pipeline run. Returns the final state dict."""
    return pipeline.invoke(create_initial_state(raw_requirement))


async def run_pipeline_streaming(
    raw_requirement: str,
    queue: Optional[asyncio.Queue] = None,
) -> AgentState:
    """
    Async pipeline run with optional live streaming.

    If queue is provided, each new execution_trace line is pushed as
    {"type": "trace", "message": str} and a final {"type": "done"} is sent.
    Returns the final state dict.
    """
    state = create_initial_state(raw_requirement)
    final_state: AgentState = state
    prev_trace_len = 0

    async for snapshot in pipeline.astream(state, stream_mode="values"):
        final_state = snapshot

        if queue is not None:
            trace: list[str] = snapshot.get("execution_trace", [])
            for msg in trace[prev_trace_len:]:
                await queue.put({"type": "trace", "message": msg})
            prev_trace_len = len(trace)

    if queue is not None:
        await queue.put({"type": "done", "message": "Pipeline complete"})

    return final_state
