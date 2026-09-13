# Deployment — Vision + UI Upgrade

Recommended: deploy the full project ZIP, while preserving your existing real `knowledge/` folder.

Changed files:
- vision_agent.py
- ui.py
- core.py
- app.py
- pages/1_Scene_Intake.py
- pages/2_Visual_Intelligence.py
- pages/3_Agentic_Analysis.py
- pages/4_Search_and_Scene_Map.py
- pages/5_Evidence_Integrity.py
- pages/6_Rich_Report.py
- README_CURRENT.md

Git commands:
```bash
git add .
git commit -m "Improve vision evidence sweep and guided sidebar UI"
git pull --rebase origin main
git push origin main
```

After Streamlit redeploys:
1. Reboot the app once.
2. Start a fresh case.
3. Save intake.
4. Upload one representative photograph.
5. Analyze the photograph once.
6. Confirm that the result now shows scene zones reviewed plus a larger candidate-evidence list.
7. Continue through the sidebar workflow to the final report.
