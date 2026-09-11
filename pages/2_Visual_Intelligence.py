import streamlit as st
from core import init_state, client_from_secrets
from ui import apply_ui, hero, case_sidebar
from vision_agent import analyze_image, image_metadata

st.set_page_config(page_title="Visual Intelligence | MORBIT", page_icon="📷", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Visual Intelligence", "Analyze scene photographs, preserve the original image bytes, and promote only investigator-verified observations.")

st.info(
    "Uploaded images are now retained in session state for downstream agents and for embedding "
    "inside the rich Word report. AI-proposed observations remain distinct from investigator verification."
)

uploads = st.file_uploader(
    "Upload up to 8 JPG/JPEG/PNG scene images",
    type=["jpg","jpeg","png"],
    accept_multiple_files=True,
)
if uploads and len(uploads) > 8:
    st.warning("Only the first 8 images will be used.")
    uploads = uploads[:8]

if uploads and st.button("Analyze Uploaded Images", type="primary", use_container_width=True):
    client = client_from_secrets()
    records = []
    for idx, up in enumerate(uploads, start=1):
        data = up.getvalue()
        with st.spinner(f"Analyzing {up.name} ({idx}/{len(uploads)})..."):
            meta = image_metadata(data, up.name)
            visual = analyze_image(client, data, up.name, st.session_state.desc)
        records.append({
            "image_id": f"IMG-{idx:03d}",
            "metadata": meta,
            "analysis": visual,
            "image_bytes": data,
        })
    st.session_state.vision_records = records
    # Verification choices belong to the specific image set; reset them after re-analysis.
    st.session_state.verified_visuals = []
    st.success("Images analyzed and preserved for downstream agents/reporting.")

verified = []
for rec in st.session_state.vision_records:
    meta = rec["metadata"]
    st.markdown(f"### {rec['image_id']} — {meta['filename']}")
    c1,c2 = st.columns([1,1.25])
    with c1:
        st.image(rec.get("image_bytes"), use_container_width=True)
    with c2:
        st.write(rec["analysis"].get("image_summary",""))
        m1,m2,m3 = st.columns(3)
        m1.metric("Width", meta.get("width"))
        m2.metric("Height", meta.get("height"))
        m3.metric("Bytes", f"{meta.get('bytes',0):,}")
        st.caption("SHA-256: " + meta.get("sha256",""))
        if rec["analysis"].get("documentation_suggestions"):
            st.markdown("**Documentation suggestions**")
            for x in rec["analysis"]["documentation_suggestions"]:
                st.write("•", x)

    st.markdown("**Human verification of AI-proposed observations**")
    for j, obs in enumerate(rec["analysis"].get("potential_observations", [])):
        key = f"verify_{rec['image_id']}_{j}"
        accepted = st.checkbox(
            f"{obs.get('observation','')} — confidence: {obs.get('confidence','unspecified')} "
            f"— category: {obs.get('possible_category','other')}",
            key=key,
        )
        if accepted:
            verified.append(f"{rec['image_id']}: {obs.get('observation','')}")
    if rec["analysis"].get("limitations"):
        st.caption("Limitations: " + "; ".join(rec["analysis"]["limitations"]))
    st.divider()

st.session_state.verified_visuals = verified

if st.session_state.vision_records:
    st.success(
        f"{len(st.session_state.vision_records)} image(s) are available to the Scene Analysis Agent, "
        "RAG retrieval query, and Rich Report. "
        f"{len(st.session_state.verified_visuals)} observation(s) are currently investigator-verified."
    )
