import streamlit as st
from core import init_state, integrity_score
from ui import apply_ui, hero, case_sidebar

st.set_page_config(page_title="Evidence Integrity | MORBIT", page_icon="🔐", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Evidence Integrity", "Review potential evidence records and track documentation-completeness fields without turning AI suggestions into scientific conclusions.")

if st.session_state.evidence_df is None or st.session_state.evidence_df.empty:
    st.info("No evidence inventory yet. Run the Agentic Analysis page first.")
else:
    edited = st.data_editor(
        st.session_state.evidence_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="evidence_integrity_editor",
    )
    st.session_state.evidence_df = edited
    score, alerts = integrity_score(edited)

    c1,c2 = st.columns([1,3])
    c1.metric("Documentation Completeness", f"{score}%")
    c2.progress(score / 100)
    if alerts:
        st.markdown("### Documentation gaps")
        for alert in alerts:
            st.warning(alert)
    else:
        st.success("All tracked documentation fields are complete.")

    st.caption(
        "This score reflects completion of the recorded documentation fields only. "
        "It does not assess evidential value, admissibility, authenticity, laboratory result or guilt."
    )
