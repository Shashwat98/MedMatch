"""
Pydantic models for MedMatch agent pipeline.
All data structures flow through these models from input to final ranked output.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import List, Optional, TypedDict

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    EXPIRING_SOON = "EXPIRING_SOON"
    MISSING_CERT = "MISSING_CERT"


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    CONFLICT = "CONFLICT"
    UNKNOWN = "UNKNOWN"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

class ShiftRequirement(BaseModel):
    """Structured shift requirement extracted from recruiter free-text."""

    specialty: str = Field(description="Clinical specialty, e.g. ICU, ER, Med-Surg")
    role: str = Field(description="Job role, e.g. RN, LPN, CNA, NP")
    certifications_required: List[str] = Field(
        default_factory=list,
        description="Required certifications, e.g. ACLS, BLS, PALS",
    )
    location: str = Field(description="City and state, e.g. Boston, MA")
    license_state: str = Field(description="Two-letter state abbreviation, e.g. MA")
    shift_type: str = Field(description="Shift type: day, night, or evening")
    shift_date: Optional[date] = Field(
        default=None, description="Specific shift date if determinable"
    )
    shift_day_of_week: Optional[str] = Field(
        default=None, description="Day of week if exact date is ambiguous, e.g. Saturday"
    )
    min_years_experience: int = Field(
        default=0, description="Minimum years of experience required"
    )
    urgency: Urgency = Field(default=Urgency.MEDIUM)
    raw_text: str = Field(description="Original free-text input from recruiter")


# ---------------------------------------------------------------------------
# Candidate pool
# ---------------------------------------------------------------------------

class Candidate(BaseModel):
    """A synthetic clinician from the candidate pool."""

    id: str
    name: str
    specialty: str
    role: str
    certifications: List[str] = Field(default_factory=list)
    license_state: str
    license_expiry: date
    years_experience: int
    availability: List[str] = Field(
        description="Days available: Monday–Sunday, or specific dates (YYYY-MM-DD)"
    )
    last_placement: Optional[date] = None
    rating: float = Field(ge=1.0, le=5.0)
    npi_number: str = Field(description="Synthetic NPI for mock verification lookup")


# ---------------------------------------------------------------------------
# Pipeline intermediate models
# ---------------------------------------------------------------------------

class MatchScores(BaseModel):
    specialty_score: float = Field(ge=0.0, le=1.0)
    cert_score: float = Field(ge=0.0, le=1.0)
    location_score: float = Field(ge=0.0, le=1.0)
    experience_score: float = Field(ge=0.0, le=1.0)
    total_score: float = Field(ge=0.0, le=1.0)


class MatchedCandidate(BaseModel):
    """Candidate annotated with match scores from CandidateMatcherAgent."""

    candidate: Candidate
    scores: MatchScores


class VerifiedCandidate(BaseModel):
    """MatchedCandidate annotated with credential verification results."""

    matched: MatchedCandidate
    verification_status: VerificationStatus
    verification_notes: List[str] = Field(default_factory=list)
    npi_verified: bool = False


class AvailableCandidate(BaseModel):
    """VerifiedCandidate annotated with availability confirmation."""

    verified: VerifiedCandidate
    availability_status: AvailabilityStatus
    availability_note: str = ""


# ---------------------------------------------------------------------------
# Final output
# ---------------------------------------------------------------------------

class RankedCandidate(BaseModel):
    """Single entry in the final ranked shortlist."""

    rank: int
    candidate: Candidate
    total_score: float
    verification_status: VerificationStatus
    availability_status: AvailabilityStatus
    reasoning: str = Field(description="One-sentence explanation of this ranking")
    flags: List[str] = Field(
        default_factory=list,
        description="Warning flags, e.g. license expiring in 30 days",
    )


class RankedShortlist(BaseModel):
    """Final output of the full agent pipeline."""

    candidates: List[RankedCandidate]
    shift_requirement: ShiftRequirement
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    total_candidates_evaluated: int


# ---------------------------------------------------------------------------
# LangGraph state
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    raw_requirement: str
    parsed_requirement: Optional[dict]
    candidate_pool: List[dict]
    matched_candidates: List[dict]
    verified_candidates: List[dict]
    available_candidates: List[dict]
    ranked_shortlist: List[dict]
    execution_trace: List[str]
    current_step: str
    error: Optional[str]
