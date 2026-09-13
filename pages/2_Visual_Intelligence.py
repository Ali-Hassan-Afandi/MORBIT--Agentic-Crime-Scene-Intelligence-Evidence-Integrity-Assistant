import streamlit as st
from core import init_state
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Visual Intelligence | MORBIT CSI CaseAssistant", page_icon="📷", layout="wide")
apply_ui(); init_state(); case_sidebar(active_step=2)
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
        if a.get("scene_zones_reviewed"):
            st.caption("Systematic sweep: " + " • ".join(a["scene_zones_reviewed"]))
        if a.get("coverage_note"):
            st.info("Coverage note: " + a["coverage_note"])

        observations = a.get("potential_observations", [])
        st.markdown(f"### Human Verification — {len(observations)} AI-Proposed Candidate(s)")
        st.caption("Tick only the visible observations you are prepared to adopt as investigator-verified context.")

        for j,obs in enumerate(observations):
            key=f"verify_{rec['image_id']}_{j}"
            with st.container(border=True):
                st.markdown(f"**{j+1}. {obs.get('observation','')}**")
                m1,m2,m3=st.columns(3)
                m1.caption("Location: " + (obs.get("location_in_image","") or "Not specified"))
                m2.caption("Category: " + obs.get("possible_category","other"))
                m3.caption("AI confidence: " + obs.get("confidence","unspecified"))
                if obs.get("reason"):
                    st.caption("Why it may warrant documentation: " + obs.get("reason",""))
                checked=st.checkbox("Investigator verifies this visible observation", key=key)
                if checked:
                    location = obs.get("location_in_image","")
                    verified.append(
                        f"{rec['image_id']}: {obs.get('observation','')}"
                        + (f" [visible location: {location}]" if location else "")
                    )

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
