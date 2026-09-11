# MORBIT v5 — Hackathon UX & Scene-Plan Update

**MORBIT — Agentic Crime Scene Intelligence & Evidence Integrity Assistant**

This remains the v5 product. This package is a focused hackathon UX update.

## Improvements in this update

### 1. Retake / Correct Case
A new **Retake / Correct This Case** control clears all derived analysis while keeping the investigator's intake fields. The user can correct an input mistake and run the case again without starting from zero.

### 2. Clear Entire Case
A separate **Clear Entire Case** control starts a completely new case. It includes a confirmation step to reduce accidental data loss.

### 3. Maximum Two Scene Photographs
For hackathon testing, the image analyzer accepts a maximum of **two** JPG/JPEG/PNG scene photographs per analysis. If more than two are selected, analysis is blocked until the selection is reduced.

### 4. Automatic Evidence Site-Plan Table
All potential evidence identified by MORBIT is automatically added to the Scene of Crime site-plan table.

Locked system fields:
- Evidence ID
- Evidence Item
- Category

Investigator-editable fields:
- X coordinate
- Y coordinate
- Notes

The investigator does not have to manually retype evidence names.

### 5. North-Up Site Plan
After all evidence rows have coordinates, MORBIT generates the north-up Scene of Crime map.

### 6. Rich Report Improvement
The Word report now includes:
- the automated evidence coordinate table,
- the scene map,
- uploaded images,
- evidence inventory,
- source-grounded guidance.

### 7. Visual Refresh
The interface uses a stronger MORBIT visual system with:
- navy/blue/cyan/violet gradients,
- improved metric cards,
- workflow cards,
- clearer next-step panels,
- more visible primary buttons.

## Keep your knowledge base
Do not delete or replace your existing real `knowledge/NFA`, `knowledge/PFSA`, or `manifest.json` files.
