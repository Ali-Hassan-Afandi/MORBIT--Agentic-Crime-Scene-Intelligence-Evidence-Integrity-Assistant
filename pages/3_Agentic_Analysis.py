import streamlit as st
from core import (
    init_state, client_from_secrets, knowledge_fingerprint, load_rag,
    scene_agent, retrieve_guidance, evidence_dataframe, vision_context
)
from ui import apply_ui, hero, case_sidebar

st.set_page_config(page_title="Agentic Analysis | MORBIT", page_icon="🧠", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Agentic Analysis", "Combine investigator narrative, image analysis and source-grounded forensic knowledge without treating AI observations as scientific findings.")

with st.sidebar:
    agency_label = st.selectbox("Forensic knowledge source", ["NFA Pakistan","PFSA Punjab","NFA + PFSA"])
    st.session_state.agency = {"NFA Pakistan":"NFA","PFSA Punjab":"PFSA","NFA + PFSA":"BOTH"}[agency_label]

st.markdown("### Multimodal context passed to the agents")
if st.session_state.vision_records:
    st.write(f"Images analyzed: **{len(st.session_state.vision_records)}**")
    st.write(f"Investigator-verified image observations: **{len(st.session_state.verified_visuals)}**")
    with st.expander("Show image context"):
        st.code(vision_context(st.session_state.vision_records, st.session_state.verified_visuals), language=None)
else:
    st.info("No image analysis is available yet. The agent can still use the investigator narrative.")

question = st.text_input(
    "Optional forensic knowledge question",
    placeholder="Example: What source-grounded packaging/submission considerations are relevant here?"
)

if st.button("Run MORBIT Agents", type="primary", use_container_width=True):
    client = client_from_secrets()
    with st.spinner("Running multimodal scene analysis..."):
        analysis = scene_agent(
            client,
            st.session_state.desc,
            st.session_state.scene_type,
            st.session_state.vision_records,
            st.session_state.verified_visuals,
        )
    with st.spinner("Retrieving NFA/PFSA source-grounded guidance..."):
        fingerprint = knowledge_fingerprint("knowledge", st.session_state.agency)
        rag = load_rag(st.session_state.agency, fingerprint)
        guidance, sources = retrieve_guidance(
            client=client,
            rag=rag,
            agency=st.session_state.agency,
            desc=st.session_state.desc,
            analysis=analysis,
            vision_records=st.session_state.vision_records,
            verified_visuals=st.session_state.verified_visuals,
            user_question=question,
        )
    st.session_state.scene_analysis = analysis
    st.session_state.guidance = guidance
    st.session_state.sources = sources
    st.session_state.evidence_df = evidence_dataframe(analysis)
    st.success("MORBIT agents completed.")

if st.session_state.scene_analysis:
    a = st.session_state.scene_analysis
    st.markdown("### Scene Analysis")
    st.write(a.get("scene_summary",""))
    if a.get("visual_context_summary"):
        st.markdown("**Visual context summary**")
        st.write(a["visual_context_summary"])

    c1,c2 = st.columns(2)
    with c1:
        st.markdown("**Potential hazards / cautions**")
        for x in a.get("hazards",[]): st.write("•", x)
    with c2:
        st.markdown("**Immediate documentation priorities**")
        for x in a.get("immediate_documentation_priorities",[]): st.write("•", x)

    st.markdown("### Source-Grounded Forensic Guidance")
    st.markdown(st.session_state.guidance)

    with st.expander("Retrieved NFA/PFSA sources"):
        for i,r in enumerate(st.session_state.sources, start=1):
            st.markdown(f"**[S{i}] {r.get('title')}**")
            st.caption(
                f"Agency: {r.get('agency')} | Type: {r.get('document_type')} | "
                f"Page: {r.get('page') or 'N/A'} | Similarity: {r.get('score',0):.3f}"
            )
            st.write(r.get("text","")[:900])
            if r.get("url"): st.link_button("Open recorded source URL", r["url"])
            st.divider()
