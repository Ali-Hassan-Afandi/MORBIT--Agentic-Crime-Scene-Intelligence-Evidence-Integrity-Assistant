# MORBIT CSI CaseAssistant — Vision + UI Upgrade

This build keeps the reliable one-photo hackathon workflow and improves two areas:

## 1. Systematic visual evidence sweep
The vision prompt now scans the image by scene zones and evidence classes instead of stopping after a few obvious items.

- Up to 10 distinct visible potential evidence candidates.
- Each candidate includes visible image location, category, confidence and reason.
- Adds scene zones reviewed and a coverage note.
- Keeps forensic guardrails: no identity/guilt inference and no laboratory confirmation.
- One normal vision call only, so demo speed remains practical.
- Qwen 3.8 strict structured output remains primary; Qwen 3.6 remains an availability fallback.

## 2. Aesthetic guided UI
- Refined dark forensic-tech visual design.
- Sidebar appears on the dashboard and all workflow pages.
- Sidebar shows all six functions with Completed / Current / Pending state.
- Quick navigation links are always available.
- Evidence candidate cards are easier to review.
- Workflow completion is more accurate: a saved image alone no longer marks Visual Review complete; the AI analysis must exist.

The single saved scene photograph still persists automatically through the complete case workflow and final DOCX report.
