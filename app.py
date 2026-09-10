from __future__ import annotations

import json
import os
from datetime import datetime

import pandas as pd
import streamlit as st
from groq import Groq

from rag_engine import (
    EMBED_MODEL,
    ForensicRAG,
    knowledge_fingerprint,
    knowledge_inventory,
    make_context,
)
from vision_agent import VISION_MODEL, analyze_image, image_metadata

TEXT_MODEL = "openai/gpt-oss-20b"

st.set_page_config(
    page_title="MORBIT SceneGuard AI v3",
    page_icon="🛡️",
    layout="wide",
)


def get_key() -> str:
    try:
        return st.secrets.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    except Exception:
        return os.getenv("GROQ_API_KEY", "")


def groq_json(client: Groq, system: str, user: str) -> dict:
    res = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_completion_tokens=2400,
        response_format={"type": "json_object"},
    )
    raw = res.choices[0].message.content or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Text model returned invalid JSON. Beginning of response: {raw[:400]!r}"
        ) from exc


def groq_text(client: Groq, system: str, user: str) -> str:
    res = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.15,
        max_completion_tokens=3000,
    )
    return res.choices[0].message.content or ""


@st.cache_resource(show_spinner="Building forensic knowledge index...")
def load_rag(agency: str, fingerprint: str):
    # fingerprint is intentionally part of the cache key.
    # Adding/removing/changing a PDF automatically invalidates the cached RAG.
    return ForensicRAG("knowledge", agency=agency)


def scene_agent(client: Groq, desc: str, scene_type: str) -> dict:
    system = """
You are SceneGuard AI's Scene Analysis Agent.
This is a human-supervised forensic documentation prototype.

Never infer guilt, identity, motive, or offender characteristics.
Never scientifically confirm a substance, fingerprint, DNA, narcotic,
explosive, toolmark, firearm relationship, or other forensic conclusion
from a narrative alone.

Use cautious terminology and return ONLY valid JSON.
""".strip()

    user = f"""
Scene type: {scene_type}
Investigator description: {desc}

Return this schema:
{{
  "scene_summary": "...",
  "hazards": ["..."],
  "potential_evidence": [
    {{
      "item": "...",
      "category": "biological|digital|latent_print|trace|physical|other",
      "location": "...",
      "reason": "..."
    }}
  ],
  "immediate_documentation_priorities": ["..."]
}}
""".strip()

    return groq_json(client, system, user)


def retrieve_guidance(
    client: Groq,
    rag: ForensicRAG,
    agency: str,
    desc: str,
    analysis: dict,
    verified_visuals: list[str],
    user_question: str = "",
):
    evidence_terms = ", ".join(
        f"{x.get('item')} ({x.get('category')})"
        for x in analysis.get("potential_evidence", [])
    )

    query = (
        f"{agency} forensic procedure SOP guideline form fees evidence collection "
        f"packaging sealing submission chain of custody scene: {desc}. "
        f"Potential evidence: {evidence_terms}. "
        f"Verified visual observations: {' '.join(verified_visuals)}. "
        f"Investigator question: {user_question}"
    )

    results = rag.search(query, k=10)
    context = make_context(results)

    system = """
You are SceneGuard AI's Forensic Knowledge Retrieval Agent.

Use ONLY the supplied retrieved excerpts for procedural, submission,
form, fee, packaging, preservation, sealing, or chain-of-custody claims.

Requirements:
1. Cite every material procedural claim with [S1], [S2], etc.
2. Clearly distinguish NFA from PFSA material.
3. Do not combine conflicting requirements as though they are identical.
4. Do not invent a fee, form, SOP, procedure, law, document version or authority.
5. If the retrieved sources do not establish a requested requirement, explicitly say so.
6. A locally stored public document is a source for this prototype but does not by itself prove that it is the latest institutional version.
7. Keep recommendations advisory and human-supervised.
""".strip()

    user = f"""
Selected authority mode: {agency}
Scene: {desc}
Potential evidence: {evidence_terms}
Verified visual observations: {verified_visuals}
Investigator question: {user_question or "Provide relevant procedural guidance."}

RETRIEVED SOURCES:
{context}

Produce:
- Relevant procedural guidance
- Packaging/preservation considerations when supported
- Submission/form considerations when supported
- Fee/payment information only when explicitly established by a retrieved source
- Source limitations
""".strip()

    return groq_text(client, system, user), results


