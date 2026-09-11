import streamlit as st
from core import init_state, integrity_score
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Evidence Integrity | MORBIT",page_icon="🔐",layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Evidence Integrity","Review potential evidence and complete the tracked documentation fields.")
render_workflow(active_step=5)

if st.session_state.evidence_df is None or st.session_state.evidence_df.empty:
    st.info("No evidence inventory is available yet. Run Agentic Analysis first.")
    st.page_link("pages/3_Agentic_Analysis.py",label="Go to Agentic Analysis",icon="🧠")
else:
    edited=st.data_editor(
        st.session_state.evidence_df,use_container_width=True,hide_index=True,num_rows="dynamic",key="evidence_editor"
    )
    st.session_state.evidence_df=edited
    score,alerts=integrity_score(edited)
    c1,c2=st.columns([1,3]); c1.metric("Documentation Completeness",f"{score}%"); c2.progress(score/100)

    if alerts:
        st.markdown("### Documentation gaps")
        for a in alerts: st.warning(a)
    else:
        st.success("All tracked documentation fields are complete.")

    st.caption("This score measures completion of recorded fields only, not evidential value, admissibility, authenticity or laboratory result.")
    st.markdown("### Next step")
    st.page_link("pages/6_Rich_Report.py",label="➡️ Continue to Final Rich Word Report",icon="📄")
