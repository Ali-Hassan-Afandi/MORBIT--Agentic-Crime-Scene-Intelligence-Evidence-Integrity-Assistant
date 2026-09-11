from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

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
from vision_agent import VISION_MODEL

APP_NAME = "MORBIT — Agentic Crime Scene Intelligence & Evidence Integrity Assistant"
APP_SHORT = "MORBIT CSI"
APP_VERSION = "v5"
TEXT_MODEL = "openai/gpt-oss-20b"

SCENE_TYPE_GROUPS = {
    "Crimes Against Persons": [
        "Homicide / Suspicious Death",
        "Attempted Homicide",
        "Assault / Grievous Hurt",
        "Sexual Assault",
        "Kidnapping / Abduction",
        "Human Trafficking",
        "Missing Person / Suspected Foul Play",
        "Domestic Violence",
        "Child Abuse / Neglect",
    ],
    "Property & Financial Crime": [
        "Burglary / Housebreaking",
        "Robbery",
        "Theft / Larceny",
        "Vehicle Theft",
        "Criminal Damage / Vandalism",
        "Fraud / Forgery",
        "Counterfeit Currency / Documents",
        "Commercial / Workplace Theft",
    ],
    "Firearms, Explosives & Terrorism": [
        "Firearm Discharge / Shooting",
        "Illegal Firearm Recovery",
        "Explosion / Blast",
        "Improvised Explosive Device (IED)",
        "Post-Blast Scene",
        "Bomb Threat / Suspicious Package",
        "Terrorism-Related Scene",
    ],
    "Fire, Chemical & Hazardous Scenes": [
        "Fire / Suspected Arson",
        "Chemical Exposure / Spill",
        "Poisoning Scene",
        "Gas Leak / Asphyxiation",
        "CBRN / Hazardous Materials",
    ],
    "Narcotics & Organized Crime": [
        "Drug Possession / Recovery",
        "Drug Manufacturing / Clandestine Laboratory",
        "Drug Trafficking / Storage",
        "Organized Crime Scene",
        "Illegal Weapons Cache",
    ],
    "Transport & Outdoor Scenes": [
        "Road Traffic Collision",
        "Hit-and-Run",
        "Vehicle Interior / Exterior",
        "Railway Incident",
        "Aviation Incident",
        "Marine / Boat Incident",
        "Open Field / Rural Scene",
        "Forest / Remote Terrain",
        "Construction / Industrial Site",
    ],
    "Death & Human Remains": [
        "Unattended / Unexplained Death",
        "Suicide / Suspected Suicide",
        "Decomposed Remains",
        "Skeletal Remains",
        "Burial / Clandestine Grave",
        "Mass Fatality / Disaster Victim Scene",
    ],
    "Digital & Technology-Related": [
        "Digital Device Recovery",
        "Computer / Server Room",
        "Cybercrime Physical Scene",
        "CCTV / DVR Recovery",
        "Mobile Device Recovery",
        "IoT / Smart Device Scene",
    ],
    "Institutional & Special Locations": [
        "Prison / Custodial Scene",
        "Hospital / Medical Facility",
        "School / University",
        "Bank / Financial Institution",
        "Office / Corporate Premises",
        "Warehouse / Factory",
        "Religious Premises",
        "Public Event / Crowd Scene",
    ],
    "Environmental & Wildlife": [
        "Environmental Crime",
        "Wildlife Crime",
        "Illegal Dumping / Pollution",
        "Animal Cruelty",
    ],
    "Other": [
        "Secondary Crime Scene",
        "Multiple / Linked Scenes",
        "Unknown / Undetermined",
        "Other / Custom",
    ],
}
SCENE_TYPES = [item for group in SCENE_TYPE_GROUPS.values() for item in group]

