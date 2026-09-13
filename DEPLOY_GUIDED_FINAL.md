# Deployment

Use the full project ZIP for the cleanest result.

Preserve your real:
- knowledge/NFA/
- knowledge/PFSA/

Then:

```bash
git add .
git commit -m "Deploy guided MORBIT intake vision map and final report workflow"
git pull --rebase origin main
git push origin main
```

In Streamlit Community Cloud:
1. Confirm branch `main`.
2. Confirm main file `app.py`.
3. Reboot once after deployment.
4. Start a fresh case.

This project no longer requires the legacy `pages/` directory.
