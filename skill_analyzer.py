"""
skill_analyzer.py
-----------------
Sends the resume to Gemini and returns a structured breakdown of:
  - listed_skills  : skills declared in a skills/technologies section
  - used_skills    : skills that appear organically in work experience / projects
  - orphan_skills  : listed but never demonstrated anywhere in the resume
"""

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chat_engine import ChatEngine

ANALYSIS_PROMPT = """
You are a precise resume parser. Analyse the resume text below and return a JSON object with exactly these three keys:

- "listed_skills"   : list of skills explicitly named in any 'Skills', 'Technologies', 'Tools', or similar section
- "used_skills"     : list of skills that appear in Work Experience, Projects, Internships, or similar sections (not just listed)
- "orphan_skills"   : skills that are in listed_skills but do NOT appear anywhere in the work/project sections

Rules:
  1. Normalise skill names (e.g. "python" → "Python", "reactjs" → "React").
  2. Be conservative — only flag a skill as an orphan if you are confident it is truly absent from the experience sections.
  3. Return ONLY the JSON object, no markdown, no explanation, no code fences.

Resume:
{resume_text}
"""


def analyze_skills(engine: "ChatEngine", resume_text: str) -> dict:
    """
    Call the LLM to extract skill categories from a resume.

    Returns:
        dict with keys: listed_skills, used_skills, orphan_skills
    """
    prompt = ANALYSIS_PROMPT.format(resume_text=resume_text)

    raw = engine.raw_generate(prompt)

    # Strip accidental markdown fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()

    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: return empty analysis so the app still runs
        result = {
            "listed_skills": [],
            "used_skills": [],
            "orphan_skills": [],
            "_parse_error": cleaned[:300],
        }

    # Ensure all three keys exist
    for key in ("listed_skills", "used_skills", "orphan_skills"):
        if key not in result:
            result[key] = []

    return result
