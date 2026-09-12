import streamlit as st
from core import init_state
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Visual Intelligence | MORBIT CSI CaseAssistant", page_icon="📷", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Visual Intelligence", "Review image-analysis outputs and verify only observations you are prepared to adopt as investigator-confirmed scene context.")
render_workflow(active_step=2)

if not st.session_state.vision_records:
    st.info("No scene photograph is saved yet. Return to the Command Dashboard and add the single scene photograph.")
    st.page_link("app.py",label="⬅ Return to Command Dashboard",icon="🏠")
else:
    verified=[]
    for rec in st.session_state.vision_records:
        m=rec.get("metadata",{}); a=rec.get("analysis",{})
        st.markdown(f"### {rec['image_id']} — {m['filename']}")
        c1,c2=st.columns([1,1.2])
        with c1:
            st.image(rec.get("image_bytes"),use_container_width=True)
        with c2:
            st.write(a.get("image_summary",""))
            st.caption(f"{m.get('width')} × {m.get('height')} | {m.get('bytes',0):,} bytes")
            st.caption("SHA-256: "+m.get("sha256",""))
            for s in a.get("documentation_suggestions",[]): st.write("•",s)

        if not a.get("image_summary"):
            st.warning("The photograph is saved, but visual AI analysis is not yet available. Return to the dashboard to retry analysis; re-upload is not required.")
        st.markdown("**Human verification**")
        for j,obs in enumerate(a.get("potential_observations",[])):
            key=f"verify_{rec['image_id']}_{j}"
            checked=st.checkbox(
                f"{obs.get('observation','')} — {obs.get('confidence','unspecified')} confidence",
                key=key,
            )
            if checked:
                verified.append(f"{rec['image_id']}: {obs.get('observation','')}")
        if a.get("limitations"):
            st.caption("Limitations: "+"; ".join(a["limitations"]))
        st.divider()

    st.session_state.verified_visuals=verified
    st.success(f"{len(verified)} visual observation(s) marked as investigator-verified.")

    st.markdown("### Next step")
    st.info("Because verification may change the usable visual context, continue to Agentic Analysis to refresh the scene analysis and source-grounded guidance.")
    st.markdown(
        """<div class="next-action"><strong>NEXT STEP → Refresh Agentic Analysis</strong><br>
        Verified visual observations will be included in the refreshed analysis.</div>""",
        unsafe_allow_html=True,
    )
    if st.button("➡️ CONTINUE TO AGENTIC ANALYSIS", type="primary", use_container_width=True):
        st.switch_page("pages/3_Agentic_Analysis.py")
