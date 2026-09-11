# MORBIT v5 — Folder Update Instructions

## Replace these files
- `app.py`
- `core.py`
- `ui.py`
- `report_builder.py`
- `pages/3_Agentic_Analysis.py`
- `pages/4_Search_and_Scene_Map.py`
- `pages/6_Rich_Report.py`

You can also copy the complete update package over your current v5 project.

## Keep these existing project assets
Keep your actual:
- `knowledge/NFA/`
- `knowledge/PFSA/`
- `knowledge/manifest.json` if present
- Streamlit secret `GROQ_API_KEY`

## GitHub update commands
After copying the files:

```bash
git status
git add .
git commit -m "MORBIT v5 hackathon UX and evidence map update"
git pull --rebase origin main
git push origin main
```

If there are no remote changes since your last pull, `git pull --rebase` will finish immediately.