def evidence_dataframe(analysis: dict) -> pd.DataFrame:
    rows = []
    for i, item in enumerate(analysis.get("potential_evidence", []), start=1):
        rows.append({
            "Evidence ID": f"E-{i:03d}",
            "Item": item.get("item", ""),
            "Category": item.get("category", "other"),
            "Location": item.get("location", ""),
            "Photographed": False,
            "Collector Recorded": False,
            "Packaging Recorded": False,
            "Seal Recorded": False,
            "Custody Started": False,
        })
    return pd.DataFrame(rows)


def integrity_score(df: pd.DataFrame) -> tuple[int, list[str]]:
    fields = [
        "Photographed",
        "Collector Recorded",
        "Packaging Recorded",
        "Seal Recorded",
        "Custody Started",
    ]
    if df.empty:
        return 0, ["No potential evidence is currently recorded."]

    work = df.copy()
    for field in fields:
        if field not in work.columns:
            work[field] = False
        work[field] = work[field].fillna(False).astype(bool)

    done = int(work[fields].sum().sum())
    total = len(work) * len(fields)

    alerts: list[str] = []
    for _, row in work.iterrows():
        missing = [field for field in fields if not bool(row[field])]
        if missing:
            alerts.append(
                f"{row.get('Evidence ID', 'Evidence')}: missing {', '.join(missing)}"
            )

    return round(done / total * 100), alerts


def reset_case_state():
    for key in [
        "vision_records",
        "scene_analysis",
        "guidance",
        "sources",
        "evidence_df",
        "report",
    ]:
        st.session_state.pop(key, None)


st.title("🛡️ MORBIT SceneGuard AI v3")
st.caption(
    "Agentic Crime Scene Intelligence • Multimodal Analysis • "
    "NFA/PFSA Source-Grounded Forensic RAG"
)
st.warning(
    "Hackathon prototype: use fictional or anonymized data only. "
    "AI observations are not laboratory findings and require investigator verification."
)

inventory = knowledge_inventory("knowledge")
nfa_count = len(inventory["NFA"])
pfsa_count = len(inventory["PFSA"])

with st.sidebar:
    st.header("Configuration")

    agency_label = st.selectbox(
        "Forensic knowledge source",
        ["NFA Pakistan", "PFSA Punjab", "NFA + PFSA"],
    )
    agency = {
        "NFA Pakistan": "NFA",
        "PFSA Punjab": "PFSA",
        "NFA + PFSA": "BOTH",
    }[agency_label]

    st.write("Text model:", TEXT_MODEL)
    st.write("Vision model:", VISION_MODEL)
    st.write("Embedding model:", EMBED_MODEL)
    st.write("Vector search:", "FAISS")
    st.metric("NFA local documents", nfa_count)
    st.metric("PFSA local documents", pfsa_count)

    with st.expander("Indexed local knowledge files"):
        for a in ["NFA", "PFSA"]:
            st.markdown(f"**{a} ({len(inventory[a])})**")
            for src in inventory[a]:
                st.caption(
                    f"• {src['filename']}  |  {src['document_type']}"
                )

    st.info(
        "V3 auto-discovers PDFs/TXT/MD placed inside knowledge/NFA and "
        "knowledge/PFSA. You no longer need a manifest entry for every new file."
    )

    if st.button("Reset current case"):
        reset_case_state()
        st.rerun()

api_key = get_key()
if not api_key:
    st.error(
        "GROQ_API_KEY is missing. Add it to Streamlit Secrets "
        "or the Colab environment."
    )
    st.stop()

