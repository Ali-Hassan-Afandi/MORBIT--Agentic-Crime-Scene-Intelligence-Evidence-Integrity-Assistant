import streamlit as st

from core import (
    APP_NAME, EMBED_MODEL, TEXT_MODEL, VISION_MODEL,
    SCENE_TYPES, init_state, reset_case_state, clear_analysis_keep_intake,
    client_from_secrets, scene_agent, retrieve_guidance, evidence_dataframe,
    recommend_search_method, knowledge_fingerprint, load_rag,
    knowledge_inventory, workflow_status, sync_map_items_with_evidence
)
from vision_agent import analyze_image, image_metadata
from ui import apply_ui, hero, render_workflow

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_ui()
init_state()

hero(
    "Case Command Dashboard",
    "Save the case intake first, review up to two scene photographs one at a time, "
    "then start the complete case analysis and follow the guided workflow."
)

st.markdown(
    """<div class="safety-card">
    <b>Hackathon testing mode:</b> use fictional, training or properly authorized case data only.
    AI observations are not laboratory findings and require investigator verification.
    </div>""",
    unsafe_allow_html=True,
)

# Dashboard overview
a,b,c,d = st.columns(4)
a.metric("Case", st.session_state.case_id)
b.metric("Photos reviewed", f"{len(st.session_state.vision_records)}/2")
c.metric("Potential evidence", len(st.session_state.evidence_df) if st.session_state.evidence_df is not None else 0)
d.metric("Workflow", f"{sum(1 for x in workflow_status() if x['done'])}/6")
render_workflow(active_step=st.session_state.current_step)

st.divider()

# Case controls
st.markdown("## Case Controls")
cc1, cc2 = st.columns(2)
with cc1:
    if st.button(
        "♻️ Retake / Correct This Case",
        use_container_width=True,
        help="Keeps the intake text but clears image analysis and all downstream results.",
    ):
        clear_analysis_keep_intake()
        st.success("Derived results cleared. Correct the intake below, save it again, then continue.")
        st.rerun()

with cc2:
    if st.button(
        "🗑️ Clear Entire Case",
        use_container_width=True,
        help="Starts a completely new case after confirmation.",
    ):
        st.session_state["confirm_full_clear"] = True

if st.session_state.get("confirm_full_clear", False):
    st.warning("This will erase the current intake, photos, analysis, map, evidence checklist and report from this session.")
    x1,x2 = st.columns(2)
    if x1.button("Yes — Clear Everything", type="primary", use_container_width=True):
        st.session_state.pop("confirm_full_clear", None)
        reset_case_state()
        st.rerun()
    if x2.button("Cancel", use_container_width=True):
        st.session_state["confirm_full_clear"] = False
        st.rerun()

st.divider()

# ------------------------------------------------------------------
# STEP 1 — SAVE INTAKE FIRST
# ------------------------------------------------------------------
st.markdown("## 1. Save Case Intake")
st.markdown(
    """<div class="input-banner">
    <b>Important:</b> case details are saved first. Photo review and AI case analysis remain disabled
    until the intake has been saved successfully.
    </div>""",
    unsafe_allow_html=True,
)

with st.form("master_intake_form"):
    r1c1,r1c2,r1c3 = st.columns(3)
    case_id = r1c1.text_input("Case ID", value=st.session_state.case_id)
    scene_type = r1c2.selectbox(
        "Crime scene type",
        SCENE_TYPES,
        index=SCENE_TYPES.index(st.session_state.scene_type) if st.session_state.scene_type in SCENE_TYPES else 0,
    )
    scene_dt = r1c3.text_input("Date / Time", value=st.session_state.scene_dt)

    custom_scene = st.session_state.custom_scene_type
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
        height=160,
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

    save_intake = st.form_submit_button(
        "💾 Save Case Intake",
        type="primary",
        use_container_width=True,
    )

