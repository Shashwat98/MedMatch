"""
apply_agent.py — submits a job application to Medfinder via their MCP server.

Claude drives the full submission flow autonomously: reads the role overview,
then calls each MCP tool in order, threading the draft_id through every step.
The submission identifies itself with agent provenance metadata so the recruiter
can see exactly which agent and model completed the application.

Usage:
    cd apply
    python apply_agent.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import anthropic
import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

# Ensure UTF-8 output on Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

MCP_ENDPOINT = "https://hatch-one.vercel.app/api/mcp"
MODEL = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# Candidate data
# ---------------------------------------------------------------------------

CANDIDATE: dict[str, Any] = {
    "name": "Shashwat Singh",
    "email": "singhshashwat08@gmail.com",
    "location": "Boston, MA",
    "resume_url": "https://drive.google.com/uc?export=download&id=1Mh8M61uC7U2Vcirkcej-uDAKbAIHnF3a",
    "resume_mime_type": "application/pdf",
    "resume_filename": "Shashwat_Singh_Resume.pdf",
    "github_url": "https://github.com/Shashwat98",
    "linkedin_url": "https://www.linkedin.com/in/singhshashwat08/",
    "agentic_project_url": "https://github.com/Shashwat98/MedMatch",
    # The Answer to Life, the Universe, and Everything (H2G2)
    "screening_answer": "42",
}

AGENT_META: dict[str, str] = {
    "agent_name": "Claude Code",
    "agent_vendor": "Anthropic",
    "agent_model": MODEL,
    "agent_rationale": (
        "Shashwat built MedMatch — a full-stack multi-agent healthcare staffing intelligence "
        "system — as a portfolio piece specifically for this role. The system uses a LangGraph "
        "StateGraph supervisor to orchestrate five specialised agents: a Claude-powered "
        "requirement parser, deterministic Python agents for candidate matching, credential "
        "verification, and availability checking, and a Claude-powered ranking agent that "
        "produces per-candidate reasoning. Only two of five agents make LLM calls — the rest "
        "are deterministic Python — demonstrating deliberate judgment about where AI is "
        "warranted vs where rules suffice. A FastAPI backend streams each agent step live to "
        "a React frontend via WebSocket, so the recruiter can watch the pipeline think in real "
        "time. This application was submitted autonomously by a Claude Code agent driving "
        "Medfinder's own MCP server — a direct demonstration of the agentic development "
        "approach the role is hiring for."
    ),
    "candidate_prompt_preview": (
        "Apply for the Agentic Engineer role at Medfinder on my behalf. I built MedMatch — "
        "a multi-agent healthcare staffing intelligence system — as a portfolio piece for "
        "this application. Submit it using their MCP server."
    ),
}

# ---------------------------------------------------------------------------
# MCP transport
# ---------------------------------------------------------------------------

_req_id = 0


def call_mcp_tool(name: str, arguments: dict[str, Any]) -> str:
    """Execute a tool call against the MCP server via JSON-RPC 2.0."""
    global _req_id
    _req_id += 1

    resp = httpx.post(
        MCP_ENDPOINT,
        json={
            "jsonrpc": "2.0",
            "id": _req_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        timeout=30,
        follow_redirects=True,
    )
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"MCP error: {data['error']}")

    content = data["result"]["content"]
    return content[0]["text"] if content else ""


# ---------------------------------------------------------------------------
# Tool definitions for Claude
# ---------------------------------------------------------------------------

MCP_TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_role_overview",
        "description": (
            "Returns the open role details, application instructions, and the ordered "
            "list of submission tools. Always call this first."
        ),
        "input_schema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "submit_basic_details",
        "description": "Step 1. Creates a draft application and returns a draft_id required by all subsequent steps.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"},
                "location": {"type": "string"},
            },
            "required": ["name", "email"],
        },
    },
    {
        "name": "submit_resume",
        "description": "Step 2. Submit the resume as a hosted file URL (resume_url + resume_mime_type), markdown text, or both.",
        "input_schema": {
            "type": "object",
            "properties": {
                "draft_id": {"type": "string"},
                "resume_text": {"type": "string"},
                "resume_url": {"type": "string"},
                "resume_mime_type": {"type": "string"},
                "resume_filename": {"type": "string"},
            },
            "required": ["draft_id"],
        },
    },
    {
        "name": "submit_links",
        "description": "Step 3. Submit GitHub and LinkedIn profile URLs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "draft_id": {"type": "string"},
                "github_url": {"type": "string"},
                "linkedin_url": {"type": "string"},
            },
            "required": ["draft_id", "github_url", "linkedin_url"],
        },
    },
    {
        "name": "submit_agentic_project",
        "description": "Step 4. Submit a link to the candidate's agent harness, OpenClaw config, or other agentic project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "draft_id": {"type": "string"},
                "project_url": {"type": "string"},
            },
            "required": ["draft_id", "project_url"],
        },
    },
    {
        "name": "submit_screening_answer",
        "description": (
            "Final step. Submits the screening answer and finalises the application. "
            "Always include agent_name, agent_vendor, agent_model, agent_rationale, "
            "and candidate_prompt_preview."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "draft_id": {"type": "string"},
                "answer": {"type": ["string", "number"]},
                "agent_name": {"type": "string"},
                "agent_vendor": {"type": "string"},
                "agent_model": {"type": "string"},
                "agent_rationale": {"type": "string"},
                "candidate_prompt_preview": {"type": "string"},
            },
            "required": ["draft_id", "answer"],
        },
    },
]

# ---------------------------------------------------------------------------
# Agentic loop
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = f"""You are submitting a job application on behalf of a candidate to Medfinder via their MCP server.

