import streamlit as st
import pandas as pd

from core import (
    APP_NAME, APP_VERSION, EMBED_MODEL, TEXT_MODEL, VISION_MODEL,
    SCENE_TYPES, init_state, reset_case_state, client_from_secrets,
    scene_agent, retrieve_guidance, evidence_dataframe,
    recommend_search_method, knowledge_fingerprint, load_rag,
    knowledge_inventory, workflow_status
)
from vision_agent import analyze_image, image_metadata
from ui import apply_ui, hero, render_workflow
from scene_map import generate_scene_map

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_ui()
init_state()

hero(
    "Command Dashboard",
    "Enter the complete scene intake here, upload images, start the first analysis, "
    "then follow the guided workflow to verification, mapping, evidence integrity and the final Word report."
)

st.warning(
    "Use fictional, training or properly authorized case data only. "
    "AI observations are not laboratory findings and require investigator verification."
)

# ------------------------------------------------------------
# Dashboard status
# ------------------------------------------------------------
a,b,c,d = st.columns(4)
a.metric("Case", st.session_state.case_id)
b.metric("Images", len(st.session_state.vision_records))
c.metric("Evidence items", len(st.session_state.evidence_df) if st.session_state.evidence_df is not None else 0)
d.metric("Workflow", f"{sum(1 for x in workflow_status() if x['done'])}/6")

render_workflow(active_step=st.session_state.current_step)

st.divider()

# ------------------------------------------------------------
# SINGLE-PAGE MASTER INTAKE
# ------------------------------------------------------------
st.markdown("## 1. Complete Case Intake")
st.caption("A new user can enter everything required for the first analysis without leaving this page.")

with st.form("master_intake_form"):
    r1c1,r1c2,r1c3 = st.columns(3)
    case_id = r1c1.text_input("Case ID", value=st.session_state.case_id)
    scene_type = r1c2.selectbox(
        "Crime scene type",
        SCENE_TYPES,
        index=SCENE_TYPES.index(st.session_state.scene_type) if st.session_state.scene_type in SCENE_TYPES else 0,
    )
    scene_dt = r1c3.text_input("Date / Time", value=st.session_state.scene_dt)

    custom_scene = ""
    if scene_type == "Other / Custom":
        custom_scene = st.text_input(
            "Custom scene type",
            value=st.session_state.custom_scene_type,
            placeholder="Describe the scene classification",
        )

    location = st.text_input(
        "Scene location",
        value=st.session_state.location,
        placeholder="Example: Training apartment, Room 2",
    )

    desc = st.text_area(
        "Investigator scene description",
        value=st.session_state.desc,
        height=150,
        placeholder=(
            "Record factual scene observations, visible conditions, reported circumstances and known boundaries. "
            "Avoid conclusions that require laboratory confirmation."
        ),
    )

    st.markdown("#### Search-planning characteristics")
    s1,s2,s3,s4 = st.columns(4)
    env_options = ["Indoor","Building / Multi-room","Outdoor","Open Terrain","Vehicle / Roadway","Underwater"]
    environment = s1.selectbox(
        "Environment",
        env_options,
        index=env_options.index(st.session_state.scene_environment)
        if st.session_state.scene_environment in env_options else 0,
    )
    size_options = ["Small","Medium","Large","Very Large"]
    scene_size = s2.selectbox(
        "Scene size",
        size_options,
        index=size_options.index(st.session_state.scene_size)
        if st.session_state.scene_size in size_options else 1,
    )
    personnel = s3.number_input(
        "Available search personnel",
        min_value=1, max_value=50, value=int(st.session_state.personnel_count),
    )
    obstacle_options = ["Low","Moderate","High"]
    obstacles = s4.selectbox(
        "Obstacle / complexity",
        obstacle_options,
        index=obstacle_options.index(st.session_state.obstacle_level)
        if st.session_state.obstacle_level in obstacle_options else 1,
    )

    st.markdown("#### Forensic knowledge source")
    agency_label = st.radio(
        "Authority mode",
        ["NFA Pakistan","PFSA Punjab","NFA + PFSA"],
        horizontal=True,
        index={"NFA":0,"PFSA":1,"BOTH":2}.get(st.session_state.agency,2),
    )

    investigator_question = st.text_input(
        "Optional forensic knowledge question",
        value=st.session_state.investigator_question,
        placeholder="Example: What packaging, submission and chain-of-custody considerations are relevant?",
    )

    st.markdown("#### Scene images")
    uploads = st.file_uploader(
        "Upload up to 8 JPG/JPEG/PNG images",
        type=["jpg","jpeg","png"],
        accept_multiple_files=True,
        help="Images are analyzed when you press Start Analysis and preserved for the final Word report.",
    )

    start = st.form_submit_button(
        "🚀 Save Intake & Start Analysis",
        type="primary",
        use_container_width=True,
    )

