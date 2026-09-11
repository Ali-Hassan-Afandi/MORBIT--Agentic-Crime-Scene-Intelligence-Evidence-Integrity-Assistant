import streamlit as st
from core import APP_NAME, APP_VERSION, init_state, workflow_status

def apply_ui():
    init_state()
    st.markdown("""
    <style>
    .block-container{max-width:1380px;padding-top:1.2rem;padding-bottom:3rem}
    [data-testid="stSidebar"]{border-right:1px solid rgba(120,145,170,.22)}
    .morbit-hero{
      background:linear-gradient(135deg,#091B2D 0%,#143A59 58%,#205D7C 100%);
      border-radius:24px;padding:30px 34px;margin-bottom:22px;color:white;
      box-shadow:0 16px 38px rgba(0,0,0,.18)}
    .morbit-kicker{font-size:11px;letter-spacing:.17em;font-weight:800;color:#8FD8FF}
    .morbit-title{font-size:34px;font-weight:850;line-height:1.08;margin-top:8px}
    .morbit-sub{font-size:14px;color:#D9EAF6;margin-top:8px;max-width:980px}
    .workflow-card{
      border:1px solid rgba(122,146,170,.25);border-radius:16px;padding:14px 15px;
      min-height:105px;background:rgba(80,120,160,.05)}
    .workflow-card.done{border-color:rgba(46,160,110,.45);background:rgba(46,160,110,.07)}
    .workflow-card.active{border-color:#3A84C0;background:rgba(58,132,192,.09)}
    .step-no{font-size:11px;font-weight:850;opacity:.7}
    .step-title{font-size:15px;font-weight:800;margin-top:6px}
    .step-status{font-size:11px;opacity:.75;margin-top:7px}
    .dashboard-card{border:1px solid rgba(122,146,170,.25);border-radius:18px;padding:17px}
    .next-card{border-left:5px solid #2E7DB2;background:rgba(46,125,178,.08);border-radius:12px;padding:14px 16px}
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

def render_workflow(active_step: int | None = None):
    status = workflow_status()
    cols = st.columns(6)
    for i, item in enumerate(status):
        state_class = "done" if item["done"] else ("active" if active_step == item["step"] else "")
        state_text = "Complete" if item["done"] else ("Next" if active_step == item["step"] else "Pending")
        with cols[i]:
            st.markdown(
                f"""<div class="workflow-card {state_class}">
                <div class="step-no">STEP {item['step']}</div>
                <div class="step-title">{item['label']}</div>
                <div class="step-status">{'✅' if item['done'] else '•'} {state_text}</div>
                </div>""",
                unsafe_allow_html=True
            )

def case_sidebar():
    with st.sidebar:
        st.markdown("### Current Case")
        st.caption(st.session_state.case_id)
        st.write("**Scene:**", st.session_state.scene_type)
        st.write("**Location:**", st.session_state.location or "Not recorded")
        st.write("**Authority:**", st.session_state.agency)
        st.divider()
        st.markdown("### Progress")
        done = sum(1 for x in workflow_status() if x["done"])
        st.progress(done / 6)
        st.caption(f"{done}/6 workflow stages complete")
