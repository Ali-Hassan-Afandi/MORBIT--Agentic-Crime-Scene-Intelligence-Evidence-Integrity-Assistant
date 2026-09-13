import pandas as pd
import streamlit as st

from core import (
    init_state, recommend_search_method, SEARCH_METHODS,
    sync_map_items_with_evidence
)
from scene_map import generate_scene_map
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Search & Scene Map | MORBIT CSI CaseAssistant",page_icon="🧭",layout="wide")
apply_ui(); init_state(); case_sidebar(active_step=4)

hero(
    "Search Strategy & Scene of Crime Map",
    "MORBIT automatically enlists every potential evidence item. The investigator only enters coordinates and optional notes before generating a north-up site plan."
)
render_workflow(active_step=4)

st.markdown("### Recommended Search Method")
if st.session_state.search_plan is None:
    st.session_state.search_plan = recommend_search_method(
        st.session_state.scene_type,
        st.session_state.scene_environment,
        st.session_state.scene_size,
        st.session_state.personnel_count,
        st.session_state.obstacle_level,
    )

p = st.session_state.search_plan
c1,c2 = st.columns(2)
c1.success(f"Recommended: {p['recommended']}")
c2.info(f"Alternative: {p['alternative']}")
st.write(p["rationale"])
st.caption(p["caution"])

with st.expander("Compare supported search methods"):
    for name,info in SEARCH_METHODS.items():
        st.markdown(f"**{name}** — {info['description']}")
        st.caption("Best for: " + info["best_for"])

st.divider()
st.markdown("### Automated Evidence Site-Plan Table")

st.markdown(
    """<div class="input-banner">
    <b>Automatic evidence listing:</b> the rows below come directly from MORBIT's current potential-evidence inventory.
    Evidence ID, item and category are locked. Enter only <b>X</b>, <b>Y</b> and <b>Notes</b>.
    </div>""",
    unsafe_allow_html=True,
)

st.session_state.map_items = sync_map_items_with_evidence(
    st.session_state.map_items,
    st.session_state.evidence_df,
)

if st.session_state.map_items.empty:
    st.info("No potential evidence has been identified yet. Complete Agentic Analysis first.")
    st.page_link("pages/3_Agentic_Analysis.py", label="Go to Agentic Analysis", icon="🧠")
else:
    edited = st.data_editor(
        st.session_state.map_items,
        use_container_width=True,
        hide_index=True,
        disabled=["Evidence ID", "Evidence Item", "Category"],
        column_config={
            "Evidence ID": st.column_config.TextColumn("Evidence ID", help="Generated automatically by MORBIT"),
            "Evidence Item": st.column_config.TextColumn("Evidence Item", help="Generated automatically from scene analysis"),
            "Category": st.column_config.TextColumn("Category", help="Generated automatically from scene analysis"),
            "X": st.column_config.NumberColumn(
                "X coordinate",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                help="0 = west edge, 100 = east edge",
            ),
            "Y": st.column_config.NumberColumn(
                "Y coordinate",
                min_value=0.0,
                max_value=100.0,
                step=1.0,
                help="0 = south edge, 100 = north edge",
            ),
            "Notes": st.column_config.TextColumn(
                "Investigator Notes",
                help="Optional positional or documentation note",
            ),
        },
        key="auto_evidence_site_plan_editor",
    )
    st.session_state.map_items = edited

    missing_xy = edited[edited["X"].isna() | edited["Y"].isna()]
    if not missing_xy.empty:
        st.warning(
            f"{len(missing_xy)} evidence item(s) still need coordinates. "
            "The map can be generated after X and Y are entered for every evidence row."
        )

    st.caption(
        "Coordinate convention: X = west→east (0–100), Y = south→north (0–100). "
        "North is always displayed at the top."
    )

    can_generate = missing_xy.empty and not edited.empty
    if st.button(
        "Generate North-Up Scene Map",
        type="primary",
        use_container_width=True,
        disabled=not can_generate,
    ):
        map_records = []
        for _, row in edited.iterrows():
            map_records.append({
                "Label": f"{row.get('Evidence ID','')} · {row.get('Evidence Item','')}",
                "Type": "Evidence",
                "X": row.get("X"),
                "Y": row.get("Y"),
                "Notes": row.get("Notes",""),
            })

        st.session_state.scene_map_png = generate_scene_map(
            st.session_state.case_id,
            st.session_state.location,
            map_records,
        )
        st.success("North-up Scene of Crime map generated.")

if st.session_state.scene_map_png:
    st.image(
        st.session_state.scene_map_png,
        use_container_width=True,
        caption="North-up schematic Scene of Crime map",
    )
    st.download_button(
        "Download Scene Map PNG",
        st.session_state.scene_map_png,
        file_name=f"{st.session_state.case_id}_scene_map.png",
        mime="image/png",
        use_container_width=True,
    )

    st.markdown(
        """<div class="next-action"><strong>NEXT STEP → Evidence Integrity</strong><br>
        Complete the evidence-action checklist before generating the final report.</div>""",
        unsafe_allow_html=True,
    )
    if st.button("➡️ CONTINUE TO EVIDENCE INTEGRITY", type="primary", use_container_width=True):
        st.switch_page("pages/5_Evidence_Integrity.py")
