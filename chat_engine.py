"""
chat_engine.py
--------------
All Gemini API calls live here.
Three responsibilities:
  1. raw_generate()           — one-shot generation (skill analysis)
  2. ask/evaluate skill       — Phase 2 skill justification loop
  3. start_interview()        — Phase 3 opening question
  4. interview_turn()         — Phase 3 multi-turn conversation
"""

import google.generativeai as genai


# ── Prompts ───────────────────────────────────────────────────────────────────

SKILL_JUSTIFICATION_PROMPT = """
You are a sharp but professional technical recruiter conducting a pre-screening call.

The candidate's resume lists the skill "{skill}" but it does not appear in any work experience or project section.

Ask the candidate to explain:
- Where specifically they used this skill
- In what context or project
- What they built or achieved with it

Be direct but polite. Ask one focused question. Do not ask multiple questions at once.
"""

SKILL_EVALUATION_PROMPT = """
You are a technical recruiter evaluating a candidate's justification for a listed skill.

Skill in question: {skill}

Conversation so far:
{conversation}

Candidate's latest response: "{user_response}"

Your task:
1. Decide if the candidate has given a satisfactory explanation (concrete context, real usage, some outcome).
2. If satisfactory: reply with a brief acknowledgement (1–2 sentences) and end your reply with the exact token: [ACCEPTED]
3. If not satisfactory: ask one sharp follow-up question to probe further. Do NOT include [ACCEPTED].

Keep your reply concise and professional. Do not repeat what the candidate said back to them verbatim.
"""

INTERVIEW_OPENING_PROMPT = """
You are an experienced technical interviewer conducting a structured interview.

Candidate Resume:
{resume_text}

Job Description:
{jd_text}

{justified_block}

Your role:
- Ask relevant, specific questions based on the JD and the candidate's background.
- Mix technical questions with behavioural/situational ones.
- If the candidate asks you a question about the role or JD, answer it clearly and honestly from the JD, then continue the interview.
- Ask one question at a time. Keep a natural, professional tone.
- Do NOT mention scores or evaluations during the conversation.

Start the interview with a warm but professional opening and your first question.
"""

INTERVIEW_TURN_PROMPT = """
You are an experienced technical interviewer. Continue the structured interview below.

Candidate Resume:
{resume_text}

Job Description:
{jd_text}

{justified_block}

Conversation so far:
{conversation}

Instructions:
- If the candidate answered a question: acknowledge briefly, then ask your next interview question OR follow up on their answer if it needs probing.
- If the candidate asked a question about the role, company, or JD: answer it clearly from the JD context, then return to interviewing.
- Keep responses concise. Ask one question at a time.
- Do not repeat earlier questions.
- After around 8–10 exchanges, you may wrap up the interview professionally.
"""


# ── Engine class ──────────────────────────────────────────────────────────────

class ChatEngine:
    def __init__(self, api_key: str, resume_text: str, jd_text: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-3.1-flash-lite")
        self.resume_text = resume_text
        self.jd_text = jd_text

    # ── Utility ──────────────────────────────────────────────────────────────

    def raw_generate(self, prompt: str) -> str:
        """Single-shot generation with no history."""
        response = self.model.generate_content(prompt)
        return response.text.strip()

    def _format_conversation(self, history: list[dict]) -> str:
        lines = []
        for msg in history:
            role = "Interviewer" if msg["role"] in ("interviewer", "ai") else "Candidate"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)

    def _justified_block(self, justified_skills: dict | None) -> str:
        if not justified_skills:
            return ""
        lines = ["Verified skill justifications from pre-screening:"]
        for skill, justification in justified_skills.items():
            lines.append(f"  • {skill}: {justification[:200]}")
        return "\n".join(lines)

    # ── Phase 2: Skill Justification ─────────────────────────────────────────

    def ask_skill_justification(self, skill: str) -> str:
        """Generate the opening challenge question for an orphan skill."""
        prompt = SKILL_JUSTIFICATION_PROMPT.format(skill=skill)
        return self.raw_generate(prompt)

    def evaluate_skill_justification(
        self,
        skill: str,
        user_response: str,
        history: list[dict],
    ) -> tuple[str, bool]:
        """
        Evaluate candidate's justification for a skill.

        Returns:
            (response_text, accepted_bool)
        """
        conversation = self._format_conversation(history[:-1])  # exclude latest user msg
        prompt = SKILL_EVALUATION_PROMPT.format(
            skill=skill,
            conversation=conversation,
            user_response=user_response,
        )
        raw = self.raw_generate(prompt)

        accepted = "[ACCEPTED]" in raw
        clean_response = raw.replace("[ACCEPTED]", "").strip()

        return clean_response, accepted

    # ── Phase 3: Interview ────────────────────────────────────────────────────

    def start_interview(self, justified_skills: dict | None = None) -> str:
        """Generate the opening message for the interview phase."""
        prompt = INTERVIEW_OPENING_PROMPT.format(
            resume_text=self.resume_text[:3000],
            jd_text=self.jd_text[:2000],
            justified_block=self._justified_block(justified_skills),
        )
        return self.raw_generate(prompt)

    def interview_turn(self, user_message: str, history: list[dict]) -> str:
        """
        Generate the interviewer's next message in the interview conversation.
        """
        # Pull justified skills from session state if available
        import streamlit as st
        justified_skills = st.session_state.get("justified_skills", {})

        conversation = self._format_conversation(history)
        prompt = INTERVIEW_TURN_PROMPT.format(
            resume_text=self.resume_text[:3000],
            jd_text=self.jd_text[:2000],
            justified_block=self._justified_block(justified_skills),
            conversation=conversation,
        )
        return self.raw_generate(prompt)