SEARCH_METHODS = {
    "Zone / Quadrant": {
        "best_for": "Buildings, rooms, vehicles, complex or compartmentalized scenes.",
        "description": "Divide the scene into defined zones and search each zone systematically.",
        "strength": "Strong accountability, team assignment and adaptation to complex scenes.",
    },
    "Grid": {
        "best_for": "Large open areas requiring high search thoroughness.",
        "description": "Conduct a line/strip search, then repeat at approximately 90 degrees.",
        "strength": "High coverage and useful for small or easily missed evidence.",
    },
    "Line / Strip": {
        "best_for": "Open fields, roadsides, corridors, shorelines and broad rectangular areas.",
        "description": "Searchers move in parallel lines at controlled spacing.",
        "strength": "Simple, scalable and easy to supervise.",
    },
    "Spiral": {
        "best_for": "Open areas with few obstacles and a single trained searcher or small team.",
        "description": "Search inward or outward in a controlled spiral around a reference point.",
        "strength": "Useful when boundaries are clear and obstructions are limited.",
    },
    "Wheel / Ray": {
        "best_for": "Small circular scenes with a meaningful central point.",
        "description": "Search along radial lines extending from or toward the center.",
        "strength": "Relates evidence to a central event point, but gaps can remain between rays.",
    },
    "Point-to-Point / Link": {
        "best_for": "Compact scenes where visible evidence or event relationships guide progression.",
        "description": "Move methodically between related points or items while documenting transitions.",
        "strength": "Flexible for reconstructive documentation; not a substitute for systematic coverage when completeness is required.",
    },
    "Lane / Vehicle": {
        "best_for": "Vehicles, roadway segments and long narrow transport scenes.",
        "description": "Divide the vehicle or roadway into lanes/sections and search each in sequence.",
        "strength": "Matches transport-scene geometry and supports clear location recording.",
    },
    "Underwater / Sector": {
        "best_for": "Submerged or shoreline scenes handled by trained specialist teams.",
        "description": "Use defined sectors, lines or circular sweeps referenced to fixed control points.",
        "strength": "Provides repeatable coverage where visibility and orientation are limited.",
    },
}


def get_key() -> str:
    try:
        return st.secrets.get("GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY", "")
    except Exception:
        return os.getenv("GROQ_API_KEY", "")


def client_from_secrets() -> Groq:
    key = get_key()
    if not key:
        raise RuntimeError("GROQ_API_KEY is missing. Add it to Streamlit Secrets.")
    return Groq(api_key=key)


def groq_json(client: Groq, system: str, user: str) -> dict:
    res = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.1,
        max_completion_tokens=2800,
        response_format={"type": "json_object"},
    )
    raw = res.choices[0].message.content or ""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Text model returned invalid JSON: {raw[:400]!r}") from exc


def groq_text(client: Groq, system: str, user: str) -> str:
    res = client.chat.completions.create(
        model=TEXT_MODEL,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0.15,
        max_completion_tokens=3600,
    )
    return res.choices[0].message.content or ""


@st.cache_resource(show_spinner="Building forensic knowledge index...")
def load_rag(agency: str, fingerprint: str):
    return ForensicRAG("knowledge", agency=agency)