if save_intake:
    errors = []
    if not case_id.strip():
        errors.append("Case ID is required.")
    if not desc.strip():
        errors.append("A factual scene description is required.")
    if scene_type == "Other / Custom" and not custom_scene.strip():
        errors.append("Please enter the custom scene type.")

    if errors:
        st.session_state.intake_saved = False
        for msg in errors:
            st.error(msg)
    else:
        # Save intake before any AI processing.
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

        # Any changed intake invalidates previous AI-derived outputs.
        st.session_state.vision_records = []
        st.session_state.verified_visuals = []
        st.session_state.scene_analysis = None
        st.session_state.guidance = ""
        st.session_state.sources = []
        st.session_state.evidence_df = st.session_state.evidence_df.iloc[0:0].copy()
        st.session_state.map_items = st.session_state.map_items.iloc[0:0].copy()
        st.session_state.scene_map_png = None
        st.session_state.search_plan = None
        st.session_state.report_docx = None
        st.session_state.analysis_started = False
        st.session_state.analysis_complete = False
        st.session_state.analysis_errors = []
        st.session_state.photo_1_filename = ""
        st.session_state.photo_2_filename = ""
        st.session_state.intake_saved = True
        st.session_state.current_step = 1

        st.success("Case intake saved. You can now review photographs one at a time before starting full analysis.")

# ------------------------------------------------------------------
# STEP 2 — PHOTO 1, THEN PHOTO 2, EACH AS A SEPARATE API CALL
# ------------------------------------------------------------------
st.divider()
st.markdown("## 2. Review Scene Photographs One at a Time")
st.caption(
    "Maximum 2 photographs for the hackathon. Each photograph is analyzed only when you press its own button, "
    "reducing back-to-back vision requests and helping avoid per-minute token/rate pressure."
)

if not st.session_state.intake_saved:
    st.info("Save the case intake above before uploading or analyzing photographs.")
