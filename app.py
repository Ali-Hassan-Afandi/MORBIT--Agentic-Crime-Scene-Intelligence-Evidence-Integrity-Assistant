import streamlit as st
from core import APP_NAME, APP_VERSION, EMBED_MODEL, TEXT_MODEL, VISION_MODEL, init_state, knowledge_inventory, reset_case_state
from ui import apply_ui, hero

st.set_page_config(page_title=APP_NAME, page_icon="🛡️", layout="wide", initial_sidebar_state="expanded")
apply_ui()
init_state()

hero(
    "Case Dashboard",
    "A multi-page workspace for scene intake, multimodal review, agentic analysis, search planning, mapping, evidence integrity and rich reporting."
)

st.warning(
    "Use fictional, training or properly authorized case data only. "
    "AI observations are not laboratory findings and require investigator verification."
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Images analyzed", len(st.session_state.vision_records))
c2.metric("Verified visual observations", len(st.session_state.verified_visuals))
c3.metric("Evidence rows", len(st.session_state.evidence_df) if hasattr(st.session_state.evidence_df, "__len__") else 0)
c4.metric("Report status", "Ready" if st.session_state.report_docx else "Not generated")

st.markdown("### Workflow")
st.write(
    "Use the page navigation in the sidebar in this order: "
    "**Scene Intake → Visual Intelligence → Agentic Analysis → Search & Scene Map → "
    "Evidence Integrity → Rich Report**."
)

inventory = knowledge_inventory("knowledge")
with st.expander("System & knowledge status"):
    a,b,c = st.columns(3)
    a.metric("NFA local documents", len(inventory["NFA"]))
    b.metric("PFSA local documents", len(inventory["PFSA"]))
    c.metric("App version", APP_VERSION)
    st.caption(f"Text model: {TEXT_MODEL} | Vision model: {VISION_MODEL} | Embeddings: {EMBED_MODEL}")

with st.sidebar:
    st.markdown("### MORBIT")
    st.caption("Agentic Crime Scene Intelligence & Evidence Integrity Assistant")
    if st.button("Reset current case", use_container_width=True):
        reset_case_state()
        st.rerun()