if start:
    st.session_state.case_id = case_id.strip()
    st.session_state.scene_type = scene_type
    st.session_state.custom_scene_type = custom_scene.strip()
    st.session_state.scene_dt = scene_dt.strip()
    st.session_state.location = location.strip()
    st.session_state.desc = desc.strip()
    st.session_state.scene_environment = environment
    st.session_state.scene_size = scene_size
    st.session_state.personnel_count = int(personnel)
    st.session_state.obstacle_level = obstacles
    st.session_state.agency = {"NFA Pakistan":"NFA","PFSA Punjab":"PFSA","NFA + PFSA":"BOTH"}[agency_label]
    st.session_state.investigator_question = investigator_question.strip()
    st.session_state.analysis_started = True
    st.session_state.analysis_complete = False
    st.session_state.analysis_errors = []

    if not st.session_state.desc:
        st.error("Please enter a factual scene description before starting analysis.")
    else:
        client = client_from_secrets()

        # A. image analysis
        records = []
        if uploads:
            use_uploads = uploads[:8]
            for idx, up in enumerate(use_uploads, start=1):
                try:
                    data = up.getvalue()
                    with st.spinner(f"Step A/4 — Analyzing image {idx}/{len(use_uploads)}: {up.name}"):
                        meta = image_metadata(data, up.name)
                        visual = analyze_image(client, data, up.name, st.session_state.desc)
                    records.append({
                        "image_id": f"IMG-{idx:03d}",
                        "metadata": meta,
                        "analysis": visual,
                        "image_bytes": data,
                    })
                except Exception as exc:
                    st.session_state.analysis_errors.append(f"Image {up.name}: {exc}")

        st.session_state.vision_records = records
        st.session_state.verified_visuals = []

        # B. scene analysis
        try:
            with st.spinner("Step B/4 — Running multimodal scene-analysis agent..."):
                effective_scene_type = (
                    st.session_state.custom_scene_type
                    if st.session_state.scene_type == "Other / Custom" and st.session_state.custom_scene_type
                    else st.session_state.scene_type
                )
                analysis = scene_agent(
                    client,
                    st.session_state.desc,
                    effective_scene_type,
                    st.session_state.vision_records,
                    st.session_state.verified_visuals,
                )
            st.session_state.scene_analysis = analysis
            st.session_state.evidence_df = evidence_dataframe(analysis)
        except Exception as exc:
            st.session_state.analysis_errors.append(f"Scene agent: {exc}")

        # C. RAG
        if st.session_state.scene_analysis:
            try:
                with st.spinner("Step C/4 — Retrieving source-grounded NFA/PFSA guidance..."):
                    fingerprint = knowledge_fingerprint("knowledge", st.session_state.agency)
                    rag = load_rag(st.session_state.agency, fingerprint)
                    guidance, sources = retrieve_guidance(
                        client=client,
                        rag=rag,
                        agency=st.session_state.agency,
                        desc=st.session_state.desc,
                        analysis=st.session_state.scene_analysis,
                        vision_records=st.session_state.vision_records,
                        verified_visuals=st.session_state.verified_visuals,
                        user_question=st.session_state.investigator_question,
                    )
                st.session_state.guidance = guidance
                st.session_state.sources = sources
            except Exception as exc:
                st.session_state.analysis_errors.append(f"RAG guidance: {exc}")

        # D. search recommendation
        try:
            with st.spinner("Step D/4 — Recommending scene-search method..."):
                st.session_state.search_plan = recommend_search_method(
                    st.session_state.scene_type,
                    st.session_state.scene_environment,
                    st.session_state.scene_size,
                    st.session_state.personnel_count,
                    st.session_state.obstacle_level,
                )
        except Exception as exc:
            st.session_state.analysis_errors.append(f"Search planning: {exc}")

        st.session_state.analysis_complete = bool(st.session_state.scene_analysis)
        st.session_state.current_step = 2 if st.session_state.vision_records else 3

        if st.session_state.analysis_errors:
            st.warning("Initial analysis completed with some issues:")
            for err in st.session_state.analysis_errors:
                st.write("•", err)
        if st.session_state.analysis_complete:
            st.success("Initial MORBIT analysis completed. Follow the guided next step below.")

