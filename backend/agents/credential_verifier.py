"""
CredentialVerifierAgent: checks license validity, required certifications, and runs a mock NPI lookup.
Pure Python. Sets VerificationStatus per candidate: VERIFIED, EXPIRING_SOON, or MISSING_CERT.
"""

from __future__ import annotations

from datetime import date
from typing import List, Tuple

from models import (
    AgentState,
    Candidate,
    MatchedCandidate,
    ShiftRequirement,
    VerificationStatus,
    VerifiedCandidate,
)

_EXPIRY_WARNING_DAYS = 60


def _mock_npi_lookup(npi: str, name: str) -> Tuple[bool, str]:
    """
    Simulate a CMS NPI Registry lookup.
    Real endpoint: https://npiregistry.cms.hhs.gov/api/
    """
    if npi and len(npi) == 10 and npi.isdigit():
        return True, f"NPI {npi} active in CMS registry (mock) — {name}"
    return False, f"NPI {npi} not found in CMS registry (mock)"


def _verify(
    candidate: Candidate,
    req: ShiftRequirement,
    ref_date: date,
) -> Tuple[VerificationStatus, List[str], bool]:
    notes: List[str] = []
    status = VerificationStatus.VERIFIED

    # NPI lookup
    npi_ok, npi_msg = _mock_npi_lookup(candidate.npi_number, candidate.name)
    notes.append(npi_msg)

    # License expiry
    days_remaining = (candidate.license_expiry - ref_date).days
    if days_remaining < 0:
        notes.append(
            f"License expired {abs(days_remaining)} days ago ({candidate.license_expiry})"
        )
        status = VerificationStatus.MISSING_CERT
    elif days_remaining <= _EXPIRY_WARNING_DAYS:
        notes.append(
            f"License expiring in {days_remaining} days ({candidate.license_expiry})"
        )
        if status == VerificationStatus.VERIFIED:
            status = VerificationStatus.EXPIRING_SOON
    else:
        notes.append(f"License valid until {candidate.license_expiry} ({days_remaining} days remaining)")

    # Required certifications
    missing = [c for c in req.certifications_required if c not in candidate.certifications]
    if missing:
        notes.append(f"Missing required certifications: {', '.join(missing)}")
        status = VerificationStatus.MISSING_CERT

    return status, notes, npi_ok


def credential_verifier_node(state: AgentState) -> dict:
    """LangGraph node: verify credentials for each matched candidate."""
    try:
        req = ShiftRequirement(**state["parsed_requirement"])
        ref_date = req.shift_date or date.today()

        verified: List[VerifiedCandidate] = []
        counts = {s.value: 0 for s in VerificationStatus}

        for mc_dict in state["matched_candidates"]:
            mc = MatchedCandidate(**mc_dict)
            v_status, notes, npi_ok = _verify(mc.candidate, req, ref_date)
            verified.append(
                VerifiedCandidate(
                    matched=mc,
                    verification_status=v_status,
                    verification_notes=notes,
                    npi_verified=npi_ok,
                )
            )
            counts[v_status.value] += 1

        summary = " · ".join(f"{k}={v}" for k, v in counts.items() if v > 0)
        trace_msg = f"[CredentialVerifier] Checked {len(verified)} candidates · {summary}"

        return {
            "verified_candidates": [v.model_dump(mode="json") for v in verified],
            "execution_trace": state["execution_trace"] + [trace_msg],
            "current_step": "credentials_verified",
            "error": None,
        }

    except Exception as exc:
        return {
            "execution_trace": state["execution_trace"] + [f"[CredentialVerifier] ERROR: {exc}"],
            "current_step": "error",
            "error": str(exc),
        }
