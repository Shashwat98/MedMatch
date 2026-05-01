# MedMatch — Healthcare Staffing Intelligence Agent

> A multi-agent AI system that takes a plain-English shift requirement and autonomously finds, verifies, and ranks the best-matched clinicians — with every reasoning step shown live.

**Live demo:** [med-match-liart.vercel.app](https://med-match-liart.vercel.app) &nbsp;|&nbsp; **API:** [medmatch-9n51.onrender.com](https://medmatch-9n51.onrender.com/health)

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-1.x-FF6B35)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-7C3AED?logo=anthropic&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript&logoColor=white)
![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3.x-06B6D4?logo=tailwindcss&logoColor=white)

---

## The Problem

Healthcare facilities lose thousands of dollars per unfilled shift, yet the staffing process is still largely manual: a recruiter reads a request, opens a spreadsheet, cross-checks licenses and certifications, calls candidates to confirm availability, and writes up a shortlist. For urgent shifts this process can take hours. MedMatch compresses it to seconds.

---

## Demo

![MedMatch UI screenshot](docs/UI.png)

*A recruiter pastes a shift requirement, watches each agent run in real time in the centre panel, and receives a ranked, reasoned shortlist on the right — all in under 15 seconds.*

---

## What It Does

1. A recruiter types a shift requirement in plain English — *"ICU RN, night shift this Saturday, Boston MA, ACLS + BLS required, urgent"*
2. A **supervisor agent** breaks the task into subtasks and routes them through five specialised sub-agents running in a LangGraph pipeline
3. Each agent streams its progress live to the UI
4. The recruiter receives a ranked shortlist of the top 5 matching clinicians, each with a match score, credential status, availability confirmation, and a one-sentence reasoning

---

## Architecture

```
Recruiter free-text input
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│              LangGraph StateGraph (supervisor)           │
│                                                         │
│  ┌─────────────────────┐                                │
│  │ RequirementParser   │  Claude extracts: specialty,   │
│  │      [LLM]          │  role, certs, location, date,  │
│  └──────────┬──────────┘  urgency → ShiftRequirement    │
│             │                                           │
│  ┌──────────▼──────────┐                                │
│  │  CandidateMatcher   │  Scores all 50 candidates on   │
│  │     [Python]        │  specialty / certs / location  │
│  └──────────┬──────────┘  / experience → top 10        │
│             │                                           │
│  ┌──────────▼──────────┐                                │
│  │ CredentialVerifier  │  Checks licence expiry, required│
│  │     [Python]        │  certs, mock NPI registry →    │
│  └──────────┬──────────┘  VERIFIED / EXPIRING / MISSING │
│             │                                           │
│  ┌──────────▼──────────┐                                │
│  │  AvailabilityAgent  │  Matches shift day-of-week     │
│  │     [Python]        │  against candidate schedule →  │
│  └──────────┬──────────┘  AVAILABLE / CONFLICT         │
│             │                                           │
│  ┌──────────▼──────────┐                                │
│  │    RankingAgent     │  Claude ranks top 5 with a     │
│  │      [LLM]          │  one-sentence reasoning each   │
│  └──────────┬──────────┘                                │
└─────────────┼───────────────────────────────────────────┘
              │  asyncio.Queue → WebSocket stream
    ┌─────────▼──────────────────────┐
    │  FastAPI  ·  POST /match        │
    │           ·  WS  /ws/match      │
    │           ·  GET /candidates    │
    └─────────┬──────────────────────┘
              │
    ┌─────────▼──────────────────────────────────────┐
    │  React Frontend                                 │
    │  [ Shift Input ] [ Live Trace ] [ Shortlist ]   │
    └─────────────────────────────────────────────────┘
```

**Key design decision:** only the first and last agents make LLM calls. The three middle agents are deterministic Python — faster, cheaper, and fully auditable. Claude is used where judgment is required (parsing ambiguous language, writing per-candidate reasoning), not where rules suffice.

---

## Running Locally

### Prerequisites
- Python 3.11+
- Node.js 18+
- An [Anthropic API key](https://console.anthropic.com/)

### Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp ../.env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# Generate the synthetic candidate pool (one-time, ~10 seconds)
python generate_candidates.py

# Start the API server
uvicorn api:app --reload --port 8000
```

### Frontend

```bash
# In a new terminal
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The backend must be running on port 8000.

### Sample prompt to try

```
Looking for an ICU RN for a night shift this Saturday in Boston, MA.
Must have ACLS and BLS certifications. At least 2 years of ICU experience
preferred. This is urgent — facility is short-staffed.
```

Expected result: ranked list of 5 ICU RNs, all ACLS/BLS verified, available Saturday nights, sorted by experience and rating with one-line reasoning per candidate.

---

## How the Pipeline Works

| Agent | What it does | Uses LLM? |
|---|---|---|
| **RequirementParser** | Extracts specialty, role, certifications, location, shift day, urgency from free text | ✅ Claude |
| **CandidateMatcher** | Scores all 50 candidates against the requirement (specialty 40%, certs 25%, location 25%, experience 10%) | ❌ |
| **CredentialVerifier** | Checks licence expiry, verifies required certs are held, runs a mock NPI registry lookup | ❌ |
| **AvailabilityAgent** | Matches the requested shift day-of-week against each candidate's availability schedule | ❌ |
| **RankingAgent** | Ranks the top 5 verified, available candidates and writes a one-sentence reasoning for each placement | ✅ Claude |

Each agent appends a log line to the shared `AgentState.execution_trace`, which streams to the frontend via WebSocket as the pipeline runs.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | Claude Sonnet 4.6 (Anthropic) |
| Agent orchestration | LangGraph `StateGraph` |
| Backend framework | FastAPI + Uvicorn |
| Real-time streaming | WebSocket (`asyncio.Queue` → WS push) |
| Data validation | Pydantic v2 |
| Frontend | React 18 + TypeScript + Vite |
| Styling | Tailwind CSS v3 |
| Icons | Lucide React |
| Deployment | Vercel (frontend) + Railway (backend) |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Liveness check |
| `GET` | `/candidates` | Full synthetic candidate pool |
| `POST` | `/match` | Run pipeline, return shortlist (non-streaming) |
| `WS` | `/ws/match` | Run pipeline, stream trace live, return result |

**WebSocket protocol:**

```
Client → server:  { "requirement": "<free-text>" }
Server → client:  { "type": "trace",  "message": "..." }   (×N, one per agent)
                  { "type": "done",   "result":  { shortlist, trace, ... } }
                  { "type": "error",  "message": "..." }
```

---

## Project Structure

```
MedMatch/
├── backend/
│   ├── agents/
│   │   ├── requirement_parser.py    # LLM → ShiftRequirement
│   │   ├── matcher_agent.py         # deterministic scoring
│   │   ├── credential_verifier.py   # licence + cert checks
│   │   ├── availability_agent.py    # shift-day matching
│   │   └── ranking_agent.py         # LLM → ranked shortlist
│   ├── data/
│   │   └── candidates.json          # generated, git-ignored
│   ├── models.py                    # all Pydantic models
│   ├── candidate_store.py           # in-memory candidate pool
│   ├── supervisor.py                # LangGraph StateGraph
│   ├── api.py                       # FastAPI app
│   ├── generate_candidates.py       # one-shot data generation
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── ShiftInput.tsx
│       │   ├── ExecutionTrace.tsx   # live streaming log
│       │   └── CandidateCard.tsx    # expandable, colour-coded
│       ├── hooks/usePipeline.ts     # WebSocket state manager
│       ├── types.ts
│       └── App.tsx
├── .env.example
└── README.md
```
