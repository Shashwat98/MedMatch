"""
One-shot script to generate the synthetic clinician pool using Claude.
Run once from the backend/ directory: python generate_candidates.py
Output: data/candidates.json
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = DATA_DIR / "candidates.json"

GENERATION_PROMPT = """Generate a realistic synthetic dataset of 50 healthcare clinicians for a staffing platform demo.

Return a JSON array of exactly 50 objects. Each object must have these exact fields:
- id: string "cand_001" through "cand_050"
- name: full name (diverse names, mix of genders and ethnicities)
- specialty: one of: ICU, ER, Med-Surg, Pediatrics, OR, L&D, Oncology, Cardiology, Neurology, Float
- role: one of: RN, LPN, NP, CNA
- certifications: array of strings, values from: BLS, ACLS, PALS, TNCC, CCRN, NRP, CEN, CNOR, OCN, NIH Stroke Scale
- license_state: two-letter US state code
- license_expiry: date string YYYY-MM-DD
- years_experience: integer 1-25
- availability: array of day names (subset of: Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday)
- last_placement: date string YYYY-MM-DD or null
- rating: float 3.5 to 5.0 with one decimal place
- npi_number: synthetic 10-digit numeric string starting with 1

Dataset constraints (required for demo to work):
- At least 8 candidates with specialty "ICU" and role "RN"
- At least 6 candidates with license_state "MA"
- At least 4 ICU RNs who have both "ACLS" and "BLS" in certifications AND license_state "MA"
- At least 3 of those 4 must have "Saturday" in availability
- Spread candidates across at least 10 different states
- Experience distribution: ~10 with 1-3 years, ~20 with 4-10 years, ~20 with 11+ years
- ~10 candidates with license_expiry between 2025-05-01 and 2025-06-30 (expiring soon)
- Remaining candidates with license_expiry between 2026-01-01 and 2028-12-31
- last_placement dates should be within the last 6 months of 2025-05-01 or null
- All ICU candidates must have at least "BLS"; most should also have "ACLS"
- Each candidate should have 2-5 certifications appropriate to their specialty

Return only the raw JSON array with no markdown fencing, no explanation, nothing else."""


def _strip_markdown(text: str) -> str:
    """Remove ```json ... ``` fencing if Claude wraps the output."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


def generate_candidates() -> list[dict]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in environment")

    client = anthropic.Anthropic(api_key=api_key)

    print("Generating 50 synthetic clinicians via Claude...")
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8192,
        messages=[{"role": "user", "content": GENERATION_PROMPT}],
    )

    raw = _strip_markdown(message.content[0].text)
    candidates: list[dict] = json.loads(raw)

    if len(candidates) != 50:
        print(f"Warning: expected 50 candidates, got {len(candidates)}")

    return candidates


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)

    if OUTPUT_FILE.exists():
        print(f"{OUTPUT_FILE} already exists. Delete it to regenerate.")
        sys.exit(0)

    candidates = generate_candidates()

    with open(OUTPUT_FILE, "w") as f:
        json.dump(candidates, f, indent=2)

    print(f"Saved {len(candidates)} candidates to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
