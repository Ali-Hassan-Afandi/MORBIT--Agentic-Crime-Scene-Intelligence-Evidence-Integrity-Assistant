import streamlit as st
from core import APP_NAME, APP_VERSION, init_state

def apply_ui():
    init_state()
    st.markdown("""
    <style>
    .block-container{max-width:1350px;padding-top:1.4rem;padding-bottom:3rem}
    [data-testid="stSidebar"]{border-right:1px solid rgba(120,145,170,.22)}
    .morbit-hero{
      background:linear-gradient(135deg,#0D2238 0%,#173B5F 58%,#275C7F 100%);
      border-radius:22px;padding:28px 32px;margin-bottom:22px;color:white;
      box-shadow:0 14px 35px rgba(0,0,0,.18)}
    .morbit-kicker{font-size:11px;letter-spacing:.16em;font-weight:800;color:#8FD8FF}
    .morbit-title{font-size:31px;font-weight:850;line-height:1.1;margin-top:7px}
    .morbit-sub{font-size:14px;color:#D9EAF6;margin-top:7px}
    .info-card{border:1px solid rgba(122,146,170,.25);border-radius:16px;padding:16px}
    .section-note{padding:12px 14px;border-left:4px solid #2E7DB2;background:rgba(46,125,178,.08);border-radius:8px}
    </style>
    """, unsafe_allow_html=True)

def hero(page_name: str, subtitle: str):
    st.markdown(f"""
    <div class="morbit-hero">
      <div class="morbit-kicker">{APP_VERSION.upper()} • HUMAN-SUPERVISED FORENSIC INTELLIGENCE</div>
      <div class="morbit-title">{APP_NAME}</div>
      <div class="morbit-sub"><b>{page_name}</b> — {subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def case_sidebar():
    with st.sidebar:
        st.markdown("### Current Case")
        st.caption(st.session_state.case_id)
        st.write("**Scene:**", st.session_state.scene_type)
        st.write("**Location:**", st.session_state.location or "Not recorded")
        st.write("**Authority:**", st.session_state.agency)
        if st.session_state.scene_analysis:
            st.success("Scene analysis available")
        if len(st.session_state.vision_records):
            st.info(f"{len(st.session_state.vision_records)} image(s) analyzed")
        if st.session_state.scene_map_png:
            st.info("Scene map available")
        if st.session_state.report_docx:
            st.success("Rich Word report ready")
