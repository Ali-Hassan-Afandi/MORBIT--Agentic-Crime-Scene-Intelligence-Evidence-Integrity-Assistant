import pandas as pd
import streamlit as st
from core import init_state, recommend_search_method, SEARCH_METHODS
from scene_map import generate_scene_map
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Search & Scene Map | MORBIT",page_icon="🧭",layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Search Strategy & Scene of Crime Map","Confirm a suitable search pattern and create a north-up schematic map.")
render_workflow(active_step=4)

st.markdown("### Recommended Search Method")
if st.session_state.search_plan is None:
    st.session_state.search_plan=recommend_search_method(
        st.session_state.scene_type,st.session_state.scene_environment,
        st.session_state.scene_size,st.session_state.personnel_count,
        st.session_state.obstacle_level
    )
p=st.session_state.search_plan
c1,c2=st.columns(2)
c1.success(f"Recommended: {p['recommended']}")
c2.info(f"Alternative: {p['alternative']}")
st.write(p["rationale"])
st.caption(p["caution"])

with st.expander("Compare all supported search methods"):
    for name,info in SEARCH_METHODS.items():
        st.markdown(f"**{name}** — {info['description']}")
        st.caption("Best for: "+info["best_for"])

st.divider()
st.markdown("### Build Scene of Crime Map")
st.info("Use a 0–100 grid. X runs west→east and Y runs south→north. North is always at the top.")

if st.session_state.map_items.empty:
    starter=pd.DataFrame([
        {"Label":"Reference A","Type":"Reference Point","X":10,"Y":10,"Notes":"Fixed point"},
        {"Label":"E-001","Type":"Evidence","X":50,"Y":55,"Notes":"Edit or delete example"},
    ])
else:
    starter=st.session_state.map_items

edited=st.data_editor(
    starter,num_rows="dynamic",use_container_width=True,key="scene_map_editor",
    column_config={
        "Type":st.column_config.SelectboxColumn("Type",options=["Evidence","Entry/Exit","Body/Remains","Vehicle","Furniture/Object","Hazard","Reference Point","Other"]),
        "X":st.column_config.NumberColumn("X (0–100)",min_value=0,max_value=100,step=1),
        "Y":st.column_config.NumberColumn("Y (0–100)",min_value=0,max_value=100,step=1),
    }
)

if st.button("Generate North-Up Scene Map",type="primary",use_container_width=True):
    st.session_state.map_items=edited
    st.session_state.scene_map_png=generate_scene_map(
        st.session_state.case_id,st.session_state.location,edited.to_dict(orient="records")
    )
    st.success("Scene map generated.")

if st.session_state.scene_map_png:
    st.image(st.session_state.scene_map_png,use_container_width=True,caption="North-up schematic scene map")
    st.download_button("Download Scene Map PNG",st.session_state.scene_map_png,
        file_name=f"{st.session_state.case_id}_scene_map.png",mime="image/png",use_container_width=True)
    st.markdown("### Next step")
    st.page_link("pages/5_Evidence_Integrity.py",label="➡️ Continue to Evidence Integrity",icon="🔐")
