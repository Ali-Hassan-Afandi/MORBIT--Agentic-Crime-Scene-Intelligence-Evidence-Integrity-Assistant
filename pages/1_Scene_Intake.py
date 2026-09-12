import streamlit as st
from core import SCENE_TYPES, init_state
from ui import apply_ui, hero, case_sidebar, render_workflow

st.set_page_config(page_title="Scene Intake | MORBIT CSI CaseAssistant", page_icon="📋", layout="wide")
apply_ui(); init_state(); case_sidebar()
hero("Scene Intake", "Edit or refine the intake created from the Command Dashboard.")
render_workflow(active_step=1)

with st.form("scene_intake_edit"):
    c1,c2,c3=st.columns(3)
    case_id=c1.text_input("Case ID",st.session_state.case_id)
    scene_type=c2.selectbox("Crime scene type",SCENE_TYPES,index=SCENE_TYPES.index(st.session_state.scene_type) if st.session_state.scene_type in SCENE_TYPES else 0)
    scene_dt=c3.text_input("Date / Time",st.session_state.scene_dt)
    custom=""
    if scene_type=="Other / Custom":
        custom=st.text_input("Custom scene type",st.session_state.custom_scene_type)
    location=st.text_input("Location",st.session_state.location)
    desc=st.text_area("Investigator scene description",st.session_state.desc,height=180)
    save=st.form_submit_button("Save Intake Changes",type="primary",use_container_width=True)

if save:
    st.session_state.case_id=case_id.strip()
    st.session_state.scene_type=scene_type
    st.session_state.custom_scene_type=custom.strip()
    st.session_state.scene_dt=scene_dt.strip()
    st.session_state.location=location.strip()
    st.session_state.desc=desc.strip()
    st.success("Scene intake updated.")
    st.page_link("app.py",label="⬅ Return to Command Dashboard",icon="🏠")
