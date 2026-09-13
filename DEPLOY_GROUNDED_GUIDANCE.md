# Deploy Source-Grounded Guidance Update

Recommended: replace the changed `app.py` and `core.py`, or deploy the full project ZIP.

Preserve:
- knowledge/NFA/
- knowledge/PFSA/
- Streamlit secret GROQ_API_KEY

Git:
```bash
git add -A
git commit -m "Show source grounded procedures forms and fees before report"
git pull --rebase origin main
git push origin main
```

Then reboot Streamlit once and start a fresh case.

Expected order:
1. Case intake
2. Photo + investigator verification
3. Search inputs
4. Case analysis
5. Source-Grounded Forensic Guidance displayed in app
6. Evidence documentation completeness
7. Map coordinates and scene map
8. Generate final draft
9. Download Word report
