# MORBIT CSI CaseAssistant — Final Clean Deployment

## What caused the latest crash

`progress_rail()` calls `workflow_status()`, but `app.py` did not import
`workflow_status` from `core.py`.

This release fixes that import and removes the now-unused `ui.py` file so the
UI cannot fall out of sync again.

## Recommended deployment

You do NOT need a new GitHub repository.

Use your existing repository, but replace the application code with this clean
release.

Keep:
- your real `knowledge/NFA/` folder
- your real `knowledge/PFSA/` folder
- your Streamlit Cloud secret `GROQ_API_KEY`

Delete from the repository if present:
- `pages/`
- `ui.py`
- old versioned README/update files
- old QA JSON files
- `__pycache__/`

The final root should contain at least:
- `app.py`
- `core.py`
- `vision_agent.py`
- `rag_engine.py`
- `scene_map.py`
- `report_builder.py`
- `requirements.txt`
- `knowledge/`

Then run:

```bash
git add -A
git commit -m "Fix MORBIT workflow status import and clean final deployment"
git pull --rebase origin main
git push origin main
```

In Streamlit Community Cloud:
1. Open Manage app.
2. Confirm branch: `main`.
3. Confirm main file path: `app.py`.
4. Reboot the app once.
5. Start a fresh case.
