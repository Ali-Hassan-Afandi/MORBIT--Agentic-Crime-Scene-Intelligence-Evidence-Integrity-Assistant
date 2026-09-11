import streamlit as st
from core import (
    init_state, client_from_secrets, knowledge_fingerprint, load_rag,
    scene_agent, retrieve_guidance, evidence_dataframe, sync_map_items_with_evidence
)
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Agentic Analysis | MORBIT", page_icon="🧠", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Agentic Analysis", "Refresh and review the multimodal scene analysis after human visual verification.")
render_workflow(active_step=3)

st.write(f"**Investigator-verified visual observations:** {len(st.session_state.verified_visuals)}")

if st.button("Refresh MORBIT Analysis with Verified Visuals",type="primary",use_container_width=True):
    client=client_from_secrets()
    effective_type=st.session_state.custom_scene_type if st.session_state.scene_type=="Other / Custom" and st.session_state.custom_scene_type else st.session_state.scene_type
    with st.spinner("Refreshing scene analysis..."):
        analysis=scene_agent(client,st.session_state.desc,effective_type,st.session_state.vision_records,st.session_state.verified_visuals)
    with st.spinner("Refreshing source-grounded guidance..."):
        fp=knowledge_fingerprint("knowledge",st.session_state.agency)
        rag=load_rag(st.session_state.agency,fp)
        guidance,sources=retrieve_guidance(
            client,rag,st.session_state.agency,st.session_state.desc,analysis,
            st.session_state.vision_records,st.session_state.verified_visuals,
            st.session_state.investigator_question
        )
    st.session_state.scene_analysis=analysis
    st.session_state.guidance=guidance
    st.session_state.sources=sources
    st.session_state.evidence_df=evidence_dataframe(analysis)
    st.session_state.map_items=sync_map_items_with_evidence(st.session_state.map_items, st.session_state.evidence_df)
    st.session_state.scene_map_png=None
    st.success("Analysis refreshed. The site-plan table has also been synchronized with the latest evidence list.")

if st.session_state.scene_analysis:
    a=st.session_state.scene_analysis
    st.markdown("### Scene Summary"); st.write(a.get("scene_summary",""))
    if a.get("visual_context_summary"):
        st.markdown("**Visual context summary**"); st.write(a["visual_context_summary"])
    c1,c2=st.columns(2)
    with c1:
        st.markdown("**Potential hazards / cautions**")
        for x in a.get("hazards",[]): st.write("•",x)
    with c2:
        st.markdown("**Documentation priorities**")
        for x in a.get("immediate_documentation_priorities",[]): st.write("•",x)

    st.markdown("### Source-Grounded Guidance")
    st.markdown(st.session_state.guidance)

    st.markdown("### Next step")
    st.page_link("pages/4_Search_and_Scene_Map.py",label="➡️ Continue to Search Strategy & Scene Map",icon="🧭")
