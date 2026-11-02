from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (importing registers the tables)
from app.applications import router as applications_router
from app.auth import router as auth_router
from app.database import Base, engine
from app.deps import get_current_user
from app.llm import usage
from app.models import User
from app.profiles import router as profiles_router

app = FastAPI(title="Career Copilot")

Base.metadata.create_all(bind=engine)

# Let the React dev server (Vite's default port, plus 3000) call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(applications_router)


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/usage")
def get_usage(_: User = Depends(get_current_user)):
    return usage()