def init_state() -> None:
    defaults = {
        "case_id": "MORBIT-DEMO-001",
        "scene_type": "Burglary / Housebreaking",
        "custom_scene_type": "",
        "scene_dt": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "location": "",
        "desc": "",
        "scene_environment": "Indoor",
        "scene_size": "Medium",
        "personnel_count": 2,
        "obstacle_level": "Moderate",
        "agency": "BOTH",
        "investigator_question": "",
        "vision_records": [],
        "verified_visuals": [],
        "scene_analysis": None,
        "guidance": "",
        "sources": [],
        "evidence_df": pd.DataFrame(),
        "search_plan": None,
        "scene_map_png": None,
        "map_items": pd.DataFrame(columns=["Label", "Type", "X", "Y", "Notes"]),
        "report_docx": None,
        "investigator_notes": "",
        "analysis_started": False,
        "analysis_complete": False,
        "current_step": 1,
        "analysis_errors": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_case_state() -> None:
    keep = {"agency"}
    for key in list(st.session_state.keys()):
        if key not in keep:
            del st.session_state[key]
    init_state()


def vision_context(records: list[dict], verified: list[str]) -> str:
    blocks = []
    for rec in records:
        meta = rec.get("metadata", {})
        analysis = rec.get("analysis", {})
        blocks.append(
            f"{rec.get('image_id','IMG')} / {meta.get('filename','image')}: "
            f"AI summary={analysis.get('image_summary','')}; "
            f"AI proposed observations={json.dumps(analysis.get('potential_observations', []), ensure_ascii=False)}"
        )
    return (
        "\n".join(blocks)
        + "\nInvestigator-verified visual observations: "
        + json.dumps(verified, ensure_ascii=False)
    ).strip()


def scene_agent(
    client: Groq,
    desc: str,
    scene_type: str,
    vision_records: list[dict] | None = None,
    verified_visuals: list[str] | None = None,
) -> dict:
    vision_records = vision_records or []
    verified_visuals = verified_visuals or []

    system = """
You are MORBIT's Scene Analysis Agent in an Agentic Crime Scene Intelligence &
Evidence Integrity Assistant. This is a human-supervised forensic documentation tool.

Never infer guilt, identity, motive, ethnicity, age, offender profile or suspect characteristics.
Never scientifically confirm blood, DNA, narcotics, explosives, fingerprints, toolmarks,
firearm relationships, cause of fire, cause of death or laboratory conclusions from
a narrative or image alone.

Image observations must remain labelled as AI-proposed unless the investigator explicitly
verified them. Use cautious terminology such as visible, apparent, possible, potential,
or may warrant examination. Return ONLY valid JSON.
""".strip()

    user = f"""
Scene type: {scene_type}
Investigator description:
{desc or "No narrative supplied."}

IMAGE CONTEXT:
{vision_context(vision_records, verified_visuals) or "No image analysis supplied."}

Return:
{{
  "scene_summary": "...",
  "hazards": ["..."],
  "visual_context_summary": "...",
  "potential_evidence": [
    {{
      "item": "...",
      "category": "biological|digital|latent_print|trace|physical|chemical|firearms|document|other",
      "location": "...",
      "reason": "...",
      "basis": "investigator_report|verified_visual|ai_visual_proposal"
    }}
  ],
  "immediate_documentation_priorities": ["..."],
  "limitations": ["..."]
}}
""".strip()
    return groq_json(client, system, user)


def retrieve_guidance(
    client: Groq,
    rag: ForensicRAG,
    agency: str,
    desc: str,
    analysis: dict,
    vision_records: list[dict],
    verified_visuals: list[str],
    user_question: str = "",
):
    evidence_terms = ", ".join(
        f"{x.get('item')} ({x.get('category')}; basis={x.get('basis','')})"
        for x in analysis.get("potential_evidence", [])
    )
    image_context = vision_context(vision_records, verified_visuals)

    query = (
        f"{agency} forensic procedure SOP guideline evidence collection packaging sealing "
        f"submission chain of custody search documentation scene: {desc}. "
        f"Potential evidence: {evidence_terms}. Image context: {image_context}. "
        f"Question: {user_question}"
    )
    results = rag.search(query, k=10)
    context = make_context(results)

    system = """
You are MORBIT's Forensic Knowledge Retrieval Agent.
Use ONLY supplied retrieved excerpts for procedural, packaging, preservation,
submission, form, fee, sealing, chain-of-custody or agency-specific claims.

Image-derived content is context, not scientific confirmation. Distinguish AI-proposed
visual observations from investigator-verified observations.

Requirements:
1. Cite material procedural claims with [S1], [S2], etc.
2. Clearly distinguish NFA from PFSA material.
3. Do not merge conflicting requirements.
4. Do not invent procedures, laws, forms, fees, versions or authorities.
5. Say when retrieved sources do not establish a requirement.
6. Keep all recommendations advisory and human-supervised.
""".strip()

    user = f"""
Selected authority: {agency}
Scene description: {desc}
Potential evidence: {evidence_terms}

IMAGE ANALYSIS CONTEXT:
{image_context}

Question:
{user_question or "Provide relevant procedural and evidence-integrity guidance."}

RETRIEVED SOURCES:
{context}

Produce:
- Relevant procedural guidance
- Image-aware documentation considerations
- Packaging/preservation considerations only when supported
- Submission/form considerations only when supported
- Chain-of-custody considerations only when supported
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
            "Basis": item.get("basis", ""),
            "Photographed": False,
            "Collector Recorded": False,
            "Packaging Recorded": False,
            "Seal Recorded": False,
            "Custody Started": False,
        })
    return pd.DataFrame(rows)


def integrity_score(df: pd.DataFrame) -> tuple[int, list[str]]:
    fields = ["Photographed", "Collector Recorded", "Packaging Recorded", "Seal Recorded", "Custody Started"]
    if df is None or df.empty:
        return 0, ["No potential evidence is currently recorded."]
    work = df.copy()
    for field in fields:
        if field not in work.columns:
            work[field] = False
        work[field] = work[field].fillna(False).astype(bool)
    done = int(work[fields].sum().sum())
    total = len(work) * len(fields)
    alerts = []
    for _, row in work.iterrows():
        missing = [field for field in fields if not bool(row[field])]
        if missing:
            alerts.append(f"{row.get('Evidence ID','Evidence')}: missing {', '.join(missing)}")
    return round(done / total * 100), alerts


def recommend_search_method(
    scene_type: str,
    environment: str,
    scene_size: str,
    personnel_count: int,
    obstacle_level: str,
) -> dict[str, Any]:
    stype = (scene_type or "").lower()
    env = (environment or "").lower()
    size = (scene_size or "").lower()
    obstacles = (obstacle_level or "").lower()

    if any(k in stype for k in ["vehicle", "road traffic", "hit-and-run", "railway"]):
        method, alt = "Lane / Vehicle", "Zone / Quadrant"
    elif any(k in stype for k in ["marine", "boat"]) or env == "underwater":
        method, alt = "Underwater / Sector", "Grid"
    elif env in {"indoor", "building / multi-room"} or any(k in stype for k in [
        "burglary", "office", "bank", "hospital", "school", "warehouse", "prison", "religious"
    ]):
        method, alt = "Zone / Quadrant", "Grid"
    elif size in {"large", "very large"} and env in {"outdoor", "open terrain"}:
        method = "Grid" if personnel_count >= 3 else "Line / Strip"
        alt = "Line / Strip" if method == "Grid" else "Grid"
    elif obstacles == "low" and personnel_count <= 2 and env in {"outdoor", "open terrain"}:
        method, alt = "Spiral", "Grid"
    elif "explosion" in stype or "blast" in stype:
        method, alt = "Zone / Quadrant", "Grid"
    else:
        method, alt = "Zone / Quadrant", "Line / Strip"

    return {
        "recommended": method,
        "alternative": alt,
        "rationale": (
            f"{method} is recommended for this {environment.lower()} {scene_size.lower()} scene "
            f"with approximately {personnel_count} search personnel and {obstacle_level.lower()} obstruction. "
            "The scene commander should confirm the pattern after considering boundaries, hazards, terrain, "
            "staffing, evidence fragility and applicable SOP."
        ),
        "details": SEARCH_METHODS[method],
        "alternative_details": SEARCH_METHODS[alt],
        "caution": (
            "This is a planning recommendation, not an automatic operational order. "
            "Document the selected method, boundaries, assignments and deviations."
        ),
    }


def case_snapshot() -> dict[str, Any]:
    selected_type = st.session_state.scene_type
    if selected_type == "Other / Custom" and st.session_state.custom_scene_type.strip():
        selected_type = st.session_state.custom_scene_type.strip()

    return {
        "case_id": st.session_state.case_id,
        "scene_type": selected_type,
        "scene_dt": st.session_state.scene_dt,
        "location": st.session_state.location,
        "description": st.session_state.desc,
        "environment": st.session_state.scene_environment,
        "scene_size": st.session_state.scene_size,
        "personnel_count": st.session_state.personnel_count,
        "obstacle_level": st.session_state.obstacle_level,
        "agency": st.session_state.agency,
    }


def workflow_status() -> list[dict[str, Any]]:
    evidence_ready = st.session_state.evidence_df is not None and not st.session_state.evidence_df.empty
    return [
        {"step": 1, "label": "Case Intake", "done": bool(st.session_state.case_id and st.session_state.desc)},
        {"step": 2, "label": "Visual Review", "done": bool(st.session_state.vision_records) or st.session_state.analysis_complete},
        {"step": 3, "label": "Agentic Analysis", "done": bool(st.session_state.scene_analysis)},
        {"step": 4, "label": "Search & Scene Map", "done": bool(st.session_state.search_plan and st.session_state.scene_map_png)},
        {"step": 5, "label": "Evidence Integrity", "done": bool(evidence_ready)},
        {"step": 6, "label": "Rich Report", "done": bool(st.session_state.report_docx)},
    ]
