import streamlit as st
from core import APP_NAME, init_state, workflow_status


def apply_ui():
    init_state()
    st.markdown("""
    <style>
      .block-container{max-width:1450px;padding-top:1rem;padding-bottom:4rem}
      [data-testid="stSidebar"]{
        border-right:1px solid rgba(49,198,216,.18);
        background:
          radial-gradient(circle at 20% 8%,rgba(49,198,216,.11),transparent 25%),
          linear-gradient(180deg,#071827,#0B2237);
      }
      .morbit-hero{
        padding:30px 34px;border-radius:24px;margin-bottom:18px;color:white;
        background:
          radial-gradient(circle at 86% 14%,rgba(49,198,216,.28),transparent 24%),
          radial-gradient(circle at 8% 100%,rgba(122,92,229,.25),transparent 30%),
          linear-gradient(135deg,#071827 0%,#103956 58%,#176A86 100%);
        box-shadow:0 18px 46px rgba(0,0,0,.20);
        border:1px solid rgba(255,255,255,.07);
      }
      .morbit-kicker{font-size:11px;font-weight:850;letter-spacing:.16em;color:#95F2FF}
      .morbit-title{font-size:36px;font-weight:900;line-height:1.08;margin-top:7px}
      .morbit-sub{font-size:14px;color:#D8EAF5;margin-top:8px}
      .panel{
        padding:15px 17px;border-radius:16px;
        border:1px solid rgba(75,135,170,.20);
        background:linear-gradient(145deg,rgba(23,110,165,.07),rgba(122,92,229,.04));
        margin:8px 0 14px 0;
      }
      .evidence-card{
        padding:13px 15px;border-radius:15px;margin:8px 0;
        border:1px solid rgba(49,198,216,.21);
        background:linear-gradient(145deg,rgba(49,198,216,.075),rgba(122,92,229,.045));
      }
      .evidence-rank{
        display:inline-block;min-width:25px;text-align:center;padding:3px 7px;
        border-radius:10px;background:#176EA5;color:white;font-weight:900;margin-right:6px;
      }
      .evidence-meta{font-size:11px;opacity:.76;margin-top:5px}
      .workflow-step{
        padding:10px 11px;border-radius:13px;margin:6px 0;
        border:1px solid rgba(120,150,175,.18);background:rgba(255,255,255,.025);
      }
      .workflow-step.done{border-color:rgba(47,180,124,.38);background:rgba(47,180,124,.08)}
      .workflow-step.current{border-color:rgba(49,198,216,.55);background:rgba(49,198,216,.10)}
      .workflow-title{font-size:12px;font-weight:850}
      .workflow-status{font-size:10px;color:#9FB8CB;margin-top:2px}
      div[data-testid="stMetric"]{
        border:1px solid rgba(110,145,170,.18);border-radius:15px;padding:9px 11px;
        background:linear-gradient(145deg,rgba(23,110,165,.06),rgba(122,92,229,.035));
      }
      div[data-testid="stFileUploader"]{
        border:1px dashed rgba(49,198,216,.35);border-radius:17px;padding:8px;
      }
      .stButton>button{border-radius:12px;font-weight:700}
      .stButton>button[kind="primary"]{
        border:0;color:white;
        background:linear-gradient(90deg,#176EA5,#31C6D8 55%,#7A5CE5);
        box-shadow:0 8px 20px rgba(49,198,216,.18);
      }
      .ready-box{
        padding:15px 17px;border-radius:15px;
        border-left:5px solid #31C6D8;
        background:linear-gradient(90deg,rgba(49,198,216,.11),rgba(122,92,229,.05));
      }
      .complete-box{
        padding:15px 17px;border-radius:15px;
        border-left:5px solid #2FB47C;
        background:linear-gradient(90deg,rgba(47,180,124,.12),rgba(49,198,216,.04));
      }
      @media(max-width:900px){.morbit-title{font-size:29px}.morbit-hero{padding:24px}}
    </style>
    """, unsafe_allow_html=True)


def hero(subtitle: str):
    st.markdown(f"""
    <div class="morbit-hero">
      <div class="morbit-kicker">HUMAN-SUPERVISED FORENSIC DOCUMENTATION</div>
      <div class="morbit-title">{APP_NAME}</div>
      <div class="morbit-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def guided_sidebar():
    status = workflow_status()
    done = sum(1 for x in status if x["done"])
    next_step = next((x["step"] for x in status if not x["done"]), 6)

    with st.sidebar:
        st.markdown(f"## 🛡️ {APP_NAME}")
        st.caption("Single-page guided case workflow")
        a,b = st.columns(2)
        a.metric("Progress", f"{done}/6")
        b.metric("Evidence", len(st.session_state.evidence_df) if st.session_state.evidence_df is not None else 0)
        st.progress(done / 6)

        st.markdown("### Function Completion")
        for item in status:
            if item["done"]:
                cls, icon, text = "done", "✅", "Completed"
            elif item["step"] == next_step:
                cls, icon, text = "current", "●", "Current / Next"
            else:
                cls, icon, text = "", "○", "Pending"

            st.markdown(
                f"""<div class="workflow-step {cls}">
                <div class="workflow-title">{icon} {item['step']}. {item['label']}</div>
                <div class="workflow-status">{text}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.divider()
        st.caption(f"Case: {st.session_state.case_id}")
        st.caption(f"Scene: {st.session_state.scene_type}")
        st.caption("AI visual findings remain proposals until investigator verification.")


def evidence_card(obs: dict):
    rank = obs.get("priority_rank", "")
    st.markdown(
        f"""<div class="evidence-card">
        <span class="evidence-rank">{rank}</span>
        <b>{obs.get('observation','')}</b>
        <div class="evidence-meta">
        📍 {obs.get('location_in_image','Location not specified')} &nbsp; • &nbsp;
        {obs.get('possible_category','other')} &nbsp; • &nbsp;
        {obs.get('confidence','unspecified')} confidence
        </div>
        <div class="evidence-meta">{obs.get('importance_reason','')}</div>
        </div>""",
        unsafe_allow_html=True,
    )
