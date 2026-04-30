"""
CandidateMatcherAgent: scores all candidates against a ShiftRequirement and returns the top 10.
Pure Python — no LLM calls. Scoring weights: specialty 40%, certs 25%, location 25%, experience 10%.
"""

from __future__ import annotations

from models import AgentState, Candidate, MatchedCandidate, MatchScores, ShiftRequirement


def _score(candidate: Candidate, req: ShiftRequirement) -> MatchScores:
    # Specialty: exact case-insensitive match
    specialty_score = 1.0 if candidate.specialty.lower() == req.specialty.lower() else 0.0

    # Certifications: fraction of required certs the candidate holds
    if req.certifications_required:
        held = sum(1 for c in req.certifications_required if c in candidate.certifications)
        cert_score = held / len(req.certifications_required)
    else:
        cert_score = 1.0

    # Location: license state match
    location_score = 1.0 if candidate.license_state == req.license_state else 0.0

    # Experience: normalised against twice the minimum requirement (or 20 yrs default)
    baseline = max(req.min_years_experience * 2, 1) if req.min_years_experience else 20
    experience_score = min(candidate.years_experience / baseline, 1.0)

    total = round(
        0.40 * specialty_score
        + 0.25 * cert_score
        + 0.25 * location_score
        + 0.10 * experience_score,
        3,
    )

    return MatchScores(
        specialty_score=specialty_score,
        cert_score=cert_score,
        location_score=location_score,
        experience_score=experience_score,
        total_score=total,
    )


def matcher_node(state: AgentState) -> dict:
    """LangGraph node: score every candidate, return top 10 sorted by total score."""
    try:
        req = ShiftRequirement(**state["parsed_requirement"])
        pool = [Candidate(**c) for c in state["candidate_pool"]]

        ranked = sorted(
            [MatchedCandidate(candidate=c, scores=_score(c, req)) for c in pool],
            key=lambda m: m.scores.total_score,
            reverse=True,
        )[:10]

        top_score = ranked[0].scores.total_score if ranked else 0.0
        trace_msg = (
            f"[CandidateMatcher] Scored {len(pool)} candidates · "
            f"top score={top_score} · returning top {len(ranked)}"
        )
        return {
            "matched_candidates": [m.model_dump(mode="json") for m in ranked],
            "execution_trace": state["execution_trace"] + [trace_msg],
            "current_step": "candidates_matched",
            "error": None,
        }

    except Exception as exc:
        return {
            "execution_trace": state["execution_trace"] + [f"[CandidateMatcher] ERROR: {exc}"],
            "current_step": "error",
            "error": str(exc),
        }
