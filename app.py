import streamlit as st
import os
from resume_parser import extract_text_from_pdf
from skill_analyzer import analyze_skills
from chat_engine import ChatEngine

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Recruitment Interview",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Space+Grotesk:wght@500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .main { background: #0f1117; }

    .stApp {
        background: linear-gradient(135deg, #0f1117 0%, #1a1f2e 100%);
        color: #e2e8f0;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #161b27;
        border-right: 1px solid #2d3748;
    }

    /* Phase badge */
    .phase-badge {
        display: inline-block;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 12px;
    }
    .phase-setup    { background: #2d3748; color: #a0aec0; }
    .phase-skill    { background: #1a2a1a; color: #68d391; border: 1px solid #276749; }
    .phase-interview{ background: #1a1f3a; color: #76e4f7; border: 1px solid #2b6cb0; }

    /* Chat bubbles */
    .chat-bubble-ai {
        background: #1e2535;
        border: 1px solid #2d3748;
        border-left: 3px solid #667eea;
        border-radius: 0 12px 12px 12px;
        padding: 12px 16px;
        margin: 8px 0 8px 0;
        max-width: 85%;
        color: #e2e8f0;
        font-size: 14px;
        line-height: 1.6;
    }
    .chat-bubble-user {
        background: #2a3a5c;
        border: 1px solid #3a5282;
        border-radius: 12px 0 12px 12px;
        padding: 12px 16px;
        margin: 8px 0 8px auto;
        max-width: 75%;
        color: #e2e8f0;
        font-size: 14px;
        line-height: 1.6;
        text-align: right;
    }
    .chat-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
        margin-bottom: 4px;
    }
    .label-ai   { color: #667eea; }
    .label-user { color: #76e4f7; text-align: right; }

    /* Skill pill */
    .skill-pill {
        display: inline-block;
        background: #2d2a1a;
        border: 1px solid #744210;
        color: #f6ad55;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        margin: 3px;
    }
    .skill-pill-ok {
        display: inline-block;
        background: #1a2a1a;
        border: 1px solid #276749;
        color: #68d391;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        margin: 3px;
    }

    /* Section header */
    .section-header {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 22px;
        font-weight: 700;
        color: #f7fafc;
        margin-bottom: 4px;
    }
    .section-sub {
        font-size: 13px;
        color: #718096;
        margin-bottom: 20px;
    }

    /* Divider */
    .fancy-divider {
        height: 1px;
        background: linear-gradient(90deg, #667eea33, #764ba233, transparent);
        margin: 20px 0;
    }

    /* Progress bar override */
    .stProgress > div > div {
        background: linear-gradient(90deg, #667eea, #764ba2);
    }

    /* Input */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #1e2535 !important;
        border: 1px solid #2d3748 !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
    }

    /* Button */
    .stButton > button {
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 24px;
        transition: opacity 0.2s;
    }
    .stButton > button:hover { opacity: 0.85; }

    /* File uploader */
    [data-testid="stFileUploader"] {
        background: #1e2535;
        border: 1px dashed #4a5568;
        border-radius: 10px;
        padding: 10px;
    }

    /* Info boxes */
    .info-box {
        background: #1a2535;
        border: 1px solid #2d4a6a;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 10px 0;
        font-size: 13px;
        color: #a0c4e8;
    }
    .warning-box {
        background: #2a1f10;
        border: 1px solid #744210;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 10px 0;
        font-size: 13px;
        color: #f6ad55;
    }
    .success-box {
        background: #0f2a1a;
        border: 1px solid #276749;
        border-radius: 10px;
        padding: 14px 18px;
        margin: 10px 0;
        font-size: 13px;
        color: #68d391;
    }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "phase": "setup",           # setup → skill_justification → interview
        "resume_text": "",
        "jd_text": "",
        "skill_analysis": None,     # {listed, used, orphan}
        "orphan_skills": [],
        "current_orphan_idx": 0,
        "justified_skills": {},     # skill → justification text
        "chat_history": [],         # [{role, content}]
        "engine": None,
        "api_key": os.getenv("GEMINI_API_KEY", ""),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-header">🎯 RecruitAI</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">AI-powered screening assistant</div>', unsafe_allow_html=True)
    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    # API Key
    api_key_input = st.text_input(
        "Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        placeholder="AIza...",
        help="Free key from aistudio.google.com",
    )
    if api_key_input:
        st.session_state.api_key = api_key_input

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    # Phase indicator
    phase_labels = {
        "setup": ("Setup", "phase-setup"),
        "skill_justification": ("Skill Check", "phase-skill"),
        "interview": ("Live Interview", "phase-interview"),
    }
    label, cls = phase_labels[st.session_state.phase]
    st.markdown(f'<div class="phase-badge {cls}">{label}</div>', unsafe_allow_html=True)

    if st.session_state.phase == "skill_justification":
        total = len(st.session_state.orphan_skills)
        done = st.session_state.current_orphan_idx
        st.progress(done / total if total else 1.0)
        st.caption(f"Verifying skill {done}/{total}")

    if st.session_state.phase == "interview":
        msgs = len([m for m in st.session_state.chat_history if m["role"] == "interviewer"])
        st.caption(f"Questions asked: {msgs}")

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    # Skill summary panel
    if st.session_state.skill_analysis:
        sa = st.session_state.skill_analysis
        st.markdown("**Skill Analysis**")
        st.markdown(
            "".join(f'<span class="skill-pill-ok">{s}</span>' for s in sa.get("used_skills", [])),
            unsafe_allow_html=True,
        )
        if sa.get("orphan_skills"):
            st.markdown("**Unverified Skills**")
            st.markdown(
                "".join(f'<span class="skill-pill">{s}</span>' for s in sa.get("orphan_skills", [])),
                unsafe_allow_html=True,
            )

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)
    if st.button("🔄 Reset Session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ── Helper: render chat ───────────────────────────────────────────────────────
def render_chat(history):
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        if role in ("interviewer", "ai"):
            st.markdown(f'<div class="chat-label label-ai">🤖 Interviewer</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-bubble-ai">{content}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="chat-label label-user">You</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="chat-bubble-user">{content}</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1: SETUP
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.phase == "setup":
    st.markdown('<div class="section-header">Upload & Configure</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-sub">Provide the resume and job description to begin the screening process.</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown("#### 📄 Resume")
        resume_file = st.file_uploader("Upload PDF resume", type=["pdf"], key="resume_uploader")
        if resume_file:
            with st.spinner("Parsing resume..."):
                text = extract_text_from_pdf(resume_file)
                st.session_state.resume_text = text
            st.markdown(
                f'<div class="success-box">✅ Resume parsed — {len(text.split())} words extracted.</div>',
                unsafe_allow_html=True,
            )
            with st.expander("Preview extracted text"):
                st.text(text[:2000] + ("..." if len(text) > 2000 else ""))

    with col2:
        st.markdown("#### 📋 Job Description")
        jd_input = st.text_area(
            "Paste the job description here",
            height=220,
            placeholder="We are looking for a Senior Python Engineer with experience in FastAPI, LLMs, and cloud deployment...",
            key="jd_input",
        )
        if jd_input:
            st.session_state.jd_text = jd_input

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    ready = st.session_state.resume_text and st.session_state.jd_text and st.session_state.api_key
    if not ready:
        missing = []
        if not st.session_state.api_key:    missing.append("Gemini API key (sidebar)")
        if not st.session_state.resume_text: missing.append("resume PDF")
        if not st.session_state.jd_text:    missing.append("job description")
        st.markdown(
            f'<div class="info-box">ℹ️ Still needed: {", ".join(missing)}.</div>',
            unsafe_allow_html=True,
        )

    if st.button("Analyse & Start →", disabled=not ready):
        with st.spinner("Analysing resume with AI..."):
            engine = ChatEngine(
                api_key=st.session_state.api_key,
                resume_text=st.session_state.resume_text,
                jd_text=st.session_state.jd_text,
            )
            st.session_state.engine = engine
            analysis = analyze_skills(
                engine,
                st.session_state.resume_text,
            )
            st.session_state.skill_analysis = analysis
            orphans = analysis.get("orphan_skills", [])
            st.session_state.orphan_skills = orphans
            st.session_state.current_orphan_idx = 0

        if orphans:
            st.session_state.phase = "skill_justification"
            # Seed first question
            first_q = engine.ask_skill_justification(orphans[0])
            st.session_state.chat_history = [{"role": "interviewer", "content": first_q}]
        else:
            st.session_state.phase = "interview"
            opening = engine.start_interview()
            st.session_state.chat_history = [{"role": "interviewer", "content": opening}]

        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2: SKILL JUSTIFICATION
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "skill_justification":
    orphans = st.session_state.orphan_skills
    idx = st.session_state.current_orphan_idx
    current_skill = orphans[idx] if idx < len(orphans) else None

    st.markdown('<div class="section-header">Skill Verification</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="section-sub">You listed skills that aren\'t visible in your work history. Let\'s verify them before the interview.</div>',
        unsafe_allow_html=True,
    )

    if current_skill:
        st.markdown(
            f'<div class="warning-box">⚠️ Verifying: <strong>{current_skill}</strong> — skill listed but not found in work experience or projects.</div>',
            unsafe_allow_html=True,
        )

    render_chat(st.session_state.chat_history)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    with st.container():
        user_input = st.text_input(
            "Your response",
            placeholder="Explain where and how you used this skill...",
            key=f"skill_input_{idx}",
            label_visibility="collapsed",
        )
        col_send, col_skip = st.columns([1, 5])
        with col_send:
            send = st.button("Send →", key="send_skill")

    if send and user_input.strip():
        engine: ChatEngine = st.session_state.engine
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.spinner("Evaluating..."):
            response, accepted = engine.evaluate_skill_justification(
                skill=current_skill,
                user_response=user_input,
                history=st.session_state.chat_history,
            )

        st.session_state.chat_history.append({"role": "interviewer", "content": response})

        if accepted:
            st.session_state.justified_skills[current_skill] = user_input
            next_idx = idx + 1
            st.session_state.current_orphan_idx = next_idx

            if next_idx >= len(orphans):
                # All skills verified — move to interview
                opening = engine.start_interview(
                    justified_skills=st.session_state.justified_skills
                )
                st.session_state.chat_history = [{"role": "interviewer", "content": opening}]
                st.session_state.phase = "interview"
            else:
                # Next skill
                next_skill = orphans[next_idx]
                next_q = engine.ask_skill_justification(next_skill)
                st.session_state.chat_history.append({"role": "interviewer", "content": next_q})

        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3: INTERVIEW
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "interview":
    st.markdown('<div class="section-header">Live Interview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">A two-way conversation — answer the interviewer\'s questions or ask your own about the role.</div>',
        unsafe_allow_html=True,
    )

    render_chat(st.session_state.chat_history)

    st.markdown('<div class="fancy-divider"></div>', unsafe_allow_html=True)

    user_input = st.text_input(
        "Your message",
        placeholder="Answer the question, or ask something about the role...",
        key="interview_input",
        label_visibility="collapsed",
    )
    st.button_send = st.button("Send →", key="send_interview")

    if st.button_send and user_input.strip():
        engine: ChatEngine = st.session_state.engine
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        with st.spinner("Thinking..."):
            response = engine.interview_turn(
                user_message=user_input,
                history=st.session_state.chat_history,
            )

        st.session_state.chat_history.append({"role": "interviewer", "content": response})
        st.rerun()
