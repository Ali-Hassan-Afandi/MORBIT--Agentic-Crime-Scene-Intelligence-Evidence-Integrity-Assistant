# MORBIT CSI CaseAssistant — Guided Final Hackathon Workflow

This build is intentionally a single-page workflow.

## Case Intake contains three sub-tabs
1. Case Details & Narrative
2. Photograph & Visual Evidence
3. Crime Scene Search Inputs

The complete saved Case Details are consolidated into the downstream case-analysis prompt.

## Vision
- One image only.
- One normal vision call.
- Maximum five highest-priority visible evidence candidates.
- Primary output budget: 620 tokens.
- Qwen 3.8 strict structured output primary.
- Qwen 3.6 plain-JSON fallback for provider capacity/structured-output failure.
- Investigator confirms visual evidence immediately in the same Photograph tab.

## Guided downstream sequence
Case analysis → evidence documentation checklist → completeness score → X/Y map coordinates →
crime scene map → one final draft-generation action → Word download.

The original scene photograph remains in session state and is embedded in the final Word report automatically.
