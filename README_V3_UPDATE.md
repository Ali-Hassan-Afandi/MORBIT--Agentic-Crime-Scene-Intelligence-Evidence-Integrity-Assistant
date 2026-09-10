# SceneGuard AI V3 — Updated Knowledge Auto-Discovery

This V3 update is designed for the folder layout:

```text
project/
├── app.py
├── rag_engine.py
├── vision_agent.py
├── requirements.txt
├── COLAB_TEST_V3.py
└── knowledge/
    ├── manifest.json          # optional metadata, no longer mandatory for every PDF
    ├── NFA/
    │   ├── *.pdf
    │   ├── *.txt
    │   └── *.md
    └── PFSA/
        ├── *.pdf
        ├── *.txt
        └── *.md
```

## Main change

`rag_engine.py` now discovers every PDF/TXT/MD under the selected agency folder.
You do **not** need to add every new source manually to `manifest.json`.

If a matching manifest entry exists, its title, URL and verification metadata are used.
If it does not exist, SceneGuard safely infers metadata from the filename.

## Authority selector

The Streamlit sidebar supports:

- NFA Pakistan
- PFSA Punjab
- NFA + PFSA

Only files belonging to the selected authority are indexed.

## New knowledge files

To add a new public source later:

1. Put NFA material in `knowledge/NFA/`, or PFSA material in `knowledge/PFSA/`.
2. Commit and push the file to GitHub.
3. Streamlit redeploys.
4. SceneGuard computes a new knowledge fingerprint and rebuilds the cached vector index automatically.

## Important limitation

Image-only scanned PDFs may produce little or no extractable text with PyPDF.
The current pipeline deliberately reports that condition rather than pretending the document was indexed.
OCR can be added in a later release if required.

## Colab test

```bash
pip install -r requirements.txt
python COLAB_TEST_V3.py
```

Then:

```bash
streamlit run app.py
```

Set `GROQ_API_KEY` in the environment or Streamlit Secrets.
