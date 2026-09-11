import streamlit as st
from core import SCENE_TYPE_GROUPS, init_state
from ui import apply_ui, hero, case_sidebar

st.set_page_config(page_title="Scene Intake | MORBIT", page_icon="📋", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Scene Intake", "Create the case record and select from a broad practical crime-scene taxonomy.")

with st.form("scene_intake"):
    c1,c2,c3 = st.columns(3)
    case_id = c1.text_input("Case ID", st.session_state.case_id)
    flat = [x for group in SCENE_TYPE_GROUPS.values() for x in group]
    idx = flat.index(st.session_state.scene_type) if st.session_state.scene_type in flat else 0
    scene_type = c2.selectbox("Crime scene type", flat, index=idx)
    scene_dt = c3.text_input("Date / Time", st.session_state.scene_dt)

    location = st.text_input("Location", st.session_state.location, placeholder="Scene location / training location")
    desc = st.text_area("Investigator scene description", st.session_state.desc, height=170)

    st.markdown("#### Search-planning characteristics")
    x1,x2,x3,x4 = st.columns(4)
    environment = x1.selectbox("Environment", ["Indoor","Building / Multi-room","Outdoor","Open Terrain","Vehicle / Roadway","Underwater"], index=0)
    scene_size = x2.selectbox("Scene size", ["Small","Medium","Large","Very Large"], index=1)
    personnel = x3.number_input("Available search personnel", min_value=1, max_value=50, value=int(st.session_state.personnel_count))
    obstacles = x4.selectbox("Obstacle / complexity level", ["Low","Moderate","High"], index=1)

    save = st.form_submit_button("Save Scene Intake", type="primary", use_container_width=True)

if save:
    st.session_state.case_id = case_id.strip()
    st.session_state.scene_type = scene_type
    st.session_state.scene_dt = scene_dt.strip()
    st.session_state.location = location.strip()
    st.session_state.desc = desc.strip()
    st.session_state.scene_environment = environment
    st.session_state.scene_size = scene_size
    st.session_state.personnel_count = int(personnel)
    st.session_state.obstacle_level = obstacles
    st.success("Scene intake saved.")

st.markdown("### Crime Scene Type Coverage")
for group, items in SCENE_TYPE_GROUPS.items():
    with st.expander(f"{group} ({len(items)})"):
        st.write(" • ".join(items))
st.caption("The taxonomy is deliberately broad rather than claiming a finite list of every conceivable crime scene. Use Other / Custom where necessary.")
