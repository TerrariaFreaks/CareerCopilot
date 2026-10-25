.\.venv\Scripts\Activate.ps1

# Career Copilot

<!-- TODO (you): one-sentence tagline. What does it do, for whom? -->

## Why I'm building this

<!-- TODO (you): 2-3 sentences in your own voice. What problem did you hit
     while job hunting? Why an agent instead of a plain prompt? -->

## What it does

1. Store your full career history once as a master profile
2. Paste a job link or description
3. An AI agent analyzes the job, drafts a tailored resume, critiques it
   against the job and your real experience, then revises it
4. Review the result, with any claim the agent couldn't back up flagged
5. Track the application in a kanban board and export the resume

## Principles

- **No fabrication.** The agent only uses facts from your profile
- **Human in the loop.** Nothing is final until you review it
- **Free to run.** Built on free-tier APIs, with usage caps so I never hit quota walls

## Tech stack

| Layer | Choice |
|-------|--------|
| Frontend | React + Tailwind |
| Backend | FastAPI (Python) |
| Database | SQLite for dev, Postgres later |
| Agent | Gemini API |
| Auth | TBD |

## Roadmap

- [ ] Phase 1: Backend agent loop (analyze, draft, critique, revise)
- [ ] Phase 2: Database and auth
- [ ] Phase 3: React frontend
- [ ] Phase 4: Live streaming of agent steps
- [ ] Phase 5: Application tracker and export
- [ ] Phase 6: Deploy

## Running locally

<!-- TODO (later): fill in once there is something to run -->

## What I'm learning

<!-- TODO (optional, later): notes on what you learned at each phase -->