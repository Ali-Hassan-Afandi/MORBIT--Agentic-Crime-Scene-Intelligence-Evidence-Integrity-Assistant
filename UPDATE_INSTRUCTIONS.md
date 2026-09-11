# MORBIT v4 Update Instructions

## Replace / add these files in your existing project

Replace:
- `app.py`
- `rag_engine.py`
- `vision_agent.py`
- `requirements.txt`

Add:
- `core.py`
- `ui.py`
- `scene_map.py`
- `report_builder.py`
- the complete `pages/` folder

## Important: KEEP your existing knowledge folder

Do not delete or replace your existing:

```text
knowledge/
├── NFA/
├── PFSA/
└── manifest.json   # if you already use one
```

The ZIP contains empty NFA/PFSA placeholders only to show the expected structure.

## Install updated dependency

The new rich Word report uses `python-docx`, which is already included in the new `requirements.txt`.

```bash
pip install -r requirements.txt
```

## Streamlit

Your existing Groq secret remains:

```toml
GROQ_API_KEY = "your-real-key"
```

Start with:

```bash
streamlit run app.py
```

## Recommended page order

1. Scene Intake
2. Visual Intelligence
3. Agentic Analysis
4. Search & Scene Map
5. Evidence Integrity
6. Rich Report

Uploaded image bytes are retained in the Streamlit session, passed as labelled visual-analysis context to downstream agents, and embedded in the generated DOCX report.
