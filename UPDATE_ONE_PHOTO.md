# Update Instructions — One-Photo Hackathon Reliability Build

Recommended: replace the complete application code with this package while preserving your real `knowledge/` folder.

Main files changed:
- app.py
- core.py
- vision_agent.py
- report_builder.py
- pages/2_Visual_Intelligence.py
- pages/6_Rich_Report.py
- README_CURRENT.md

Git:
```bash
git add .
git commit -m "Switch MORBIT to persistent single-photo hackathon workflow"
git pull --rebase origin main
git push origin main
```

After Streamlit redeploys, reboot the app once and start a fresh case.

Expected demo flow:
1. Save intake.
2. Upload one photograph.
3. The app immediately saves the image into case session state.
4. Analyze it once.
5. Start full case analysis.
6. Continue through verification, analysis, map, evidence and report.
7. Generate the Word report; the same saved photograph is embedded automatically.
