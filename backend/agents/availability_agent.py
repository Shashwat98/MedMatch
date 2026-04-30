"""
AvailabilityAgent: checks each candidate's availability against the requested shift day.
Pure Python — no LLM calls.
"""

from __future__ import annotations

from datetime import date
from typing import List, Tuple

from models import (
    AgentState,
    AvailableCandidate,
    AvailabilityStatus,
    ShiftRequirement,
    VerifiedCandidate,
)

_WEEKDAY_NAMES = {
    0: "Monday", 1: "Tuesday", 2: "Wednesday",
    3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday",
}


def _resolve_shift_day(req: ShiftRequirement) -> str | None:
    """Return the day-of-week string to match against candidate availability."""
    if req.shift_day_of_week:
        return req.shift_day_of_week.strip().capitalize()
    if req.shift_date:
        return _WEEKDAY_NAMES[req.shift_date.weekday()]
    return None


def _check(availability: List[str], req: ShiftRequirement) -> Tuple[AvailabilityStatus, str]:
    day = _resolve_shift_day(req)
    if day is None:
        return AvailabilityStatus.UNKNOWN, "Shift day not specified; availability unconfirmed"
    if day in availability:
        return AvailabilityStatus.AVAILABLE, f"Available on {day}"
    return AvailabilityStatus.CONFLICT, f"Not available on {day}"


def availability_node(state: AgentState) -> dict:
    """LangGraph node: confirm shift-day availability for each verified candidate."""
    try:
        req = ShiftRequirement(**state["parsed_requirement"])
        results: List[AvailableCandidate] = []
        counts = {s.value: 0 for s in AvailabilityStatus}

        for vc_dict in state["verified_candidates"]:
            vc = VerifiedCandidate(**vc_dict)
            a_status, note = _check(vc.matched.candidate.availability, req)
            results.append(
                AvailableCandidate(verified=vc, availability_status=a_status, availability_note=note)
            )
            counts[a_status.value] += 1

        summary = " · ".join(f"{k}={v}" for k, v in counts.items() if v > 0)
        trace_msg = f"[AvailabilityAgent] Checked {len(results)} candidates · {summary}"

        return {
            "available_candidates": [a.model_dump(mode="json") for a in results],
            "execution_trace": state["execution_trace"] + [trace_msg],
            "current_step": "availability_checked",
            "error": None,
        }

    except Exception as exc:
        return {
            "execution_trace": state["execution_trace"] + [f"[AvailabilityAgent] ERROR: {exc}"],
            "current_step": "error",
            "error": str(exc),
        }
