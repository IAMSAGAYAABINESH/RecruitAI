"""
AI Recruitment Screening Bot — POC
Single file, minimal UI, runs with: streamlit run app.py
Requires: pip install streamlit pdfplumber google-generativeai python-dotenv
"""

import io
import json
import os
import re

import google.generativeai as genai
import pdfplumber
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="RecruitAI",
    page_icon="🎯",
    layout="centered",
)

st.markdown("""
<style>
    /* Clean minimal look */
    .block-container { padding-top: 2rem; max-width: 800px; }

    /* AI message bubble */
    .bubble-ai {
        background: #1e2535;
        border-left: 3px solid #4f8ef7;
        padding: 12px 16px;
        border-radius: 0 10px 10px 10px;
        margin: 8px 0;
        font-size: 15px;
        color: #e2e8f0;
    }
    /* User message bubble */
    .bubble-user {
        background: #1a2e1a;
        border-left: 3px solid #28a745;
        padding: 12px 16px;
        border-radius: 0 10px 10px 10px;
        margin: 8px 0;
        font-size: 15px;
        color: #e2e8f0;
    }
    .role-label {
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        color: #888;
        margin-bottom: 4px;
    }
    .phase-tag {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
def init_state():
    defaults = {
        "phase": "setup",               # setup | skill_check | interview | done
        "resume_text": "",
        "jd_text": "",
        "orphan_skills": [],            # skills listed but not used in experience
        "unverified_skills": [],        # skills that failed justification
        "current_skill_idx": 0,
        "skill_attempts": 0,            # attempts for current skill
        "justified_skills": {},         # skill -> justification or "UNVERIFIED"
        "chat_history": [],             # [{"role": "ai"|"user", "content": "..."}]
        "api_key": os.getenv("GEMINI_API_KEY", ""),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def get_model():
    """Configure and return the Gemini model."""
    genai.configure(api_key=st.session_state.api_key)
    return genai.GenerativeModel("gemini-3.1-flash-lite")


def ask_gemini(prompt: str) -> str:
    """Single-shot call to Gemini. Returns plain text."""
    model = get_model()
    response = model.generate_content(prompt)
    return response.text.strip()


def parse_resume(uploaded_file) -> str:
    """Extract all text from a PDF resume."""
    pdf_bytes = uploaded_file.read()
    pages = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text.strip())
    return "\n\n".join(pages)


def detect_orphan_skills(resume_text: str) -> list:
    """Ask Gemini to find skills listed but not used in experience/projects."""
    prompt = f"""
You are a resume parser. Analyse the resume below.

Return ONLY a valid JSON object with these exact keys:
- "listed_skills": skills explicitly named in a Skills or Technologies section
- "used_skills": skills that appear in Work Experience or Projects sections
- "orphan_skills": skills in listed_skills that do NOT appear in work/projects

Rules:
- Normalise names (python -> Python, reactjs -> React)
- Be conservative — only flag a skill as orphan if you are confident it's truly absent from experience
- Return ONLY the JSON. No markdown, no explanation, no code fences.

Resume:
{resume_text}
"""
    raw = ask_gemini(prompt)
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
    try:
        data = json.loads(cleaned)
        return data.get("orphan_skills", [])
    except json.JSONDecodeError:
        return []  # if parsing fails, skip skill check and go straight to interview


def format_history(history: list) -> str:
    """Format chat history as plain text for inclusion in prompts."""
    lines = []
    for msg in history:
        role = "Interviewer" if msg["role"] == "ai" else "Candidate"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


def render_chat(history: list):
    """Render all messages in the chat history."""
    for msg in history:
        if msg["role"] == "ai":
            st.markdown(f'<div class="role-label">🤖 Interviewer</div><div class="bubble-ai">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="role-label">🧑 You</div><div class="bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)


def add_msg(role: str, content: str):
    """Append a message to chat history."""
    st.session_state.chat_history.append({"role": role, "content": content})


# ─────────────────────────────────────────────
# AI FUNCTIONS
# ─────────────────────────────────────────────
def ask_skill_question(skill: str) -> str:
    prompt = f"""
You are a professional technical recruiter doing a pre-screening call.

The candidate listed "{skill}" in their skills section but it does not appear
anywhere in their work experience or projects.

Ask them ONE focused question: where and how did they use this skill?
Be direct but polite. One question only.
"""
    return ask_gemini(prompt)


def evaluate_skill_answer(skill: str, answer: str, history: list) -> tuple[str, bool]:
    prompt = f"""
You are a technical recruiter evaluating a candidate's justification for a skill.

Skill: {skill}
Conversation so far:
{format_history(history)}

Candidate's latest answer: "{answer}"

Decide if this is a satisfactory explanation (concrete usage, real context, some outcome).

If YES: acknowledge briefly in 1-2 sentences, then add exactly: [ACCEPTED]
If NO: ask ONE sharp follow-up question. Do NOT add [ACCEPTED].

Be concise and professional.
"""
    raw = ask_gemini(prompt)
    accepted = "[ACCEPTED]" in raw
    clean = raw.replace("[ACCEPTED]", "").strip()
    return clean, accepted


def start_interview() -> str:
    # Build a summary of what we know about their skills
    skill_notes = ""
    if st.session_state.justified_skills:
        lines = []
        for skill, note in st.session_state.justified_skills.items():
            if note == "UNVERIFIED":
                lines.append(f"  - {skill}: could not justify (flag for follow-up)")
            else:
                lines.append(f"  - {skill}: verified — {note[:150]}")
        skill_notes = "Pre-screening skill notes:\n" + "\n".join(lines)

    prompt = f"""
You are an experienced technical interviewer conducting a structured interview.

Candidate Resume (excerpt):
{st.session_state.resume_text[:3000]}

Job Description:
{st.session_state.jd_text[:2000]}

{skill_notes}

Instructions:
- Ask relevant questions based on the JD and the candidate's background
- Mix technical and behavioural questions
- If the candidate asks about the role or JD, answer honestly from the JD then continue
- Ask ONE question at a time
- Do NOT mention scores or evaluations

Start with a brief, warm opening and your first question.
"""
    return ask_gemini(prompt)


def interview_turn(user_message: str) -> str:
    prompt = f"""
You are an experienced technical interviewer. Continue the interview below.

Candidate Resume (excerpt):
{st.session_state.resume_text[:3000]}

Job Description:
{st.session_state.jd_text[:2000]}

Conversation so far:
{format_history(st.session_state.chat_history)}

Instructions:
- If the candidate answered your question: acknowledge briefly, then ask your next question or probe deeper
- If the candidate asked about the role or JD: answer from the JD, then return to interviewing
- ONE question at a time. Don't repeat earlier questions.
- After 8-10 exchanges total, wrap up the interview professionally.
"""
    return ask_gemini(prompt)


# ─────────────────────────────────────────────
# UI — SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎯 RecruitAI")
    st.caption("AI-powered screening POC")
    st.divider()

    api_input = st.text_input(
        "Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder="AIza...",
        help="Free key from aistudio.google.com",
    )
    if api_input:
        st.session_state.api_key = api_input

    st.divider()

    # Phase indicator
    phase_colors = {
        "setup":      ("⚙️ Setup",      "#888"),
        "skill_check":("🔍 Skill Check", "#e67e22"),
        "interview":  ("🎤 Interview",   "#2980b9"),
        "done":       ("✅ Complete",    "#27ae60"),
    }
    label, color = phase_colors[st.session_state.phase]
    st.markdown(f'<span class="phase-tag" style="background:{color}22;color:{color};border:1px solid {color}44">{label}</span>', unsafe_allow_html=True)

    if st.session_state.orphan_skills:
        st.divider()
        st.caption("Skills to verify:")
        for i, skill in enumerate(st.session_state.orphan_skills):
            note = st.session_state.justified_skills.get(skill)
            if note == "UNVERIFIED":
                st.markdown(f"❌ {skill}")
            elif note:
                st.markdown(f"✅ {skill}")
            elif i == st.session_state.current_skill_idx:
                st.markdown(f"🔍 **{skill}**")
            else:
                st.markdown(f"⏳ {skill}")

    st.divider()
    if st.button("🔄 Reset", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


# ─────────────────────────────────────────────
# PHASE 1 — SETUP
# ─────────────────────────────────────────────
if st.session_state.phase == "setup":
    st.title("AI Recruitment Screening")
    st.caption("Upload a resume and job description to begin.")
    st.divider()

    resume_file = st.file_uploader("📄 Upload Resume (PDF)", type=["pdf"])
    if resume_file:
        with st.spinner("Reading resume..."):
            st.session_state.resume_text = parse_resume(resume_file)
        st.success(f"Resume parsed — {len(st.session_state.resume_text.split())} words.")

    st.session_state.jd_text = st.text_area(
        "📋 Paste Job Description",
        value=st.session_state.jd_text,
        height=180,
        placeholder="We are looking for a Python engineer with experience in FastAPI...",
    )

    st.divider()

    ready = st.session_state.resume_text and st.session_state.jd_text and st.session_state.api_key

    if not ready:
        missing = []
        if not st.session_state.api_key:     missing.append("API key")
        if not st.session_state.resume_text: missing.append("resume")
        if not st.session_state.jd_text:     missing.append("job description")
        st.info(f"Still needed: {', '.join(missing)}")

    if st.button("Analyse & Start →", disabled=not ready, type="primary", use_container_width=True):
        with st.spinner("Analysing resume for skill gaps..."):
            orphans = detect_orphan_skills(st.session_state.resume_text)
            st.session_state.orphan_skills = orphans
            st.session_state.current_skill_idx = 0
            st.session_state.skill_attempts = 0

        if orphans:
            st.session_state.phase = "skill_check"
            with st.spinner("Preparing first question..."):
                first_q = ask_skill_question(orphans[0])
            add_msg("ai", first_q)
        else:
            st.session_state.phase = "interview"
            with st.spinner("Starting interview..."):
                opening = start_interview()
            add_msg("ai", opening)

        st.rerun()


# ─────────────────────────────────────────────
# PHASE 2 — SKILL CHECK
# ─────────────────────────────────────────────
elif st.session_state.phase == "skill_check":
    idx = st.session_state.current_skill_idx
    orphans = st.session_state.orphan_skills
    current_skill = orphans[idx] if idx < len(orphans) else None
    MAX_ATTEMPTS = 3

    st.title("Skill Verification")
    if current_skill:
        attempts_left = MAX_ATTEMPTS - st.session_state.skill_attempts
        st.caption(f"Verifying: **{current_skill}** — {attempts_left} attempt(s) remaining")
    st.divider()

    render_chat(st.session_state.chat_history)
    st.divider()

    user_input = st.text_input(
        "Your answer",
        placeholder="Explain where and how you used this skill...",
        key=f"skill_input_{idx}_{st.session_state.skill_attempts}",
        label_visibility="collapsed",
    )

    if st.button("Send →", type="primary", key=f"send_skill_{idx}"):
        if user_input.strip():
            add_msg("user", user_input)
            st.session_state.skill_attempts += 1

            with st.spinner("Evaluating..."):
                response, accepted = evaluate_skill_answer(
                    skill=current_skill,
                    answer=user_input,
                    history=st.session_state.chat_history,
                )

            add_msg("ai", response)

            def move_to_next_skill():
                """Move to the next orphan skill or transition to interview."""
                next_idx = st.session_state.current_skill_idx + 1
                st.session_state.current_skill_idx = next_idx
                st.session_state.skill_attempts = 0

                if next_idx >= len(orphans):
                    # All skills processed — start interview
                    st.session_state.phase = "interview"
                    with st.spinner("Starting interview..."):
                        opening = start_interview()
                    add_msg("ai", opening)
                else:
                    # Ask about next skill
                    next_skill = orphans[next_idx]
                    with st.spinner("Preparing next question..."):
                        next_q = ask_skill_question(next_skill)
                    add_msg("ai", next_q)

            if accepted:
                st.session_state.justified_skills[current_skill] = user_input
                move_to_next_skill()
            elif st.session_state.skill_attempts >= MAX_ATTEMPTS:
                # Cap reached — mark unverified and move on
                st.session_state.justified_skills[current_skill] = "UNVERIFIED"
                st.session_state.unverified_skills.append(current_skill)
                add_msg("ai", f"Let's move on. We'll note that **{current_skill}** couldn't be verified and flag it for the hiring team.")
                move_to_next_skill()

            st.rerun()


# ─────────────────────────────────────────────
# PHASE 3 — INTERVIEW
# ─────────────────────────────────────────────
elif st.session_state.phase == "interview":
    st.title("Live Interview")
    st.caption("Answer questions or ask about the role — it's a two-way conversation.")
    st.divider()

    render_chat(st.session_state.chat_history)
    st.divider()

    col1, col2 = st.columns([5, 1])

    with col1:
        user_input = st.text_input(
            "Your message",
            placeholder="Type your answer, or ask something about the role...",
            key="interview_input",
            label_visibility="collapsed",
        )
    with col2:
        send = st.button("Send →", type="primary", use_container_width=True)

    end_col, _ = st.columns([2, 3])
    with end_col:
        end = st.button("End Interview", use_container_width=True)

    if send and user_input.strip():
        add_msg("user", user_input)
        with st.spinner("Thinking..."):
            response = interview_turn(user_input)
        add_msg("ai", response)
        st.rerun()

    if end:
        st.session_state.phase = "done"
        st.rerun()


# ─────────────────────────────────────────────
# PHASE 4 — TRANSCRIPT
# ─────────────────────────────────────────────
elif st.session_state.phase == "done":
    st.title("Interview Complete")
    st.success("Screening session finished.")
    st.divider()

    # Skill summary
    if st.session_state.justified_skills:
        st.markdown("#### Skill Verification Summary")
        for skill, note in st.session_state.justified_skills.items():
            if note == "UNVERIFIED":
                st.markdown(f"❌ **{skill}** — could not justify")
            else:
                st.markdown(f"✅ **{skill}** — verified")
        st.divider()

    # Full transcript
    st.markdown("#### Full Interview Transcript")
    for msg in st.session_state.chat_history:
        if msg["role"] == "ai":
            st.markdown(f'<div class="role-label">🤖 Interviewer</div><div class="bubble-ai">{msg["content"]}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="role-label">🧑 Candidate</div><div class="bubble-user">{msg["content"]}</div>', unsafe_allow_html=True)

    st.divider()

    # Download transcript
    transcript_lines = []
    for msg in st.session_state.chat_history:
        role = "INTERVIEWER" if msg["role"] == "ai" else "CANDIDATE"
        transcript_lines.append(f"{role}:\n{msg['content']}\n")
    transcript_text = "\n---\n".join(transcript_lines)

    st.download_button(
        label="⬇️ Download Transcript",
        data=transcript_text,
        file_name="interview_transcript.txt",
        mime="text/plain",
        use_container_width=True,
    )