Rules:
- Call get_role_overview first to confirm the submission flow.
- Follow every step in order: basic_details → resume → links → agentic_project → screening_answer.
- Thread the draft_id returned by submit_basic_details through every subsequent call.
- Do not skip or reorder any step — the server rejects out-of-order submissions.
- For submit_screening_answer, include ALL agent metadata fields verbatim.

Candidate data:
{json.dumps(CANDIDATE, indent=2)}

Agent metadata (pass verbatim to submit_screening_answer):
{json.dumps(AGENT_META, indent=2)}
"""

USER_PROMPT = (
    "Apply for the Agentic Engineer role at Medfinder on Shashwat's behalf. "
    "Start with get_role_overview, then complete every required submission step. "
    "Do not stop until the application is finalised."
)


def run() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        sys.exit("ANTHROPIC_API_KEY not set — add it to backend/.env")

    client = anthropic.Anthropic(api_key=api_key)
    messages: list[dict[str, Any]] = [{"role": "user", "content": USER_PROMPT}]

    print("=" * 60)
    print("  MedMatch Application Agent")
    print("  Candidate: Shashwat Singh")
    print("  Target:    Agentic Engineer @ Medfinder")
    print("=" * 60 + "\n")

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=MCP_TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        tool_results: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text" and block.text.strip():
                print(f"\nAgent: {block.text.strip()}")

            elif block.type == "tool_use":
                args_preview = json.dumps(block.input, ensure_ascii=False)
                print(f"\n-> {block.name}({args_preview[:100]}{'...' if len(args_preview) > 100 else ''})")

                try:
                    result = call_mcp_tool(block.name, block.input)
                    preview = result[:200] + ("..." if len(result) > 200 else "")
                    print(f"  OK {preview}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
                except Exception as exc:
                    print(f"  ERR {exc}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(exc),
                        "is_error": True,
                    })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        if response.stop_reason == "end_turn":
            print("\nDONE: Application complete.")
            break

        if response.stop_reason not in ("tool_use",):
            print(f"\nStopped: {response.stop_reason}")
            break


if __name__ == "__main__":
    run()
