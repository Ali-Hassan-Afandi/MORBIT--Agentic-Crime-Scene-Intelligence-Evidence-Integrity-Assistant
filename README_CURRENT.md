# MORBIT CSI CaseAssistant — One-Photo Hackathon Build

This build optimizes reliability and demo speed.

## Key behavior

- One representative scene photograph only.
- The photograph is saved to Streamlit session state immediately on upload.
- The saved bytes, metadata and SHA-256 record are reused automatically across:
  - Visual Intelligence
  - Agentic Analysis
  - Evidence workflow
  - Scene mapping context
  - Final Word report
- No re-upload and no browser refresh are required for the final report.
- The vision model is called only once unless the user deliberately presses Re-analyze.

## Vision reliability

Primary:
`qwen/qwen3.8-27b` with strict JSON Schema.

Fallback:
`qwen/qwen3.6-27b` without provider-side JSON mode, followed by local JSON parsing.

This means a temporary Qwen 3.8 over-capacity response does not immediately end the demo.
Normal successful requests have no artificial waiting delay.

## Deployment

Replace the files from this package in the GitHub repository, keeping the existing real `knowledge/` content.
