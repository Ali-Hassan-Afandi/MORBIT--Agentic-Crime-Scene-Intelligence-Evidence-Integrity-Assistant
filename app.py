import html
import pandas as pd
import streamlit as st

from core import (
    APP_NAME,
    SCENE_TYPES,
    init_state,
    reset_case_state,
    client_from_secrets,
    scene_agent,
    retrieve_guidance,
    evidence_dataframe,
    recommend_search_method,
    knowledge_fingerprint,
    load_rag,
    sync_map_items_with_evidence,
    normalize_evidence_checklist,
    integrity_score,
    case_snapshot,
    build_case_prompt,
    workflow_status,
)
from vision_agent import analyze_image, image_metadata
from scene_map import generate_scene_map
from report_builder import build_rich_report



# ------------------------------------------------------------------
# EMBEDDED UI HELPERS
# Keeping these in app.py removes the deployment-time dependency on
# matching versions of app.py and ui.py.
# ------------------------------------------------------------------

def apply_ui():
    init_state()
    st.markdown("""
    <style>
      [data-testid="stSidebar"],
      [data-testid="collapsedControl"]{
        display:none !important;
      }

      .block-container{
        max-width:none;
        padding-top:1rem;
        padding-bottom:4rem;
        padding-left:2rem;
        padding-right:338px;
      }

      .morbit-hero{
        padding:30px 34px;
        border-radius:24px;
        margin-bottom:18px;
        color:white;
        background:
          radial-gradient(circle at 86% 14%,rgba(49,198,216,.28),transparent 24%),
          radial-gradient(circle at 8% 100%,rgba(122,92,229,.25),transparent 30%),
          linear-gradient(135deg,#071827 0%,#103956 58%,#176A86 100%);
        box-shadow:0 18px 46px rgba(0,0,0,.20);
        border:1px solid rgba(255,255,255,.07);
      }

      .morbit-kicker{
        font-size:11px;
        font-weight:850;
        letter-spacing:.16em;
        color:#95F2FF;
      }
      .morbit-title{
        font-size:36px;
        font-weight:900;
        line-height:1.08;
        margin-top:7px;
      }
      .morbit-sub{
        font-size:14px;
        color:#D8EAF5;
        margin-top:8px;
      }

      .panel{
        padding:15px 17px;
        border-radius:16px;
        border:1px solid rgba(75,135,170,.20);
        background:linear-gradient(
          145deg,
          rgba(23,110,165,.07),
          rgba(122,92,229,.04)
        );
        margin:8px 0 14px 0;
      }

      .evidence-card{
        padding:13px 15px;
        border-radius:15px;
        margin:8px 0;
        border:1px solid rgba(49,198,216,.21);
        background:linear-gradient(
          145deg,
          rgba(49,198,216,.075),
          rgba(122,92,229,.045)
        );
      }
      .evidence-card.body-first{
        border-color:rgba(240,165,60,.48);
        background:linear-gradient(
          145deg,
          rgba(240,165,60,.12),
          rgba(217,91,138,.05)
        );
      }
      .evidence-rank{
        display:inline-block;
        min-width:25px;
        text-align:center;
        padding:3px 7px;
        border-radius:10px;
        background:#176EA5;
        color:white;
        font-weight:900;
        margin-right:6px;
      }
      .evidence-card.body-first .evidence-rank{
        background:#C87819;
      }
      .evidence-meta{
        font-size:11px;
        opacity:.76;
        margin-top:5px;
      }

      div[data-testid="stMetric"]{
        border:1px solid rgba(110,145,170,.18);
        border-radius:15px;
        padding:9px 11px;
        background:linear-gradient(
          145deg,
          rgba(23,110,165,.06),
          rgba(122,92,229,.035)
        );
      }

      div[data-testid="stFileUploader"]{
        border:1px dashed rgba(49,198,216,.35);
        border-radius:17px;
        padding:8px;
      }

      .stButton>button{
        border-radius:12px;
        font-weight:700;
      }
      .stButton>button[kind="primary"]{
        border:0;
        color:white;
        background:linear-gradient(
          90deg,
          #176EA5,
          #31C6D8 55%,
          #7A5CE5
        );
        box-shadow:0 8px 20px rgba(49,198,216,.18);
      }

      .ready-box{
        padding:15px 17px;
        border-radius:15px;
        border-left:5px solid #31C6D8;
        background:linear-gradient(
          90deg,
          rgba(49,198,216,.11),
          rgba(122,92,229,.05)
        );
      }

      .complete-box{
        padding:15px 17px;
        border-radius:15px;
        border-left:5px solid #2FB47C;
        background:linear-gradient(
          90deg,
          rgba(47,180,124,.12),
          rgba(49,198,216,.04)
        );
      }

      .morbit-right-rail{
        position:fixed;
        top:68px;
        right:18px;
        width:294px;
        max-height:calc(100vh - 88px);
        overflow:auto;
        z-index:99999;
        padding:16px;
        border-radius:20px;
        color:#EAF6FF;
        border:1px solid rgba(49,198,216,.24);
        background:
          radial-gradient(
            circle at 20% 8%,
            rgba(49,198,216,.12),
            transparent 24%
          ),
          radial-gradient(
            circle at 90% 35%,
            rgba(122,92,229,.10),
            transparent 28%
          ),
          linear-gradient(
            180deg,
            rgba(7,24,39,.97),
            rgba(11,34,55,.97)
          );
        box-shadow:0 18px 44px rgba(0,0,0,.28);
        backdrop-filter:blur(14px);
      }

      .rail-title{
        font-size:15px;
        font-weight:900;
      }
      .rail-sub{
        font-size:10px;
        color:#9FB8CB;
        margin-top:2px;
        margin-bottom:10px;
      }
      .rail-summary{
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:7px;
        margin-bottom:12px;
      }
      .rail-metric{
        padding:9px 8px;
        border-radius:12px;
        background:rgba(255,255,255,.04);
        border:1px solid rgba(255,255,255,.06);
      }
      .rail-metric b{
        font-size:16px;
      }
      .rail-metric span{
        display:block;
        font-size:9px;
        color:#9FB8CB;
        margin-top:2px;
      }

      .rail-progress-bg{
        height:7px;
        border-radius:999px;
        background:rgba(255,255,255,.08);
        overflow:hidden;
        margin:8px 0 13px;
      }
      .rail-progress-fill{
        height:100%;
        background:linear-gradient(
          90deg,
          #2FB47C,
          #31C6D8,
          #7A5CE5
        );
        border-radius:999px;
      }

      .rail-step{
        padding:9px 10px;
        margin:6px 0;
        border-radius:12px;
        border:1px solid rgba(130,155,178,.14);
        background:rgba(255,255,255,.025);
      }
      .rail-step.done{
        border-color:rgba(47,180,124,.40);
        background:rgba(47,180,124,.08);
      }
      .rail-step.current{
        border-color:rgba(49,198,216,.55);
        background:linear-gradient(
          90deg,
          rgba(49,198,216,.13),
          rgba(122,92,229,.08)
        );
        box-shadow:0 7px 18px rgba(49,198,216,.08);
      }
      .rail-step-title{
        font-size:11px;
        font-weight:850;
      }
      .rail-step-status{
        font-size:9px;
        color:#9FB8CB;
        margin-top:2px;
      }
      .rail-case{
        margin-top:12px;
        padding-top:10px;
        border-top:1px solid rgba(255,255,255,.08);
        font-size:9px;
        color:#9FB8CB;
        line-height:1.55;
      }

      @media(max-width:1050px){
        .block-container{
          padding-right:1rem;
          padding-left:1rem;
          padding-bottom:150px;
        }
        .morbit-right-rail{
          top:auto;
          right:10px;
          left:10px;
          bottom:10px;
          width:auto;
          max-height:none;
          overflow:hidden;
          padding:10px 12px;
          border-radius:17px;
        }
        .rail-title,
        .rail-sub,
        .rail-summary,
        .rail-case{
          display:none;
        }
        .rail-progress-bg{
          margin:4px 0 8px;
        }
        .rail-steps{
          display:grid;
          grid-template-columns:repeat(6,1fr);
          gap:4px;
        }
        .rail-step{
          margin:0;
          padding:7px 5px;
          text-align:center;
        }
        .rail-step-title{
          font-size:9px;
        }
        .rail-step-status{
          display:none;
        }
      }

      @media(max-width:700px){
        .morbit-title{
          font-size:28px;
        }
        .morbit-hero{
          padding:23px 20px;
        }
        .rail-step-title{
          font-size:0;
        }
        .rail-step-title .rail-mobile-icon{
          font-size:14px;
        }
      }
    </style>
    """, unsafe_allow_html=True)


