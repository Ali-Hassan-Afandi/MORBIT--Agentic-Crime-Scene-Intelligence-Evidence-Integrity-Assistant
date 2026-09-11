import streamlit as st
from core import init_state, integrity_score, case_snapshot
from report_builder import build_rich_report
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Rich Report | MORBIT",page_icon="📄",layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Final Rich Word Report","Generate a visually formatted DOCX containing the complete case workflow.")
render_workflow(active_step=6)

notes=st.text_area("Investigator notes",value=st.session_state.investigator_notes,height=150)
st.session_state.investigator_notes=notes
score,alerts=integrity_score(st.session_state.evidence_df)

st.markdown("### Final readiness")
checks=[
    ("Scene intake",bool(st.session_state.case_id and st.session_state.desc)),
    ("Image record",bool(st.session_state.vision_records)),
    ("Scene analysis",bool(st.session_state.scene_analysis)),
    ("Search recommendation",bool(st.session_state.search_plan)),
    ("Scene map",bool(st.session_state.scene_map_png)),
    ("Evidence inventory",st.session_state.evidence_df is not None and not st.session_state.evidence_df.empty),
    ("Source-grounded guidance",bool(st.session_state.guidance)),
]
for label,ready in checks:
    st.write(("✅" if ready else "▫️")+" "+label)

if st.button("Generate Final MORBIT Word Report (.docx)",type="primary",use_container_width=True):
    with st.spinner("Building rich Word report with embedded images and scene map..."):
        st.session_state.report_docx=build_rich_report(
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
    st.success("Final report generated.")

if st.session_state.report_docx:
    st.download_button(
        "⬇️ Download Final MORBIT Word Report",
        st.session_state.report_docx,
        file_name=f"{st.session_state.case_id}_MORBIT_Crime_Scene_Report.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
        type="primary",
    )
    st.success("Workflow complete.")
    st.page_link("app.py",label="🏠 Return to Command Dashboard",icon="🏠")
