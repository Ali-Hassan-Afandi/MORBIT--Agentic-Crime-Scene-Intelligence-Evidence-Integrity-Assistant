# MORBIT CSI CaseAssistant

A human-supervised crime-scene intelligence, evidence-integrity and case-reporting assistant.

## Current hackathon workflow

1. Save the complete case intake.
2. Analyze Photograph 1.
3. Review its immediate recommendations.
4. Optionally analyze Photograph 2 separately.
5. Start full case analysis.
6. Verify image observations.
7. Refresh agentic analysis.
8. Enter evidence coordinates for the north-up scene map.
9. Complete and save the evidence-integrity checklist.
10. Generate the formatted Word report.

## Important deployment note

The visible application name comes from `APP_NAME` in `core.py` and the hero renderer in `ui.py`.
This clean project contains no runtime `APP_VERSION` constant and no visible `V5` label.

## Existing knowledge files

When updating an existing repository, keep your real:

```text
knowledge/NFA/
knowledge/PFSA/
knowledge/manifest.json
```

Do not replace those with the empty placeholder directories from this package.
