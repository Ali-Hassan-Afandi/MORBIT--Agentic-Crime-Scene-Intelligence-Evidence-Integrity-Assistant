# Exact Update Procedure

## A. Replace the project code in VS Code

1. Make a backup copy of your current project folder.
2. Extract this ZIP to a temporary folder.
3. Copy these files/folders into your existing repository folder:
   - app.py
   - core.py
   - ui.py
   - rag_engine.py
   - vision_agent.py
   - scene_map.py
   - report_builder.py
   - requirements.txt
   - pages/
4. Do NOT delete your existing real `knowledge/` folder.

## B. Confirm the new name locally before Git

In VS Code terminal:

```powershell
Select-String -Path .\core.py -Pattern "APP_NAME|APP_VERSION"
Select-String -Path .\ui.py -Pattern "APP_VERSION|V5|Agentic Crime Scene Intelligence"
```

Expected:
- `APP_NAME = "MORBIT CSI CaseAssistant"`
- no `APP_VERSION`
- no `V5` in `ui.py`

## C. Push to GitHub

```bash
git status
git add .
git commit -m "Replace app with clean MORBIT CSI CaseAssistant build"
git pull --rebase origin main
git push origin main
```

Then verify the latest commit on GitHub contains the new `core.py` and `ui.py`.

## D. Streamlit Community Cloud

1. Open the app's **Manage app** page.
2. Confirm the repository and branch are the expected GitHub repository and `main`.
3. Reboot the app after the GitHub push.
4. Open the app in a fresh/incognito browser tab so an old Streamlit browser session cannot confuse testing.
5. Confirm the header reads **MORBIT CSI CaseAssistant** and contains no `V5`.

## E. If the old title still appears

That means Streamlit is deploying a different file/branch/commit than the one you edited. Check:
- Streamlit repository setting
- branch = `main`
- main file path = `app.py`
- latest GitHub commit contains the updated `core.py` and `ui.py`

Do not keep editing code until those deployment settings are confirmed.
