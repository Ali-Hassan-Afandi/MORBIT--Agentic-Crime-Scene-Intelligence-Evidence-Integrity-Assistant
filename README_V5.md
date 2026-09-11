# MORBIT v5 — Guided Command Dashboard

**MORBIT — Agentic Crime Scene Intelligence & Evidence Integrity Assistant**

This update keeps the multi-page architecture, but makes the main page the single starting point for a new user.

## New-user workflow

1. Open the main **Command Dashboard**.
2. Enter:
   - Case ID
   - Crime scene type
   - Date/time
   - Location
   - Investigator narrative
   - Search-planning characteristics
   - NFA / PFSA knowledge-source mode
   - Optional forensic question
   - Scene photographs
3. Press **Save Intake & Start Analysis**.
4. MORBIT runs:
   - image analysis,
   - initial scene analysis,
   - evidence proposal generation,
   - RAG retrieval,
   - search-method recommendation.
5. The dashboard then tells the user exactly what to do next.
6. Continue through:
   - Visual Intelligence
   - Agentic Analysis
   - Search & Scene Map
   - Evidence Integrity
   - Rich Word Report

## Files to replace/add

Replace the files in your existing project with the files in this package, but **keep your existing `knowledge/` folder and its NFA/PFSA documents**.

## Secret

```toml
GROQ_API_KEY = "your-real-key"
```

## Start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Important

This is a human-supervised forensic documentation and knowledge-support prototype. It does not establish identity, guilt, scientific source attribution or laboratory confirmation.