client = Groq(api_key=api_key)

st.subheader("1. Scene Intake")
c1, c2, c3 = st.columns(3)
case_id = c1.text_input("Case ID", "SG-V3-DEMO-001")
scene_type = c2.selectbox(
    "Scene type",
    ["Burglary", "Assault", "Vehicle", "Fire", "Digital Device Recovery", "Other"],
)
scene_dt = c3.text_input(
    "Date / Time",
    datetime.now().strftime("%Y-%m-%d %H:%M"),
)
location = st.text_input("Location", "Training Apartment, Room 2")

desc = st.text_area(
    "Scene description",
    (
        "A broken bedroom window is visible. A reddish-brown stain is reported "
        "on a glass fragment near the window. A laptop is lying on the floor. "
        "Possible fingerprint marks are visible on a drinking glass on the table."
    ),
    height=125,
)

st.subheader("2. Multimodal Scene Images")
uploads = st.file_uploader(
    "Upload up to 5 JPG/JPEG/PNG images",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

if uploads and len(uploads) > 5:
    st.warning("Only the first 5 uploaded images will be analyzed.")
    uploads = uploads[:5]

if "vision_records" not in st.session_state:
    st.session_state.vision_records = []

if uploads and st.button("Analyze Uploaded Images", use_container_width=True):
    records = []
    for idx, up in enumerate(uploads, start=1):
        data = up.getvalue()
        try:
            with st.spinner(f"Analyzing image {idx}/{len(uploads)}: {up.name}"):
                meta = image_metadata(data, up.name)
                visual = analyze_image(client, data, up.name, desc)
            records.append({
                "image_id": f"IMG-{idx:03d}",
                "metadata": meta,
                "analysis": visual,
            })
        except Exception as exc:
            st.error(f"Image analysis failed for {up.name}: {exc}")
    st.session_state.vision_records = records

verified_visuals: list[str] = []

if st.session_state.vision_records:
    st.markdown("#### Human Verification")
    st.caption(
        "Only observations checked below are promoted into the scene context used by RAG."
    )

    for rec in st.session_state.vision_records:
        meta = rec["metadata"]
        with st.expander(f"{rec['image_id']} — {meta['filename']}"):
            m1, m2, m3 = st.columns(3)
            m1.metric("Dimensions", f"{meta['width']} × {meta['height']}")
            m2.metric("Bytes", f"{meta['bytes']:,}")
            m3.code(meta["sha256"][:20] + "...", language=None)

            st.write(rec["analysis"].get("image_summary", ""))

            suggestions = rec["analysis"].get("documentation_suggestions", [])
            if suggestions:
                st.markdown("**Documentation suggestions**")
                for s in suggestions:
                    st.write("•", s)

            for j, obs in enumerate(
                rec["analysis"].get("potential_observations", [])
            ):
                key = f"verify_{rec['image_id']}_{j}"
                label = (
                    f"Accept: {obs.get('observation', '')} "
                    f"[{obs.get('confidence', 'unspecified')}]"
                )
                if st.checkbox(label, key=key):
                    verified_visuals.append(obs.get("observation", ""))

            limitations = rec["analysis"].get("limitations", [])
            if limitations:
                st.caption("Limitations: " + "; ".join(limitations))

st.subheader("3. Agentic Analysis + RAG")

investigator_question = st.text_input(
    "Optional forensic knowledge question",
    placeholder=(
        "Example: What packaging/submission guidance and forms are relevant "
        "to the potential evidence in this scene?"
    ),
)

if st.button("Run V3 Agents", type="primary", use_container_width=True):
    try:
        fingerprint = knowledge_fingerprint("knowledge", agency)
        rag = load_rag(agency, fingerprint)

        analysis = scene_agent(client, desc, scene_type)

        guidance, sources = retrieve_guidance(
            client=client,
            rag=rag,
            agency=agency,
            desc=desc,
            analysis=analysis,
            verified_visuals=verified_visuals,
            user_question=investigator_question,
        )

        st.session_state.scene_analysis = analysis
        st.session_state.guidance = guidance
        st.session_state.sources = sources
        st.session_state.evidence_df = evidence_dataframe(analysis)

        st.success("SceneGuard V3 agents completed successfully.")
    except Exception as exc:
        st.exception(exc)

if "scene_analysis" in st.session_state:
    analysis = st.session_state.scene_analysis

    st.subheader("4. Scene Analysis Agent")
    st.write(analysis.get("scene_summary", ""))

    if analysis.get("hazards"):
        st.markdown("**Potential hazards / cautions**")
        for item in analysis["hazards"]:
            st.write("•", item)

    if analysis.get("immediate_documentation_priorities"):
        st.markdown("**Immediate documentation priorities**")
        for item in analysis["immediate_documentation_priorities"]:
            st.write("•", item)

    st.subheader("5. Source-Grounded Forensic Guidance")
    st.markdown(st.session_state.guidance)

    with st.expander("Show retrieved NFA/PFSA sources"):
        for i, r in enumerate(st.session_state.sources, start=1):
            page = f" — Page {r['page']}" if r.get("page") else ""
            st.markdown(f"**[S{i}] {r['title']}{page}**")
            st.caption(
                f"Agency: {r['agency']} | "
                f"Type: {r['document_type']} | "
                f"Verification: {r['verification']} | "
                f"Similarity: {r['score']:.3f}"
            )
            st.caption(f"Local file: {r.get('file', '')}")
            st.write(r["text"][:1000])

            if r.get("url"):
                st.link_button("Open recorded source URL", r["url"])

            st.divider()

    st.subheader("6. Evidence Integrity Agent")
    edited = st.data_editor(
        st.session_state.evidence_df,
        use_container_width=True,
        hide_index=True,
        key="evidence_editor",
    )

    score, alerts = integrity_score(edited)
    st.metric("Documentation Completeness", f"{score}%")
    st.progress(score / 100)

    for alert in alerts:
        st.warning(alert)

    st.subheader("7. Report Agent")
    notes = st.text_area("Investigator notes", "")

    if st.button(
        "Generate Source-Grounded V3 Report",
        use_container_width=True,
    ):
        context = make_context(st.session_state.sources)

        system = """
You are SceneGuard AI's Report Agent.
Produce a structured forensic documentation draft.

Clearly distinguish:
- investigator-reported observations,
- AI-proposed observations,
- investigator-verified visual observations,
- source-grounded procedural guidance,
- deterministic documentation alerts.

Never infer guilt, identity, or scientific confirmation.
Cite procedural statements with the supplied [S#] references.
""".strip()

        user = f"""
CASE: {case_id}
Scene type: {scene_type}
Date/time: {scene_dt}
Location: {location}
Selected authority mode: {agency}

Investigator description:
{desc}

Scene analysis:
{json.dumps(analysis, ensure_ascii=False)}

Verified visual observations:
{json.dumps(verified_visuals, ensure_ascii=False)}

Evidence inventory:
{json.dumps(edited.to_dict(orient="records"), ensure_ascii=False)}

Documentation completeness:
{score}%

Investigator notes:
{notes}

RAG guidance:
{st.session_state.guidance}

Retrieved sources:
{context}

Required sections:
CASE DETAILS
SCENE SUMMARY
VERIFIED VISUAL OBSERVATIONS
POTENTIAL EVIDENCE INVENTORY
SOURCE-GROUNDED PROCEDURAL GUIDANCE
DOCUMENTATION GAPS
INVESTIGATOR NOTES
SOURCE REFERENCES
DISCLAIMER
""".strip()

        report = groq_text(client, system, user)
        st.session_state.report = report

if "report" in st.session_state:
    st.text_area(
        "Generated report",
        st.session_state.report,
        height=520,
    )
    st.download_button(
        "Download TXT Report",
        st.session_state.report,
        file_name="SceneGuard_V3_Report.txt",
        mime="text/plain",
    )
