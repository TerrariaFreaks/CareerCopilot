import json

from app.llm import ask

RULES = (
    "STRICT RULES: Use ONLY facts present in the candidate profile. Never invent "
    "employers, titles, dates, skills, tools, or numbers. If the job wants something "
    "the profile does not show, leave it out rather than guess. "
    "Do not add praise or intensity words (such as robust, efficient, comprehensive, "
    "critical, strong, proficient) and do not state skill levels the profile does not "
    "state. Describe what was done and any measurable result, nothing more. "
    "If the profile lacks a detail (contact info, university name), omit that line "
    "entirely. Never write placeholder text like [Not Provided]. "
    "Only list a keyword in Skills if the profile supports it."
)

def parse_json(raw):
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"raw": raw}


def run_agent(profile, job):
    # Step 1: analyze the job posting
    yield {"step": "analyze", "status": "running"}
    analysis = parse_json(ask(
        "You analyze job postings. Reply with JSON only.",
        "Extract a JSON object with keys: role_title, seniority, required_skills (list), "
        "nice_to_have (list), keywords (list), responsibilities (short list).\n\nJOB:\n" + job,
        json_mode=True,
    ))
    yield {"step": "analyze", "status": "done", "data": analysis}

    # Step 2: draft a tailored resume
    yield {"step": "draft", "status": "running"}
    draft = ask(
        "You are an expert resume writer. " + RULES,
        f"CANDIDATE PROFILE:\n{profile}\n\nJOB ANALYSIS:\n{json.dumps(analysis)}\n\n"
        "Write a tailored one-page resume in Markdown. Lead with the most relevant "
        "experience, use strong action verbs, keep bullets concise, and mirror the "
        "job's keywords only where the profile supports them.",
    )
    yield {"step": "draft", "status": "done"}

    # Step 3: critique the draft
    yield {"step": "critique", "status": "running"}
    critique = parse_json(ask(
        "You are a strict recruiter and fact-checker. Reply with JSON only.",
        f"JOB ANALYSIS:\n{json.dumps(analysis)}\n\nCANDIDATE PROFILE:\n{profile}\n\n"
        f"RESUME DRAFT:\n{draft}\n\n"
        "Return JSON with keys: "
        "weaknesses (list of problems that can be fixed by rewording or reordering only; "
        "ignore skills the candidate genuinely lacks), "
        "missing_keywords (only job keywords the PROFILE actually supports), "
        "unsupported_claims (any resume statement not backed by the profile, including "
        "exaggerating adjectives, skill levels like 'proficient', placeholder text, "
        "and impact claims the profile does not make).",
        json_mode=True,
    ))
    yield {"step": "critique", "status": "done", "data": critique}

    # Step 4: revise using the critique
    yield {"step": "revise", "status": "running"}
    final = ask(
        "You are an expert resume writer. " + RULES,
        f"CANDIDATE PROFILE:\n{profile}\n\nDRAFT:\n{draft}\n\n"
        f"CRITIQUE:\n{json.dumps(critique)}\n\n"
        "Produce the final resume in Markdown. Fix the weaknesses, remove every "
        "unsupported claim, and add missing keywords only if the profile supports them.",
    )
    yield {"step": "revise", "status": "done"}

    yield {"step": "result", "resume": final, "flags": critique.get("unsupported_claims", [])}