"""
RankingAgent: uses Claude to produce a final ranked shortlist with one-sentence reasoning per candidate.
Only AVAILABLE candidates are eligible for top-5; CONFLICT candidates are noted but deprioritised.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import List

import anthropic
from dotenv import load_dotenv

load_dotenv()

from models import (
    AgentState,
    AvailableCandidate,
    AvailabilityStatus,
    RankedCandidate,
    RankedShortlist,
    ShiftRequirement,
    VerificationStatus,
)

MODEL = "claude-sonnet-4-6"

_RANKING_TOOL = {
    "name": "produce_ranked_shortlist",
    "description": "Produce the final ranked shortlist of up to 5 candidates.",
    "input_schema": {
        "type": "object",
        "properties": {
            "ranked_candidates": {
                "type": "array",
                "maxItems": 5,
                "items": {
                    "type": "object",
                    "properties": {
                        "candidate_id": {"type": "string"},
                        "rank": {"type": "integer"},
                        "reasoning": {
                            "type": "string",
                            "description": "One sentence explaining this ranking.",
                        },
                        "flags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Notable items: e.g. 'License expiring in 45 days', 'Exceeds experience requirement'",
                        },
                    },
                    "required": ["candidate_id", "rank", "reasoning", "flags"],
                },
            }
        },
        "required": ["ranked_candidates"],
    },
}


def _build_candidate_summary(ac: AvailableCandidate) -> str:
    c = ac.verified.matched.candidate
    s = ac.verified.matched.scores
    return (
        f"ID={c.id} | {c.name} | {c.specialty} {c.role} | "
        f"Certs: {', '.join(c.certifications)} | "
        f"Experience: {c.years_experience}yr | Rating: {c.rating} | "
        f"Score: {s.total_score} | "
        f"Credentials: {ac.verified.verification_status.value} | "
        f"Availability: {ac.availability_status.value}"
    )


def ranking_node(state: AgentState) -> dict:
    """LangGraph node: rank verified, available candidates and generate reasoning via Claude."""
    try:
        req = ShiftRequirement(**state["parsed_requirement"])
        all_candidates = [AvailableCandidate(**a) for a in state["available_candidates"]]

        # Eligible = AVAILABLE first, then fall back to CONFLICT if needed to fill 5 slots
        available = [a for a in all_candidates if a.availability_status == AvailabilityStatus.AVAILABLE]
        eligible = available if len(available) >= 5 else all_candidates
        eligible = eligible[:10]  # cap context

        if not eligible:
            trace_msg = "[RankingAgent] No eligible candidates to rank"
            return {
                "ranked_shortlist": [],
                "execution_trace": state["execution_trace"] + [trace_msg],
                "current_step": "ranking_complete",
                "error": None,
            }

        req_summary = (
            f"Shift: {req.role} · {req.specialty} · {req.location} · "
            f"{req.shift_type} shift · "
            f"{'on ' + req.shift_day_of_week if req.shift_day_of_week else ''} · "
            f"Certs required: {', '.join(req.certifications_required)} · "
            f"Min experience: {req.min_years_experience}yr · "
            f"Urgency: {req.urgency.value}"
        )

        candidate_lines = "\n".join(
            f"{i+1}. {_build_candidate_summary(a)}" for i, a in enumerate(eligible)
        )

        prompt = (
            f"You are a healthcare staffing coordinator. Rank the top 5 candidates for this shift.\n\n"
            f"SHIFT REQUIREMENT:\n{req_summary}\n\n"
            f"CANDIDATES:\n{candidate_lines}\n\n"
            f"Ranking criteria (in order): "
            f"(1) availability AVAILABLE > CONFLICT, "
            f"(2) verification VERIFIED > EXPIRING_SOON > MISSING_CERT, "
            f"(3) match score descending, "
            f"(4) years experience descending.\n"
            f"Provide a one-sentence reasoning that highlights the key reason for each candidate's placement."
        )

        client = anthropic.Anthropic()
        response = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            tools=[_RANKING_TOOL],
            tool_choice={"type": "tool", "name": "produce_ranked_shortlist"},
            messages=[{"role": "user", "content": prompt}],
        )

        tool_block = next(b for b in response.content if b.type == "tool_use")
        ranking_data: list[dict] = tool_block.input["ranked_candidates"]

        # Join back with full candidate objects
        candidate_map = {a.verified.matched.candidate.id: a for a in eligible}
        ranked: List[RankedCandidate] = []

        for entry in ranking_data:
            cid = entry["candidate_id"]
            if cid not in candidate_map:
                continue
            ac = candidate_map[cid]
            c = ac.verified.matched.candidate
            ranked.append(
                RankedCandidate(
                    rank=entry["rank"],
                    candidate=c,
                    total_score=ac.verified.matched.scores.total_score,
                    verification_status=ac.verified.verification_status,
                    availability_status=ac.availability_status,
                    reasoning=entry["reasoning"],
                    flags=entry.get("flags", []),
                )
            )

        ranked.sort(key=lambda r: r.rank)

        shortlist = RankedShortlist(
            candidates=ranked,
            shift_requirement=req,
            generated_at=datetime.utcnow(),
            total_candidates_evaluated=len(all_candidates),
        )

        trace_msg = (
            f"[RankingAgent] Ranked {len(ranked)} candidates · "
            f"top pick: {ranked[0].candidate.name} (score={ranked[0].total_score})"
            if ranked else "[RankingAgent] No candidates ranked"
        )

        return {
            "ranked_shortlist": [r.model_dump(mode="json") for r in ranked],
            "execution_trace": state["execution_trace"] + [trace_msg],
            "current_step": "ranking_complete",
            "error": None,
        }

    except Exception as exc:
        return {
            "execution_trace": state["execution_trace"] + [f"[RankingAgent] ERROR: {exc}"],
            "current_step": "error",
            "error": str(exc),
        }
