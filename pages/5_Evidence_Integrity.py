import streamlit as st

from core import init_state, integrity_score, normalize_evidence_checklist
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Evidence Integrity | MORBIT CSI CaseAssistant",page_icon="🔐",layout="wide")
apply_ui(); init_state(); case_sidebar(active_step=5)

hero(
    "Evidence Integrity",
    "Tick completed documentation actions, save the checklist, and review the updated completeness score."
)
render_workflow(active_step=5)

if st.session_state.evidence_df is None or st.session_state.evidence_df.empty:
    st.info("No evidence inventory is available yet. Run Agentic Analysis first.")
    if st.button("🧠 GO TO AGENTIC ANALYSIS", type="primary", use_container_width=True):
        st.switch_page("pages/3_Agentic_Analysis.py")
else:
    base = normalize_evidence_checklist(st.session_state.evidence_df)

    st.markdown(
        """<div class="input-banner">
        <b>How to use this table:</b> tick the actions that have actually been completed for each evidence item,
        then press <b>Save Evidence Checklist</b>. The checkboxes are saved together so they do not disappear on rerun.
        </div>""",
        unsafe_allow_html=True,
    )

    checkbox_cols = {
        "Photographed": st.column_config.CheckboxColumn("Photographed", default=False),
        "Collector Recorded": st.column_config.CheckboxColumn("Collector Recorded", default=False),
        "Packaging Recorded": st.column_config.CheckboxColumn("Packaging Recorded", default=False),
        "Seal Recorded": st.column_config.CheckboxColumn("Seal Recorded", default=False),
        "Custody Started": st.column_config.CheckboxColumn("Custody Started", default=False),
    }

    with st.form("evidence_integrity_form", clear_on_submit=False):
        edited = st.data_editor(
            base,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key="evidence_integrity_editor",
            column_config=checkbox_cols,
            disabled=["Evidence ID", "Item", "Category", "Location", "Basis"],
        )
        save = st.form_submit_button(
            "💾 Save Evidence Checklist",
            type="primary",
            use_container_width=True,
        )

    if save:
        st.session_state.evidence_df = normalize_evidence_checklist(edited)
        st.session_state.evidence_checklist_saved = True
        st.session_state.report_docx = None
        st.success("Evidence checklist saved. Workflow tracker updated.")

    # Always calculate from the last saved dataframe.
    saved = normalize_evidence_checklist(st.session_state.evidence_df)
    score,alerts = integrity_score(saved)

    c1,c2 = st.columns([1,3])
    c1.metric("Documentation Completeness",f"{score}%")
    c2.progress(score/100)

    if alerts:
        st.markdown("### Documentation gaps")
        for a in alerts:
            st.warning(a)
    else:
        st.success("All tracked documentation fields are complete.")

    st.caption(
        "This score measures completion of recorded documentation fields only. "
        "It does not determine evidential value, admissibility, authenticity or laboratory result."
    )

    st.markdown(
        """<div class="next-action"><strong>NEXT STEP → Final Word Report</strong><br>
        Generate the formatted case report after saving your evidence checklist.</div>""",
        unsafe_allow_html=True,
    )
    if st.button("➡️ CONTINUE TO FINAL REPORT", type="primary", use_container_width=True):
        st.switch_page("pages/6_Rich_Report.py")
