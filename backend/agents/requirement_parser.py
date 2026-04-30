"""
RequirementParserAgent: extracts a structured ShiftRequirement from recruiter free-text.
Uses Claude tool use to guarantee structured JSON output.
"""

from __future__ import annotations

from datetime import date

import anthropic
from dotenv import load_dotenv

load_dotenv()

from models import AgentState, ShiftRequirement

MODEL = "claude-sonnet-4-6"

_EXTRACTION_TOOL = {
    "name": "extract_shift_requirement",
    "description": "Extract structured information from a healthcare shift requirement.",
    "input_schema": {
        "type": "object",
        "properties": {
            "specialty": {
                "type": "string",
                "description": "Clinical specialty, e.g. ICU, ER, Med-Surg, Pediatrics",
            },
            "role": {
                "type": "string",
                "description": "Job role, e.g. RN, LPN, CNA, NP",
            },
            "certifications_required": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Required certifications, e.g. ACLS, BLS, PALS",
            },
            "location": {
                "type": "string",
                "description": "City and state, e.g. Boston, MA",
            },
            "license_state": {
                "type": "string",
                "description": "Two-letter US state abbreviation inferred from location",
            },
            "shift_type": {
                "type": "string",
                "enum": ["day", "night", "evening"],
            },
            "shift_date": {
                "type": "string",
                "description": "ISO date YYYY-MM-DD if determinable, otherwise omit",
            },
            "shift_day_of_week": {
                "type": "string",
                "description": "Day of week if exact date is ambiguous, e.g. Saturday",
            },
            "min_years_experience": {
                "type": "integer",
                "description": "Minimum years of experience required; 0 if not specified",
            },
            "urgency": {
                "type": "string",
                "enum": ["low", "medium", "high"],
                "description": "'urgent', 'ASAP', 'short-staffed' = high; default = medium",
            },
        },
        "required": [
            "specialty",
            "role",
            "certifications_required",
            "location",
            "license_state",
            "shift_type",
            "urgency",
            "min_years_experience",
        ],
    },
}

_SYSTEM = (
    "You are a healthcare staffing specialist. Extract structured information from shift requirements.\n"
    f"Today's date is {date.today().isoformat()}. Use it to resolve relative dates like 'this Saturday'.\n"
    "Infer license_state as the two-letter code from the city/state in the location.\n"
    "urgency: 'urgent', 'ASAP', 'short-staffed', 'critical' → high; 'when available' → low; otherwise → medium."
)


def requirement_parser_node(state: AgentState) -> dict:
    """LangGraph node: parse raw free-text into a structured ShiftRequirement."""
    try:
        client = anthropic.Anthropic()

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=_SYSTEM,
            tools=[_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "extract_shift_requirement"},
            messages=[{"role": "user", "content": state["raw_requirement"]}],
        )

        tool_block = next(b for b in response.content if b.type == "tool_use")
        data: dict = dict(tool_block.input)
        data["raw_text"] = state["raw_requirement"]

        # Normalise optional date field
        if data.get("shift_date") in (None, "", "null"):
            data.pop("shift_date", None)

        req = ShiftRequirement(**data)

        trace_msg = (
            f"[RequirementParser] {req.role} · {req.specialty} · {req.location} · "
            f"shift={req.shift_type} · certs={req.certifications_required} · "
            f"urgency={req.urgency.value}"
        )
        return {
            "parsed_requirement": req.model_dump(mode="json"),
            "execution_trace": state["execution_trace"] + [trace_msg],
            "current_step": "requirement_parsed",
            "error": None,
        }

    except Exception as exc:
        return {
            "execution_trace": state["execution_trace"] + [f"[RequirementParser] ERROR: {exc}"],
            "current_step": "error",
            "error": str(exc),
        }
