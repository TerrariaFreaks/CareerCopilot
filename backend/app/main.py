from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google.genai import errors
from pydantic import BaseModel, Field

from app.agent import run_agent
from app.llm import QuotaExceeded, usage

from app.database import Base, engine
import app.models  # noqa: F401  (importing registers the tables)

app = FastAPI(title="Career Copilot")

Base.metadata.create_all(bind=engine)

# Let the React dev server (Vite's default port, plus 3000) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class TailorRequest(BaseModel):
    profile: str = Field(min_length=50)
    job: str = Field(min_length=50)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/usage")
def get_usage():
    return usage()


@app.post("/api/tailor")
def tailor(req: TailorRequest):
    events = []
    try:
        for event in run_agent(req.profile, req.job):
            events.append(event)
    except QuotaExceeded as e:
        raise HTTPException(status_code=429, detail=str(e))
    except errors.APIError as e:
        raise HTTPException(status_code=502, detail=f"Gemini API error ({e.code}). Try again shortly.")
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    result = events[-1]
    return {"resume": result["resume"], "flags": result["flags"], "steps": events[:-1]}