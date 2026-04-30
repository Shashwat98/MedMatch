"""
Candidate store: loads the synthetic clinician pool into memory at startup.
Auto-generates candidates.json on first run if it doesn't exist.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from models import Candidate

DATA_FILE = Path(__file__).parent / "data" / "candidates.json"

_cache: Optional[List[Candidate]] = None


def _ensure_data() -> None:
    if DATA_FILE.exists():
        return

    print("candidates.json not found — generating synthetic pool...")
    from generate_candidates import generate_candidates

    DATA_FILE.parent.mkdir(exist_ok=True)
    candidates = generate_candidates()
    with open(DATA_FILE, "w") as f:
        json.dump(candidates, f, indent=2)
    print(f"Saved {len(candidates)} candidates to {DATA_FILE}")


def load_candidates() -> List[Candidate]:
    """Load all candidates from JSON, parsing into Pydantic models."""
    _ensure_data()
    with open(DATA_FILE) as f:
        raw: list[dict] = json.load(f)
    return [Candidate(**c) for c in raw]


def get_all() -> List[Candidate]:
    """Return the full candidate pool, loading from disk on first call."""
    global _cache
    if _cache is None:
        _cache = load_candidates()
    return _cache


def get_by_id(candidate_id: str) -> Optional[Candidate]:
    """Return a single candidate by ID, or None if not found."""
    return next((c for c in get_all() if c.id == candidate_id), None)
