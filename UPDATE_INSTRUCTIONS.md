# Update Instructions — MORBIT v5

## 1. Back up your project

Before replacing files, make a copy of the current repository folder.

## 2. Keep your existing knowledge folder

Do not delete:

```text
knowledge/
├── NFA/
├── PFSA/
└── manifest.json   # if present
```

## 3. Replace/add

Replace:
- app.py
- rag_engine.py
- vision_agent.py
- requirements.txt

Add/replace:
- core.py
- ui.py
- scene_map.py
- report_builder.py
- complete `pages/` folder

## 4. GitHub update

```bash
git status
git add .
git commit -m "MORBIT v5 guided command dashboard"
git pull --rebase origin main
git push origin main
```

If `git pull --rebase` reports a conflict, resolve the files in VS Code, then:

```bash
git add .
git rebase --continue
git push origin main
```

## 5. Streamlit

If your Streamlit Community Cloud app is connected to the same GitHub repository and `main` branch, it should redeploy from the new commit.

The main page is now the required starting point for new users.
