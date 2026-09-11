import pandas as pd
import streamlit as st
from core import init_state, recommend_search_method, SEARCH_METHODS
from scene_map import generate_scene_map
from ui import apply_ui, hero, case_sidebar

st.set_page_config(page_title="Search & Scene Map | MORBIT", page_icon="🧭", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Search Strategy & Scene of Crime Map", "Recommend a search pattern from scene characteristics and create a north-up schematic map from investigator-entered coordinates.")

st.markdown("### Search Method Recommendation")
c1,c2,c3,c4 = st.columns(4)
environment = c1.selectbox(
    "Environment", ["Indoor","Building / Multi-room","Outdoor","Open Terrain","Vehicle / Roadway","Underwater"],
    index=["Indoor","Building / Multi-room","Outdoor","Open Terrain","Vehicle / Roadway","Underwater"].index(st.session_state.scene_environment)
    if st.session_state.scene_environment in ["Indoor","Building / Multi-room","Outdoor","Open Terrain","Vehicle / Roadway","Underwater"] else 0
)
size = c2.selectbox("Scene size", ["Small","Medium","Large","Very Large"], index=["Small","Medium","Large","Very Large"].index(st.session_state.scene_size))
personnel = c3.number_input("Search personnel", min_value=1, max_value=50, value=int(st.session_state.personnel_count))
obstacles = c4.selectbox("Obstacle level", ["Low","Moderate","High"], index=["Low","Moderate","High"].index(st.session_state.obstacle_level))

if st.button("Recommend Search Method", type="primary", use_container_width=True):
    st.session_state.scene_environment = environment
    st.session_state.scene_size = size
    st.session_state.personnel_count = int(personnel)
    st.session_state.obstacle_level = obstacles
    st.session_state.search_plan = recommend_search_method(
        st.session_state.scene_type, environment, size, int(personnel), obstacles
    )

if st.session_state.search_plan:
    p = st.session_state.search_plan
    a,b = st.columns(2)
    a.success(f"Recommended: {p['recommended']}")
    b.info(f"Alternative: {p['alternative']}")
    st.write(p["rationale"])
    st.caption(p["caution"])
    with st.expander("Method details"):
        st.write("**Recommended:**", p["details"]["description"])
        st.write("Best for:", p["details"]["best_for"])
        st.write("Strength:", p["details"]["strength"])
        st.divider()
        st.write("**Alternative:**", p["alternative_details"]["description"])

st.markdown("### Search Method Reference")
with st.expander("Compare all supported search methods"):
    for name, info in SEARCH_METHODS.items():
        st.markdown(f"**{name}** — {info['description']}")
        st.caption("Best for: " + info["best_for"])
        st.write(info["strength"])

st.divider()
st.markdown("### Scene of Crime Map")
st.info(
    "Enter measured or investigator-estimated coordinates on a 0–100 scene grid. "
    "X runs west→east; Y runs south→north. The generated map always keeps **North at the top**."
)

if st.session_state.map_items.empty:
    starter = pd.DataFrame([
        {"Label":"Reference A","Type":"Reference Point","X":10,"Y":10,"Notes":"Fixed reference point"},
        {"Label":"E-001","Type":"Evidence","X":50,"Y":55,"Notes":"Example only — edit or delete"},
    ])
else:
    starter = st.session_state.map_items

edited = st.data_editor(
    starter,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "Type": st.column_config.SelectboxColumn(
            "Type",
            options=["Evidence","Entry/Exit","Body/Remains","Vehicle","Furniture/Object","Hazard","Reference Point","Other"],
        ),
        "X": st.column_config.NumberColumn("X (0–100)", min_value=0, max_value=100, step=1),
        "Y": st.column_config.NumberColumn("Y (0–100)", min_value=0, max_value=100, step=1),
    },
    key="scene_map_editor",
)

if st.button("Generate North-Up Scene Map", type="primary", use_container_width=True):
    st.session_state.map_items = edited
    st.session_state.scene_map_png = generate_scene_map(
        st.session_state.case_id,
        st.session_state.location,
        edited.to_dict(orient="records"),
    )
    st.success("Scene map generated.")

if st.session_state.scene_map_png:
    st.image(st.session_state.scene_map_png, caption="North-up schematic scene map", use_container_width=True)
    st.download_button(
        "Download Scene Map PNG",
        st.session_state.scene_map_png,
        file_name=f"{st.session_state.case_id}_scene_map.png",
        mime="image/png",
        use_container_width=True,
    )