else:
    client = None

    # Photo 1
    st.markdown("### Photograph 1")
    photo1 = st.file_uploader(
        "Upload Photograph 1",
        type=["jpg","jpeg","png"],
        accept_multiple_files=False,
        key="photo1_upload",
    )
    if photo1 is not None:
        st.image(photo1, caption=photo1.name, width=430)

    if st.button(
        "🔎 Analyze Photograph 1 & Show Recommendation",
        type="primary",
        use_container_width=True,
        disabled=photo1 is None,
    ):
        try:
            client = client_from_secrets()
            data = photo1.getvalue()
            with st.spinner("Analyzing Photograph 1..."):
                meta = image_metadata(data, photo1.name)
                visual = analyze_image(client, data, photo1.name, st.session_state.desc)

            rec = {
                "image_id": "IMG-001",
                "metadata": meta,
                "analysis": visual,
                "image_bytes": data,
            }
            # Replace only slot 1.
            others = [r for r in st.session_state.vision_records if r.get("image_id") != "IMG-001"]
            st.session_state.vision_records = [rec] + others
            st.session_state.vision_records.sort(key=lambda r: r.get("image_id",""))
            st.session_state.photo_1_filename = photo1.name
            st.success("Photograph 1 analyzed and saved.")
        except Exception as exc:
            st.error(f"Photograph 1 analysis failed: {exc}")

    rec1 = next((r for r in st.session_state.vision_records if r.get("image_id") == "IMG-001"), None)
    if rec1:
        a1 = rec1["analysis"]
        st.markdown("#### Photograph 1 — Immediate Findings & Recommendation")
        st.write(a1.get("image_summary",""))
        for s in a1.get("documentation_suggestions", []):
            st.info("Recommendation: " + s)
        with st.expander("Potential visual observations"):
            for obs in a1.get("potential_observations", []):
                st.write(
                    f"• {obs.get('observation','')} "
                    f"({obs.get('confidence','unspecified')} confidence; "
                    f"{obs.get('possible_category','other')})"
                )
        if a1.get("limitations"):
            st.caption("Limitations: " + "; ".join(a1["limitations"]))

    # Photo 2 appears after photo 1 has been analyzed, enforcing sequence.
    if rec1:
        st.divider()
        st.markdown("### Photograph 2 — Optional")
        photo2 = st.file_uploader(
            "Upload Photograph 2",
            type=["jpg","jpeg","png"],
            accept_multiple_files=False,
            key="photo2_upload",
        )
        if photo2 is not None:
            st.image(photo2, caption=photo2.name, width=430)

        if st.button(
            "🔎 Analyze Photograph 2 & Show Recommendation",
            type="primary",
            use_container_width=True,
            disabled=photo2 is None,
        ):
            try:
                if client is None:
                    client = client_from_secrets()
                data = photo2.getvalue()
                with st.spinner("Analyzing Photograph 2..."):
                    meta = image_metadata(data, photo2.name)
                    visual = analyze_image(client, data, photo2.name, st.session_state.desc)

                rec = {
                    "image_id": "IMG-002",
                    "metadata": meta,
                    "analysis": visual,
                    "image_bytes": data,
                }
                others = [r for r in st.session_state.vision_records if r.get("image_id") != "IMG-002"]
                st.session_state.vision_records = others + [rec]
                st.session_state.vision_records.sort(key=lambda r: r.get("image_id",""))
                st.session_state.photo_2_filename = photo2.name
                st.success("Photograph 2 analyzed and saved.")
            except Exception as exc:
                st.error(f"Photograph 2 analysis failed: {exc}")

        rec2 = next((r for r in st.session_state.vision_records if r.get("image_id") == "IMG-002"), None)
        if rec2:
            a2 = rec2["analysis"]
            st.markdown("#### Photograph 2 — Immediate Findings & Recommendation")
            st.write(a2.get("image_summary",""))
            for s in a2.get("documentation_suggestions", []):
                st.info("Recommendation: " + s)
            with st.expander("Potential visual observations"):
                for obs in a2.get("potential_observations", []):
                    st.write(
                        f"• {obs.get('observation','')} "
                        f"({obs.get('confidence','unspecified')} confidence; "
                        f"{obs.get('possible_category','other')})"
                    )
            if a2.get("limitations"):
                st.caption("Limitations: " + "; ".join(a2["limitations"]))

# ------------------------------------------------------------------
# STEP 3 — START FULL CASE ANALYSIS
# ------------------------------------------------------------------
st.divider()
st.markdown("## 3. Start Case Analysis")
st.markdown(
    """<div class="next-action">
    <strong>Ready when the intake is saved.</strong><br>
    The full analysis uses the saved intake plus any photographs already analyzed above.
    It does not send the photographs to the vision model again.
    </div>""",
    unsafe_allow_html=True,
)

