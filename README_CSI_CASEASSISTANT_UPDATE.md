# MORBIT CSI CaseAssistant — Hackathon Update

This update keeps the existing v5 project architecture but removes the visible version label and shortens the product name to:

**MORBIT CSI CaseAssistant**

## Improvements

- No visible version number in the application title/hero.
- Case intake is saved before any AI case processing starts.
- Maximum two scene photographs.
- Photographs are handled sequentially:
  1. Upload Photograph 1.
  2. Analyze Photograph 1 and review immediate recommendations.
  3. Optionally upload Photograph 2.
  4. Analyze Photograph 2 separately.
- Full case analysis reuses the already-analyzed photo records and does not send the photos to the vision model again.
- More visible NEXT STEP buttons using primary action buttons.
- Evidence Integrity checklist now uses explicit checkbox columns inside a form and a Save Evidence Checklist button so ticks persist reliably.
- Final Word report converts Markdown-like retrieved guidance into normal Word headings, numbered points and bullet points.
- Existing NFA/PFSA knowledge documents remain unchanged.

## Important

Keep your real `knowledge/` folder and your Streamlit `GROQ_API_KEY`.
