# MORBIT CSI CaseAssistant — Final Right-Rail Build

## Interface
The native Streamlit sidebar is removed.

Desktop:
- permanent fixed progress rail on the right
- main workflow remains visible beside it

Tablet/mobile:
- the same progress component becomes a fixed bottom strip automatically

## Vision
- one scene photograph
- maximum five ranked visual evidence candidates
- primary output budget: 620 tokens
- Qwen 3.8 strict structured output primary
- Qwen 3.6 plain-JSON fallback during provider pressure

### Homicide / murder / suspicious-death / human-remains scenes
MORBIT uses body-first priority:
1. inspect the full photograph for every visually supportable possible human body/body-like form/possible human remains
2. put those candidates first
3. use any remaining positions, up to five total, for other high-priority evidence

The image model does not confirm death, identity, cause/manner/time of death or laboratory findings.

## Guided workflow
Case Details → Photograph + Immediate Investigator Verification → Search Inputs →
Case Analysis → Documentation Completeness → X/Y Coordinates → Scene Map →
Generate Draft → Download Word Report.