if st.button(
    "🚀 START FULL CASE ANALYSIS",
    type="primary",
    use_container_width=True,
    disabled=not st.session_state.intake_saved,
):
    st.session_state.analysis_started = True
    st.session_state.analysis_complete = False
    st.session_state.analysis_errors = []

    client = client_from_secrets()
    effective_scene_type = (
        st.session_state.custom_scene_type
        if st.session_state.scene_type == "Other / Custom" and st.session_state.custom_scene_type
        else st.session_state.scene_type
    )

    try:
        with st.spinner("Running multimodal scene-analysis agent..."):
            analysis = scene_agent(
                client,
                st.session_state.desc,
                effective_scene_type,
                st.session_state.vision_records,
                st.session_state.verified_visuals,
            )
        st.session_state.scene_analysis = analysis
        st.session_state.evidence_df = evidence_dataframe(analysis)
        st.session_state.map_items = sync_map_items_with_evidence(
            st.session_state.map_items,
            st.session_state.evidence_df,
        )
    except Exception as exc:
        st.session_state.analysis_errors.append(f"Scene agent: {exc}")

    if st.session_state.scene_analysis:
        try:
            with st.spinner("Retrieving source-grounded NFA/PFSA guidance..."):
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

    try:
        with st.spinner("Recommending scene-search method..."):
            st.session_state.search_plan = recommend_search_method(
                effective_scene_type,
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
        st.warning("Analysis completed with some issues:")
        for err in st.session_state.analysis_errors:
            st.write("•", err)
    if st.session_state.analysis_complete:
        st.success("Case analysis completed. Potential evidence has been synchronized with the Scene of Crime site-plan table.")

# ------------------------------------------------------------------
# GUIDED NEXT STEP
# ------------------------------------------------------------------
st.divider()
st.markdown("## 4. Guided Next Step")

if not st.session_state.analysis_started:
    st.info("Save the intake, optionally analyze one or two photographs, then press **START FULL CASE ANALYSIS**.")
else:
    c1,c2,c3 = st.columns(3)
    c1.metric("Photos analyzed", f"{len(st.session_state.vision_records)}/2")
    c2.metric("Potential evidence", len(st.session_state.evidence_df) if st.session_state.evidence_df is not None else 0)
    c3.metric("Sources retrieved", len(st.session_state.sources))

    if st.session_state.scene_analysis:
        st.markdown("### Initial scene summary")
        st.write(st.session_state.scene_analysis.get("scene_summary",""))

    if st.session_state.search_plan:
        st.markdown("### Recommended search method")
        st.success(st.session_state.search_plan["recommended"])
        st.caption(st.session_state.search_plan["rationale"])

    if st.session_state.vision_records:
        st.markdown(
            """<div class="next-action"><strong>NEXT STEP → Visual Verification</strong><br>
            Review the photo observations and tick only those that you personally verify.
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("➡️ CONTINUE TO VISUAL VERIFICATION", type="primary", use_container_width=True):
            st.switch_page("pages/2_Visual_Intelligence.py")
    elif st.session_state.scene_analysis:
        st.markdown(
            """<div class="next-action"><strong>NEXT STEP → Search Strategy & Scene Map</strong><br>
            Confirm the search method and enter coordinates for the automatically listed evidence.
            </div>""",
            unsafe_allow_html=True,
        )
        if st.button("➡️ CONTINUE TO SEARCH & SCENE MAP", type="primary", use_container_width=True):
            st.switch_page("pages/4_Search_and_Scene_Map.py")

st.divider()

st.markdown("## Full Workflow")
p1,p2,p3 = st.columns(3)
with p1:
    st.page_link("pages/1_Scene_Intake.py", label="Scene Intake", icon="📋")
    st.page_link("pages/2_Visual_Intelligence.py", label="Visual Intelligence", icon="📷")
with p2:
    st.page_link("pages/3_Agentic_Analysis.py", label="Agentic Analysis", icon="🧠")
    st.page_link("pages/4_Search_and_Scene_Map.py", label="Search & Scene Map", icon="🧭")
with p3:
    st.page_link("pages/5_Evidence_Integrity.py", label="Evidence Integrity", icon="🔐")
    st.page_link("pages/6_Rich_Report.py", label="Rich Report", icon="📄")

with st.sidebar:
    st.markdown("### 🎛️ Case Controls")
    if st.button("♻️ Retake Case", use_container_width=True):
        clear_analysis_keep_intake()
        st.rerun()
    if st.button("🗑️ Clear Case", use_container_width=True):
        st.session_state["confirm_full_clear"] = True
        st.rerun()

    inventory = knowledge_inventory("knowledge")
    with st.expander("System status"):
        st.caption(f"Text: {TEXT_MODEL}")
        st.caption(f"Vision: {VISION_MODEL}")
        st.caption(f"Embeddings: {EMBED_MODEL}")
        st.caption(f"NFA docs: {len(inventory['NFA'])}")
        st.caption(f"PFSA docs: {len(inventory['PFSA'])}")
