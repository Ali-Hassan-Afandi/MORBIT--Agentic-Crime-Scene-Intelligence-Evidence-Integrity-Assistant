# MORBIT CSI CaseAssistant — Vision JSON Fix

Replace the existing `vision_agent.py` with the included file.

Changes:
- Uses `qwen/qwen3.8-27b`.
- Uses strict JSON Schema Structured Outputs first.
- Disables reasoning for this extraction task.
- Keeps responses concise.
- Falls back to locally parsed JSON if provider-side structured output fails.
- Keeps all existing human-supervised forensic safety rules.

Deploy:
```bash
git add vision_agent.py
git commit -m "Fix photograph JSON validation"
git pull --rebase origin main
git push origin main
```

Then reboot the Streamlit app and test Photograph 1.
