# MORBIT — Agentic Crime Scene Intelligence & Evidence Integrity Assistant (v4)

This update converts the earlier single-page SceneGuard prototype into a multi-page Streamlit application.

## Pages

1. **Case Dashboard**
2. **Scene Intake**
3. **Visual Intelligence**
4. **Agentic Analysis**
5. **Search & Scene Map**
6. **Evidence Integrity**
7. **Rich Report**

## Important v4 changes

- Product name updated throughout to:
  **MORBIT — Agentic Crime Scene Intelligence & Evidence Integrity Assistant**
- Uploaded images are now preserved in session state and:
  - passed as clearly-labelled image context to downstream agents,
  - included in the rich Word report,
  - accompanied by image metadata and AI-analysis limitations.
- Broad practical crime-scene taxonomy with an **Other / Custom** option.
- Search-method recommendation engine supports:
  - Zone / Quadrant
  - Grid
  - Line / Strip
  - Spiral
  - Wheel / Ray
  - Point-to-Point / Link
  - Lane / Vehicle
  - Underwater / Sector
- Dedicated **Search & Scene Map** page.
- Scene map uses investigator-entered 0–100 coordinates and always displays **North at the top**.
- Report export is now a formatted **DOCX** with:
  - colors and hierarchy,
  - case metadata table,
  - uploaded scene photographs,
  - visual-analysis records,
  - verified visual observations,
  - evidence inventory,
  - documentation-completeness result,
  - search recommendation,
  - generated scene map,
  - source-grounded guidance,
  - source references and disclaimer.

## Folder structure

```text
project/
├── app.py
├── core.py
├── ui.py
├── scene_map.py
├── report_builder.py
├── rag_engine.py
├── vision_agent.py
├── requirements.txt
├── pages/
│   ├── 1_Scene_Intake.py
│   ├── 2_Visual_Intelligence.py
│   ├── 3_Agentic_Analysis.py
│   ├── 4_Search_and_Scene_Map.py
│   ├── 5_Evidence_Integrity.py
│   └── 6_Rich_Report.py
└── knowledge/
    ├── NFA/
    └── PFSA/
```

**Keep your existing `knowledge/` folder and its files.** This update does not replace those documents.

## Streamlit secret

```toml
GROQ_API_KEY = "your-key"
```

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Forensic-use limitation

MORBIT is a human-supervised documentation and knowledge-support prototype. It must not be treated as a substitute for scene-command decisions, laboratory analysis, applicable law, agency SOP, expert testimony or judicial findings.
