import streamlit as st
from core import init_state, integrity_score, case_snapshot
from report_builder import build_rich_report
from ui import apply_ui, hero, case_sidebar

st.set_page_config(page_title="Rich Report | MORBIT", page_icon="📄", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Rich Word Report", "Generate a visually formatted DOCX containing case details, uploaded scene images, image analysis, evidence integrity, search strategy, scene map and source-grounded guidance.")

notes = st.text_area(
    "Investigator notes",
    value=st.session_state.investigator_notes,
    height=150,
    placeholder="Add factual investigator notes that should appear in the report.",
)
st.session_state.investigator_notes = notes

score, alerts = integrity_score(st.session_state.evidence_df)

st.markdown("### Report contents")
checks = [
    ("Case intake", bool(st.session_state.case_id)),
    ("Uploaded images embedded", bool(st.session_state.vision_records)),
    ("Image-analysis record", bool(st.session_state.vision_records)),
    ("Investigator-verified visual observations", bool(st.session_state.verified_visuals)),
    ("Scene analysis", bool(st.session_state.scene_analysis)),
    ("Evidence inventory", st.session_state.evidence_df is not None and not st.session_state.evidence_df.empty),
    ("Search-method recommendation", bool(st.session_state.search_plan)),
    ("North-up scene map", bool(st.session_state.scene_map_png)),
    ("Source-grounded guidance", bool(st.session_state.guidance)),
    ("Retrieved source references", bool(st.session_state.sources)),
]
for label, ready in checks:
    st.write(("✅" if ready else "▫️") + " " + label)

if st.button("Generate Rich Word Report (.docx)", type="primary", use_container_width=True):
    with st.spinner("Building formatted Word report with embedded images..."):
        docx_bytes = build_rich_report(
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
        )
    st.session_state.report_docx = docx_bytes
    st.success("Rich Word report generated.")

if st.session_state.report_docx:
    st.download_button(
        "Download MORBIT Rich Word Report",
        st.session_state.report_docx,
        file_name=f"{st.session_state.case_id}_MORBIT_Crime_Scene_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
        type="primary",
    )
    st.caption("The downloadable file is a formatted Word document, not Markdown or plain text.")