def hero(subtitle: str):
    st.markdown(
        f"""
        <div class="morbit-hero">
          <div class="morbit-kicker">
            HUMAN-SUPERVISED FORENSIC DOCUMENTATION
          </div>
          <div class="morbit-title">
            {APP_NAME}
          </div>
          <div class="morbit-sub">
            {html.escape(str(subtitle))}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def progress_rail():
    status = workflow_status()
    done = sum(1 for item in status if item["done"])
    next_step = next(
        (item["step"] for item in status if not item["done"]),
        6,
    )
    pct = int(round((done / 6) * 100))

    evidence_count = (
        len(st.session_state.evidence_df)
        if st.session_state.evidence_df is not None
        else 0
    )

    step_html = []
    for item in status:
        if item["done"]:
            css_class = "done"
            icon = "✅"
            state_text = "Completed"
        elif item["step"] == next_step:
            css_class = "current"
            icon = "●"
            state_text = "Current / Next"
        else:
            css_class = ""
            icon = "○"
            state_text = "Pending"

        step_html.append(
            f"""
            <div class="rail-step {css_class}">
              <div class="rail-step-title">
                <span class="rail-mobile-icon">{icon}</span>
                {item['step']}. {html.escape(item['label'])}
              </div>
              <div class="rail-step-status">
                {state_text}
              </div>
            </div>
            """
        )

    case_id = html.escape(str(st.session_state.case_id))
    scene_type = html.escape(str(st.session_state.scene_type))

    st.markdown(
        f"""
        <div class="morbit-right-rail">
          <div class="rail-title">
            🛡️ Case Progress
          </div>
          <div class="rail-sub">
            Permanent guided workflow tracker
          </div>

          <div class="rail-summary">
            <div class="rail-metric">
              <b>{done}/6</b>
              <span>Functions complete</span>
            </div>
            <div class="rail-metric">
              <b>{evidence_count}</b>
              <span>Evidence rows</span>
            </div>
          </div>

          <div class="rail-progress-bg">
            <div
              class="rail-progress-fill"
              style="width:{pct}%"
            ></div>
          </div>

          <div class="rail-steps">
            {''.join(step_html)}
          </div>

          <div class="rail-case">
            <b>Case:</b> {case_id}<br>
            <b>Scene:</b> {scene_type}<br>
            AI visual findings remain proposals until investigator verification.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def evidence_card(obs: dict):
    rank = obs.get("priority_rank", "")
    is_body = (
        obs.get("possible_category")
        == "possible_human_body_or_remains"
    )
    body_class = "body-first" if is_body else ""
    prefix = (
        "Possible body/remains priority"
        if is_body
        else "Evidence priority"
    )

    st.markdown(
        f"""
        <div class="evidence-card {body_class}">
          <span class="evidence-rank">
            {rank}
          </span>
          <b>{html.escape(str(obs.get('observation','')))}</b>

          <div class="evidence-meta">
            {prefix}
            &nbsp; • &nbsp;
            📍 {html.escape(str(obs.get('location_in_image','Location not specified')))}
            &nbsp; • &nbsp;
            {html.escape(str(obs.get('possible_category','other')))}
            &nbsp; • &nbsp;
            {html.escape(str(obs.get('confidence','unspecified')))} confidence
          </div>

          <div class="evidence-meta">
            {html.escape(str(obs.get('importance_reason','')))}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(
    page_title=APP_NAME,
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

apply_ui()
init_state()
progress_rail()

hero(
    "Enter all case inputs in one Case Intake workspace, verify the five highest-priority "
    "visual evidence candidates at the image-analysis point, then follow the guided workflow "
    "to documentation completeness, scene map and final draft report."
)

if st.button("🗑️ Start New Case", help="Clear the current case session and begin again."):
    reset_case_state()
    st.rerun()

st.markdown("## Step 1–3 • Case Intake Workspace")
st.caption(
    "The three sub-tabs below collect the complete case prompt, the persistent scene photograph "
    "and the search-planning inputs. The downstream analysis uses these saved inputs automatically."
)

tab_case, tab_photo, tab_search = st.tabs([
    "📝 A. Case Details & Narrative",
    "📷 B. Photograph & Visual Evidence",
    "🧭 C. Crime Scene Search Inputs",
])

# ------------------------------------------------------------------
# TAB A — CASE DETAILS
# ------------------------------------------------------------------
with tab_case:
    st.markdown("### A. Case Details & Narrative")
    st.markdown(
        '<div class="panel"><b>Purpose:</b> This complete case intake becomes the grounded prompt '
        'for downstream scene analysis and source-grounded guidance.</div>',
        unsafe_allow_html=True,
    )

    with st.form("case_details_form"):
        c1,c2,c3 = st.columns(3)
        case_id = c1.text_input("Case ID", value=st.session_state.case_id)
        scene_type = c2.selectbox(
            "Crime scene type",
            SCENE_TYPES,
            index=SCENE_TYPES.index(st.session_state.scene_type)
            if st.session_state.scene_type in SCENE_TYPES else 0,
        )
        scene_dt = c3.text_input("Date / Time", value=st.session_state.scene_dt)

        custom_scene = st.session_state.custom_scene_type
        if scene_type == "Other / Custom":
            custom_scene = st.text_input(
                "Custom scene type",
                value=st.session_state.custom_scene_type,
            )

        location = st.text_input("Scene location", value=st.session_state.location)
        desc = st.text_area(
            "Investigator factual scene narrative",
            value=st.session_state.desc,
            height=190,
            placeholder=(
                "Describe visible scene conditions, known boundaries, reported circumstances, "
                "positions and factual observations. Avoid laboratory conclusions."
            ),
        )

        st.markdown("#### Forensic knowledge source")
        agency_label = st.radio(
            "Authority mode",
            ["NFA Pakistan","PFSA Punjab","NFA + PFSA"],
            horizontal=True,
            index={"NFA":0,"PFSA":1,"BOTH":2}.get(st.session_state.agency,2),
        )
        question = st.text_input(
            "Optional procedure / forensic knowledge question",
            value=st.session_state.investigator_question,
        )

        save_case = st.form_submit_button(
            "💾 Save Case Details",
            type="primary",
            use_container_width=True,
        )

    if save_case:
        errors = []
        if not case_id.strip():
            errors.append("Case ID is required.")
        if not desc.strip():
            errors.append("A factual scene narrative is required.")
        if scene_type == "Other / Custom" and not custom_scene.strip():
            errors.append("Enter the custom scene type.")

        if errors:
            for e in errors:
                st.error(e)
        else:
            changed = any([
                st.session_state.case_id != case_id.strip(),
                st.session_state.scene_type != scene_type,
                st.session_state.desc != desc.strip(),
                st.session_state.location != location.strip(),
            ])

            st.session_state.case_id = case_id.strip()
            st.session_state.scene_type = scene_type
            st.session_state.custom_scene_type = custom_scene.strip()
            st.session_state.scene_dt = scene_dt.strip()
            st.session_state.location = location.strip()
            st.session_state.desc = desc.strip()
            st.session_state.agency = {
                "NFA Pakistan":"NFA","PFSA Punjab":"PFSA","NFA + PFSA":"BOTH"
            }[agency_label]
            st.session_state.investigator_question = question.strip()
            st.session_state.intake_saved = True

            if changed:
                # Keep the case text, but invalidate downstream derived outputs.
                st.session_state.vision_records = []
                st.session_state.verified_visuals = []
                st.session_state.visual_verification_saved = False
                st.session_state.search_inputs_saved = False
                st.session_state.scene_analysis = None
                st.session_state.guidance = ""
                st.session_state.sources = []
                st.session_state.evidence_df = pd.DataFrame()
                st.session_state.map_items = pd.DataFrame(
                    columns=["Evidence ID","Evidence Item","Category","X","Y","Notes"]
                )
                st.session_state.scene_map_png = None
                st.session_state.search_plan = None
                st.session_state.analysis_started = False
                st.session_state.analysis_complete = False
                st.session_state.evidence_checklist_saved = False
                st.session_state.map_coordinates_saved = False
                st.session_state.report_docx = None

            st.success("Case details saved. Continue to the Photograph & Visual Evidence sub-tab.")

    if st.session_state.intake_saved:
        with st.expander("Preview downstream case prompt"):
            st.code(build_case_prompt(), language=None)

# ------------------------------------------------------------------
# TAB B — PHOTO + IMMEDIATE VISUAL VERIFICATION
# ------------------------------------------------------------------
with tab_photo:
    st.markdown("### B. Photograph & Immediate Visual Evidence Verification")

    if not st.session_state.intake_saved:
        st.info("Save Case Details first.")
    else:
        scene_photo = st.file_uploader(
            "Upload ONE representative scene photograph",
            type=["jpg","jpeg","png"],
            accept_multiple_files=False,
            key="guided_single_scene_photo",
        )

        if scene_photo is not None:
            data = scene_photo.getvalue()
            try:
                meta = image_metadata(data, scene_photo.name)
                existing_hash = (
                    st.session_state.vision_records[0].get("metadata", {}).get("sha256")
                    if st.session_state.vision_records else ""
                )

                if meta["sha256"] != existing_hash:
                    st.session_state.vision_records = [{
                        "image_id": "IMG-001",
                        "metadata": meta,
                        "analysis": {},
                        "image_bytes": data,
                    }]
                    st.session_state.photo_1_filename = scene_photo.name
                    st.session_state.verified_visuals = []
                    st.session_state.visual_verification_saved = False
                    st.session_state.scene_analysis = None
                    st.session_state.analysis_complete = False
                    st.session_state.evidence_df = pd.DataFrame()
                    st.session_state.map_items = pd.DataFrame(
                        columns=["Evidence ID","Evidence Item","Category","X","Y","Notes"]
                    )
                    st.session_state.scene_map_png = None
                    st.session_state.evidence_checklist_saved = False
                    st.session_state.map_coordinates_saved = False
                    st.session_state.report_docx = None
            except Exception as exc:
                st.error(f"Could not save photograph: {exc}")

        if st.session_state.vision_records:
            record = st.session_state.vision_records[0]
            st.image(
                record["image_bytes"],
                caption=record["metadata"]["filename"],
                width=520,
            )
            st.caption(
                "The image bytes, metadata and SHA-256 are already stored in this case session. "
                "No re-upload or manual refresh is needed later."
            )

            analyzed = bool(record.get("analysis", {}).get("image_summary"))
            if st.button(
                "🔎 Analyze Image for Top 5 Visual Evidence Candidates"
                if not analyzed else
                "🔁 Re-analyze Top 5 Visual Evidence Candidates",
                type="primary",
                use_container_width=True,
            ):
                try:
                    with st.spinner("Reviewing the photograph and ranking the five most important visible evidence candidates..."):
                        client = client_from_secrets()
                        effective_scene_type = (
                            st.session_state.custom_scene_type
                            if st.session_state.scene_type == "Other / Custom"
                            and st.session_state.custom_scene_type
                            else st.session_state.scene_type
                        )
                        visual = analyze_image(
                            client,
                            record["image_bytes"],
                            record["metadata"]["filename"],
                            build_case_prompt(),
                            effective_scene_type,
                        )
                    st.session_state.vision_records[0]["analysis"] = visual
                    st.session_state.verified_visuals = []
                    st.session_state.visual_verification_saved = False
                    st.session_state.scene_analysis = None
                    st.session_state.analysis_complete = False
                    st.session_state.report_docx = None
                    st.success("Image analyzed. Verify the proposed visual evidence immediately below.")
                except Exception as exc:
                    st.error(
                        "Vision analysis could not complete. The photograph remains safely stored "
                        "in the case session, so you can retry without uploading it again. "
                        f"Provider message: {exc}"
                    )

            analysis = st.session_state.vision_records[0].get("analysis", {})
            if analysis.get("image_summary"):
                st.markdown("#### Image Summary")
                st.write(analysis["image_summary"])

                observations = analysis.get("potential_observations", [])
                st.metric("Ranked visual candidates", len(observations))

                if analysis.get("scene_priority_mode") == "death_scene_body_first":
                    st.warning(
                        "Death-scene priority mode: MORBIT checks the whole photograph for every "
                        "visually supportable possible human body/body-like form/possible human remains "
                        "before ranking other evidence. Image appearance alone does not confirm death."
                    )

                st.markdown("#### Investigator Confirmation")
                st.caption(
                    "Confirm only what you can personally verify from the photograph. "
                    "Unchecked AI proposals will not be promoted to investigator-verified context."
                )

                with st.form("visual_confirmation_form"):
                    checked = []
                    for idx, obs in enumerate(observations):
                        evidence_card(obs)
                        verified = st.checkbox(
                            f"Verify candidate #{obs.get('priority_rank', idx+1)}",
                            key=f"visual_verify_{idx}",
                        )
                        checked.append((verified, obs))

                    save_visual = st.form_submit_button(
                        "✅ Save Investigator-Verified Visual Evidence",
                        type="primary",
                        use_container_width=True,
                    )

                if save_visual:
                    verified_visuals = []
                    for ok, obs in checked:
                        if ok:
                            verified_visuals.append(
                                f"Priority {obs.get('priority_rank','')}: "
                                f"{obs.get('observation','')} "
                                f"[visible location: {obs.get('location_in_image','not specified')}]"
                            )
                    st.session_state.verified_visuals = verified_visuals
                    st.session_state.visual_verification_saved = True
                    st.session_state.report_docx = None
                    st.success(
                        f"Visual verification saved. {len(verified_visuals)} candidate(s) adopted as investigator-verified."
                    )

                if analysis.get("documentation_suggestions"):
                    with st.expander("Photography / documentation suggestions"):
                        for item in analysis["documentation_suggestions"]:
                            st.write("•", item)
                if analysis.get("limitations"):
                    st.caption("Vision limitations: " + "; ".join(analysis["limitations"]))
            else:
                st.info("Analyze the saved photograph to reveal and verify the top five visual evidence candidates.")
        else:
            st.info("Upload the representative scene photograph here.")

# ------------------------------------------------------------------
# TAB C — SEARCH INPUTS
# ------------------------------------------------------------------
with tab_search:
    st.markdown("### C. Crime Scene Search Inputs")
    if not st.session_state.intake_saved:
        st.info("Save Case Details first.")
    else:
        with st.form("search_inputs_form"):
            a,b,c,d = st.columns(4)
            env_options = ["Indoor","Building / Multi-room","Outdoor","Open Terrain","Vehicle / Roadway","Underwater"]
            environment = a.selectbox(
                "Environment",
                env_options,
                index=env_options.index(st.session_state.scene_environment)
                if st.session_state.scene_environment in env_options else 0,
            )
            size_options = ["Small","Medium","Large","Very Large"]
            scene_size = b.selectbox(
                "Scene size",
                size_options,
                index=size_options.index(st.session_state.scene_size)
                if st.session_state.scene_size in size_options else 1,
            )
            personnel = c.number_input(
                "Available search personnel",
                min_value=1,max_value=50,
                value=int(st.session_state.personnel_count),
            )
            obstacle_options = ["Low","Moderate","High"]
            obstacles = d.selectbox(
                "Obstacle / complexity",
                obstacle_options,
                index=obstacle_options.index(st.session_state.obstacle_level)
                if st.session_state.obstacle_level in obstacle_options else 1,
            )

            save_search = st.form_submit_button(
                "💾 Save Search Inputs & Recommend Method",
                type="primary",
                use_container_width=True,
            )

        if save_search:
            st.session_state.scene_environment = environment
            st.session_state.scene_size = scene_size
            st.session_state.personnel_count = int(personnel)
            st.session_state.obstacle_level = obstacles

            effective_type = (
                st.session_state.custom_scene_type
                if st.session_state.scene_type == "Other / Custom" and st.session_state.custom_scene_type
                else st.session_state.scene_type
            )
            st.session_state.search_plan = recommend_search_method(
                effective_type,
                environment,
                scene_size,
                int(personnel),
                obstacles,
            )
            st.session_state.search_inputs_saved = True
            st.session_state.scene_map_png = None
            st.session_state.map_coordinates_saved = False
            st.session_state.report_docx = None
            st.success("Search inputs saved.")

        if st.session_state.search_plan:
            st.success("Recommended method: " + st.session_state.search_plan["recommended"])
            st.caption(st.session_state.search_plan["rationale"])
            with st.expander("Alternative & operational caution"):
                st.write("Alternative:", st.session_state.search_plan["alternative"])
                st.write(st.session_state.search_plan["caution"])

# ------------------------------------------------------------------
# READINESS
# ------------------------------------------------------------------
st.divider()
st.markdown("## Step 4 • Run Guided Case Analysis")

requirements = {
    "Case details saved": bool(st.session_state.intake_saved),
    "Photograph analyzed": bool(
        st.session_state.vision_records
        and st.session_state.vision_records[0].get("analysis", {}).get("image_summary")
    ),
    "Visual evidence confirmation saved": bool(st.session_state.visual_verification_saved),
    "Search inputs saved": bool(st.session_state.search_inputs_saved),
}
rcols = st.columns(4)
for col, (label, ok) in zip(rcols, requirements.items()):
    col.metric(label, "Ready" if ok else "Pending")

ready_for_analysis = all(requirements.values())

if ready_for_analysis:
    st.markdown(
        '<div class="ready-box"><b>All case inputs are ready.</b><br>'
        'The next action uses the saved Case Details as the main prompt, adds the investigator-verified '
        'visual evidence, creates the evidence inventory and retrieves configured NFA/PFSA guidance.</div>',
        unsafe_allow_html=True,
    )
else:
    st.info("Complete the three Case Intake sub-tabs before running case analysis.")

if st.button(
    "🚀 Run Case Analysis & Build Evidence Inventory",
    type="primary",
    use_container_width=True,
    disabled=not ready_for_analysis,
):
    st.session_state.analysis_started = True
    st.session_state.analysis_complete = False
    st.session_state.analysis_errors = []

    client = client_from_secrets()
    case_prompt = build_case_prompt()
    effective_type = (
        st.session_state.custom_scene_type
        if st.session_state.scene_type == "Other / Custom" and st.session_state.custom_scene_type
        else st.session_state.scene_type
    )

    try:
        with st.spinner("Building scene analysis from the complete case prompt and verified visual context..."):
            analysis = scene_agent(
                client,
                case_prompt,
                effective_type,
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
        st.session_state.analysis_errors.append(f"Scene analysis: {exc}")

    if st.session_state.scene_analysis:
        try:
            with st.spinner("Retrieving configured source-grounded forensic guidance..."):
                fingerprint = knowledge_fingerprint("knowledge", st.session_state.agency)
                rag = load_rag(st.session_state.agency, fingerprint)
                guidance, sources = retrieve_guidance(
                    client=client,
                    rag=rag,
                    agency=st.session_state.agency,
                    desc=case_prompt,
                    analysis=st.session_state.scene_analysis,
                    vision_records=st.session_state.vision_records,
                    verified_visuals=st.session_state.verified_visuals,
                    user_question=st.session_state.investigator_question,
                )
            st.session_state.guidance = guidance
            st.session_state.sources = sources
        except Exception as exc:
            st.session_state.analysis_errors.append(f"Source-grounded guidance: {exc}")

    st.session_state.analysis_complete = bool(st.session_state.scene_analysis)
    st.session_state.evidence_checklist_saved = False
    st.session_state.map_coordinates_saved = False
    st.session_state.scene_map_png = None
    st.session_state.report_docx = None

    if st.session_state.analysis_errors:
        st.warning("Case analysis completed with these non-fatal issue(s):")
        for err in st.session_state.analysis_errors:
            st.write("•", err)
    if st.session_state.analysis_complete:
        st.success("Case analysis complete. Continue to documentation completeness below.")

if st.session_state.scene_analysis:
    with st.expander("Scene analysis summary", expanded=True):
        st.write(st.session_state.scene_analysis.get("scene_summary",""))
        if st.session_state.scene_analysis.get("hazards"):
            st.markdown("**Potential hazards / cautions**")
            for x in st.session_state.scene_analysis["hazards"]:
                st.write("•", x)

# ------------------------------------------------------------------
# STEP 5A — DOCUMENTATION COMPLETENESS
# ------------------------------------------------------------------
st.divider()
st.markdown("## Step 5 • Evidence Documentation Completeness")

if not st.session_state.analysis_complete:
    st.info("Run Case Analysis first.")
elif st.session_state.evidence_df is None or st.session_state.evidence_df.empty:
    st.warning("No evidence inventory was generated. The draft can still document this limitation.")
    st.session_state.evidence_checklist_saved = True
else:
    checklist = normalize_evidence_checklist(st.session_state.evidence_df)

    with st.form("documentation_checklist_form"):
        edited = st.data_editor(
            checklist,
            hide_index=True,
            use_container_width=True,
            disabled=["Evidence ID","Item","Category","Location","Basis"],
            column_config={
                "Photographed": st.column_config.CheckboxColumn("Photographed"),
                "Collector Recorded": st.column_config.CheckboxColumn("Collector Recorded"),
                "Packaging Recorded": st.column_config.CheckboxColumn("Packaging Recorded"),
                "Seal Recorded": st.column_config.CheckboxColumn("Seal Recorded"),
                "Custody Started": st.column_config.CheckboxColumn("Custody Started"),
            },
        )
        save_checklist = st.form_submit_button(
            "✅ Save Documentation Checklist",
            type="primary",
            use_container_width=True,
        )

    if save_checklist:
        st.session_state.evidence_df = normalize_evidence_checklist(edited)
        st.session_state.evidence_checklist_saved = True
        st.session_state.map_items = sync_map_items_with_evidence(
            st.session_state.map_items,
            st.session_state.evidence_df,
        )
        st.session_state.report_docx = None
        st.success("Documentation checklist saved.")

    score, alerts = integrity_score(st.session_state.evidence_df)
    c1,c2 = st.columns([1,3])
    c1.metric("Documentation completeness", f"{score}%")
    c2.progress(score / 100)
    if alerts:
        with st.expander(f"Outstanding documentation items ({len(alerts)})"):
            for item in alerts:
                st.write("•", item)
    else:
        st.success("All tracked evidence-documentation fields are complete.")

# ------------------------------------------------------------------
# STEP 5B — MAP COORDINATES AND GENERATION
# ------------------------------------------------------------------
st.markdown("### Crime Scene Map Coordinates")

if not st.session_state.analysis_complete:
    st.info("Case Analysis must be complete before mapping.")
elif st.session_state.evidence_df is None or st.session_state.evidence_df.empty:
    st.info("No mapped evidence rows are available. Scene-map generation is not required for this draft.")
else:
    st.caption(
        "Enter X and Y values from 0–100 for every automatically listed evidence item. "
        "X runs West→East and Y runs South→North. North remains fixed at the top."
    )

    map_df = sync_map_items_with_evidence(
        st.session_state.map_items,
        st.session_state.evidence_df,
    )

    with st.form("map_coordinates_form"):
        edited_map = st.data_editor(
            map_df,
            hide_index=True,
            use_container_width=True,
            disabled=["Evidence ID","Evidence Item","Category"],
            column_config={
                "X": st.column_config.NumberColumn("X", min_value=0.0, max_value=100.0, step=1.0),
                "Y": st.column_config.NumberColumn("Y", min_value=0.0, max_value=100.0, step=1.0),
                "Notes": st.column_config.TextColumn("Map notes"),
            },
        )
        generate_map = st.form_submit_button(
            "🗺️ Save Coordinates & Generate Crime Scene Map",
            type="primary",
            use_container_width=True,
        )

    if generate_map:
        work = edited_map.copy()
        coordinate_errors = []
        for _, row in work.iterrows():
            try:
                x = float(row["X"])
                y = float(row["Y"])
                if not (0 <= x <= 100 and 0 <= y <= 100):
                    raise ValueError
            except Exception:
                coordinate_errors.append(str(row.get("Evidence ID","Evidence")))

        if coordinate_errors:
            st.error(
                "Enter valid X/Y coordinates (0–100) for: "
                + ", ".join(coordinate_errors)
            )
        else:
            st.session_state.map_items = work
            map_items = []
            for _, row in work.iterrows():
                map_items.append({
                    "Type": "Evidence",
                    "Label": f"{row['Evidence ID']} · {row['Evidence Item']}",
                    "X": float(row["X"]),
                    "Y": float(row["Y"]),
                })

            st.session_state.scene_map_png = generate_scene_map(
                st.session_state.case_id,
                st.session_state.location,
                map_items,
            )
            st.session_state.map_coordinates_saved = True
            st.session_state.report_docx = None
            st.success("Crime scene map generated.")

    if st.session_state.scene_map_png:
        st.image(st.session_state.scene_map_png, caption="Schematic Scene of Crime Map")
        st.download_button(
            "Download Scene Map PNG",
            data=st.session_state.scene_map_png,
            file_name=f"{st.session_state.case_id}_scene_map.png",
            mime="image/png",
        )

# ------------------------------------------------------------------
# FINAL READINESS + ONE-TIME DRAFT GENERATION
# ------------------------------------------------------------------
st.divider()
st.markdown("## Step 6 • Generate Final Draft Report")

score, alerts = integrity_score(st.session_state.evidence_df)
has_evidence = st.session_state.evidence_df is not None and not st.session_state.evidence_df.empty
map_ready = bool(st.session_state.scene_map_png) if has_evidence else True

final_requirements = {
    "Case analysis complete": bool(st.session_state.analysis_complete),
    "Documentation checklist saved": bool(st.session_state.evidence_checklist_saved),
    "Crime scene map ready": map_ready,
}
fcols = st.columns(3)
for col, (label, ok) in zip(fcols, final_requirements.items()):
    col.metric(label, "Complete" if ok else "Pending")

st.metric("Overall evidence-documentation completeness", f"{score}%")
st.progress(score / 100 if score >= 0 else 0)

investigator_notes = st.text_area(
    "Final investigator notes for the draft",
    value=st.session_state.investigator_notes,
    height=120,
)
st.session_state.investigator_notes = investigator_notes

ready_for_report = all(final_requirements.values())

if ready_for_report and st.session_state.report_docx is None:
    st.markdown(
        '<div class="ready-box"><b>Ready to generate the draft.</b><br>'
        'This is the only report-generation action. It uses the saved case prompt, verified visual evidence, '
        'evidence checklist, search plan, coordinates/map and retrieved sources.</div>',
        unsafe_allow_html=True,
    )

if st.button(
    "📄 Generate Final Draft Report",
    type="primary",
    use_container_width=True,
    disabled=(not ready_for_report) or (st.session_state.report_docx is not None),
):
    try:
        with st.spinner("Building the complete Word draft..."):
            score, alerts = integrity_score(st.session_state.evidence_df)
            st.session_state.report_docx = build_rich_report(
                case=case_snapshot(),
                analysis=st.session_state.scene_analysis,
                guidance=st.session_state.guidance,
                sources=st.session_state.sources,
                evidence_df=st.session_state.evidence_df,
                integrity_score=score,
                integrity_alerts=alerts,
                vision_records=st.session_state.vision_records,
                verified_visuals=st.session_state.verified_visuals,
                search_plan=st.session_state.search_plan,
                investigator_notes=st.session_state.investigator_notes,
                scene_map_png=st.session_state.scene_map_png,
                map_items=st.session_state.map_items,
            )
        st.success("Draft report generated. Review and download it below.")
    except Exception as exc:
        st.error(f"Could not build the draft report: {exc}")

if st.session_state.report_docx:
    st.markdown(
        '<div class="complete-box"><b>Case draft is ready.</b><br>'
        'Download the Word file below. The original scene photograph and generated scene map are embedded automatically.</div>',
        unsafe_allow_html=True,
    )
    st.download_button(
        "⬇️ Download MORBIT Case Draft (.docx)",
        data=st.session_state.report_docx,
        file_name=f"{st.session_state.case_id}_MORBIT_CSI_Draft.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        type="primary",
        use_container_width=True,
    )
