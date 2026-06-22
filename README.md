# RecruitAI — AI Recruitment Screening Bot

A Streamlit-based POC that conducts AI-powered resume screening and interviews using Google Gemini (free tier).

---

## Features

- **Resume parsing** — extracts text from PDF resumes
- **Skill gap detection** — finds skills listed but not demonstrated in work/projects
- **Phase 1: Skill Justification** — AI challenges unverified skills and probes until satisfied
- **Phase 2: Live Interview** — 2-way conversation; AI asks JD-based questions; candidate can also ask about the role

---

## Quick Start

### 1. Clone / copy the project
```bash
cd recruitment_bot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Get a free Gemini API key
Go to https://aistudio.google.com → **Get API Key** → copy it.  
No credit card required. Free tier: 15 RPM, 1M tokens/day.

### 4. Run the app
```bash
streamlit run app.py
```

### 5. Usage
1. Paste your **Gemini API key** in the sidebar
2. Upload the candidate's **PDF resume**
3. Paste the **Job Description**
4. Click **Analyse & Start →**
5. Complete the skill verification phase (if any orphan skills found)
6. Proceed to the live interview

---

## Project Structure

```
recruitment_bot/
├── app.py              # Streamlit UI + session state machine
├── resume_parser.py    # PDF text extraction (pdfplumber)
├── skill_analyzer.py   # LLM-based skill gap detection
├── chat_engine.py      # All Gemini API calls + prompt logic
└── requirements.txt
```

---

## Configuration

You can optionally set the API key via environment variable instead of the UI:
```bash
export GEMINI_API_KEY="AIza..."
streamlit run app.py
```
Then pre-fill it in `app.py` by changing:
```python
api_key_input = st.text_input(..., value=os.getenv("GEMINI_API_KEY", ""))
```

---

## Extending for Production

| Area | Suggestion |
|------|-----------|
| Auth | Add login before resume upload |
| Storage | Save chat transcripts to DB (PostgreSQL/MySQL) |
| Scoring | Add a post-interview scoring prompt |
| Multi-candidate | Add candidate ID + session namespacing |
| Report | Export interview transcript as PDF |
| Model | Swap Gemini Flash → Pro for harder technical roles |
