import streamlit as st
from core import init_state
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Visual Intelligence | MORBIT", page_icon="📷", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Visual Intelligence", "Review image-analysis outputs and verify only observations you are prepared to adopt as investigator-confirmed scene context.")
render_workflow(active_step=2)

if not st.session_state.vision_records:
    st.info("No images were analyzed on the Command Dashboard. You may return to the dashboard and upload images, or continue without images.")
    st.page_link("app.py",label="⬅ Return to Command Dashboard",icon="🏠")
else:
    verified=[]
    for rec in st.session_state.vision_records:
        m=rec["metadata"]; a=rec["analysis"]
        st.markdown(f"### {rec['image_id']} — {m['filename']}")
        c1,c2=st.columns([1,1.2])
        with c1:
            st.image(rec.get("image_bytes"),use_container_width=True)
        with c2:
            st.write(a.get("image_summary",""))
            st.caption(f"{m.get('width')} × {m.get('height')} | {m.get('bytes',0):,} bytes")
            st.caption("SHA-256: "+m.get("sha256",""))
            for s in a.get("documentation_suggestions",[]): st.write("•",s)

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
    st.page_link("pages/3_Agentic_Analysis.py",label="➡️ Continue to Agentic Analysis",icon="🧠")