st.divider()

# ------------------------------------------------------------
# ANALYSIS SUMMARY + GUIDED NEXT STEP
# ------------------------------------------------------------
st.markdown("## 2. Analysis Status & Guided Next Step")

if not st.session_state.analysis_started:
    st.info("Complete the intake above and press **Save Intake & Start Analysis**.")
else:
    c1,c2,c3 = st.columns(3)
    c1.metric("Images analyzed", len(st.session_state.vision_records))
    c2.metric("Potential evidence", len(st.session_state.evidence_df) if st.session_state.evidence_df is not None else 0)
    c3.metric("Sources retrieved", len(st.session_state.sources))

    if st.session_state.scene_analysis:
        st.markdown("### Initial scene summary")
        st.write(st.session_state.scene_analysis.get("scene_summary",""))

    if st.session_state.search_plan:
        st.markdown("### Recommended search method")
        st.success(st.session_state.search_plan["recommended"])
        st.caption(st.session_state.search_plan["rationale"])

    st.markdown("### What should the user do next?")

    if st.session_state.vision_records and not st.session_state.verified_visuals:
        st.markdown(
            """<div class="next-card"><b>Next: Visual Intelligence</b><br>
            Review every uploaded image and decide which AI-proposed visual observations you accept as investigator-verified.
            Only verified observations should be promoted as confirmed scene context.</div>""",
            unsafe_allow_html=True,
        )
        st.page_link("pages/2_Visual_Intelligence.py", label="➡️ Continue to Visual Verification", icon="📷")
    elif not st.session_state.scene_analysis:
        st.error("Scene analysis has not completed. Review any errors above and run the analysis again.")
    elif st.session_state.scene_map_png is None:
        st.markdown(
            """<div class="next-card"><b>Next: Search Strategy & Scene Map</b><br>
            Confirm the recommended search method and build a north-up scene map using investigator-entered coordinates.</div>""",
            unsafe_allow_html=True,
        )
        st.page_link("pages/4_Search_and_Scene_Map.py", label="➡️ Continue to Search & Scene Map", icon="🧭")
    elif st.session_state.evidence_df is not None and not st.session_state.evidence_df.empty:
        st.markdown(
            """<div class="next-card"><b>Next: Evidence Integrity</b><br>
            Review each evidence record and complete photography, collector, packaging, seal and custody fields.</div>""",
            unsafe_allow_html=True,
        )
        st.page_link("pages/5_Evidence_Integrity.py", label="➡️ Continue to Evidence Integrity", icon="🔐")
    else:
        st.page_link("pages/6_Rich_Report.py", label="➡️ Generate Final Rich Word Report", icon="📄")

st.divider()

# ------------------------------------------------------------
# PAGE DIRECTORY
# ------------------------------------------------------------
st.markdown("## 3. Full Workflow")
p1,p2,p3 = st.columns(3)
with p1:
    st.page_link("pages/1_Scene_Intake.py", label="Scene Intake", icon="📋")
    st.caption("Edit or refine case details.")
    st.page_link("pages/2_Visual_Intelligence.py", label="Visual Intelligence", icon="📷")
    st.caption("Verify image observations.")
with p2:
    st.page_link("pages/3_Agentic_Analysis.py", label="Agentic Analysis", icon="🧠")
    st.caption("Review multimodal analysis and RAG guidance.")
    st.page_link("pages/4_Search_and_Scene_Map.py", label="Search & Scene Map", icon="🧭")
    st.caption("Confirm search strategy and map the scene.")
with p3:
    st.page_link("pages/5_Evidence_Integrity.py", label="Evidence Integrity", icon="🔐")
    st.caption("Track documentation completeness.")
    st.page_link("pages/6_Rich_Report.py", label="Rich Report", icon="📄")
    st.caption("Generate the final formatted DOCX.")

with st.sidebar:
    st.markdown("### MORBIT Command")
    st.caption("The main page is now the starting point for all new users.")
    if st.button("Reset current case", use_container_width=True):
        reset_case_state()
        st.rerun()

    inventory = knowledge_inventory("knowledge")
    with st.expander("System status"):
        st.caption(f"Text: {TEXT_MODEL}")
        st.caption(f"Vision: {VISION_MODEL}")
        st.caption(f"Embeddings: {EMBED_MODEL}")
        st.caption(f"NFA docs: {len(inventory['NFA'])}")
        st.caption(f"PFSA docs: {len(inventory['PFSA'])}")
