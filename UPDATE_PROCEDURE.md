# Update Procedure — MORBIT CSI CaseAssistant

## Files to replace
Copy these files into your existing project and allow replacement:

- `app.py`
- `core.py`
- `ui.py`
- `report_builder.py`
- `pages/2_Visual_Intelligence.py`
- `pages/3_Agentic_Analysis.py`
- `pages/4_Search_and_Scene_Map.py`
- `pages/5_Evidence_Integrity.py`

The package also includes the unchanged project files so you can use the full ZIP if preferred.

## Do not delete
Keep:
- `knowledge/NFA/`
- `knowledge/PFSA/`
- `knowledge/manifest.json` if present
- your Streamlit Secrets / `GROQ_API_KEY`

## VS Code -> GitHub
Open the project folder in VS Code Terminal and run:

```bash
git status
git add .
git commit -m "MORBIT CSI CaseAssistant sequential photo and checklist update"
git pull --rebase origin main
git push origin main
```

If `git pull --rebase` reports a conflict, resolve the marked files in VS Code, save them, then:

```bash
git add .
git rebase --continue
git push origin main
```

## Streamlit
Your Streamlit Community Cloud deployment is connected to the GitHub repository. After the push:
1. Open the Streamlit app.
2. Wait for the redeployment/reboot.
3. If the old UI remains, open the app menu and choose **Reboot app**.
4. Confirm that the `GROQ_API_KEY` secret is still present in Streamlit app settings.
