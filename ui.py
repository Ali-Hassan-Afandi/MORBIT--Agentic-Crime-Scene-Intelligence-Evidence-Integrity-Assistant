import streamlit as st
from core import APP_NAME, APP_VERSION, init_state, workflow_status

def apply_ui():
    init_state()
    st.markdown("""
    <style>
    :root{
      --morbit-navy:#0A1D32;
      --morbit-blue:#1B6CA8;
      --morbit-cyan:#2FC3D8;
      --morbit-violet:#7457D9;
      --morbit-green:#2AA876;
      --morbit-amber:#E8A23A;
      --morbit-pink:#D95B8A;
      --morbit-soft:#F5F8FC;
    }

    .block-container{
      max-width:1400px;
      padding-top:1.15rem;
      padding-bottom:3rem;
    }

    [data-testid="stSidebar"]{
      border-right:1px solid rgba(90,120,155,.18);
      background:
        radial-gradient(circle at 15% 10%, rgba(47,195,216,.08), transparent 28%),
        radial-gradient(circle at 80% 35%, rgba(116,87,217,.08), transparent 30%);
    }

    .morbit-hero{
      position:relative;
      overflow:hidden;
      background:
        radial-gradient(circle at 80% 20%, rgba(47,195,216,.24), transparent 28%),
        radial-gradient(circle at 10% 90%, rgba(116,87,217,.22), transparent 32%),
        linear-gradient(135deg,#081A2D 0%,#113855 58%,#1A5D7D 100%);
      border-radius:26px;
      padding:32px 36px;
      margin-bottom:20px;
      color:white;
      box-shadow:0 18px 44px rgba(0,0,0,.20);
      border:1px solid rgba(255,255,255,.08);
    }

    .morbit-kicker{
      font-size:11px;
      letter-spacing:.18em;
      font-weight:850;
      color:#8EEBFF;
    }
    .morbit-title{
      font-size:35px;
      font-weight:900;
      line-height:1.08;
      margin-top:8px;
    }
    .morbit-sub{
      font-size:14px;
      color:#D9EAF6;
      margin-top:8px;
      max-width:1000px;
    }

    .workflow-card{
      border:1px solid rgba(122,146,170,.25);
      border-radius:17px;
      padding:14px 14px;
      min-height:110px;
      background:linear-gradient(180deg,rgba(255,255,255,.03),rgba(80,120,160,.05));
      box-shadow:0 7px 18px rgba(16,40,65,.06);
    }
    .workflow-card.done{
      border-color:rgba(42,168,118,.55);
      background:linear-gradient(180deg,rgba(42,168,118,.12),rgba(42,168,118,.05));
    }
    .workflow-card.active{
      border-color:#2FC3D8;
      background:linear-gradient(180deg,rgba(47,195,216,.14),rgba(116,87,217,.06));
      box-shadow:0 8px 22px rgba(47,195,216,.12);
    }
    .step-no{font-size:10px;font-weight:900;letter-spacing:.08em;opacity:.72}
    .step-title{font-size:15px;font-weight:850;margin-top:6px}
    .step-status{font-size:11px;opacity:.78;margin-top:8px}

    .next-card{
      border-left:5px solid #2FC3D8;
      background:linear-gradient(90deg,rgba(47,195,216,.11),rgba(116,87,217,.05));
      border-radius:13px;
      padding:15px 17px;
      box-shadow:0 8px 20px rgba(33,84,120,.06);
    }

    .input-banner{
      padding:14px 16px;
      border-radius:14px;
      background:linear-gradient(90deg,rgba(27,108,168,.11),rgba(116,87,217,.08));
      border:1px solid rgba(47,195,216,.20);
      margin-bottom:10px;
    }

    .safety-card{
      padding:12px 14px;
      border-radius:12px;
      background:linear-gradient(90deg,rgba(232,162,58,.10),rgba(217,91,138,.07));
      border:1px solid rgba(232,162,58,.22);
    }

    div[data-testid="stMetric"]{
      border:1px solid rgba(105,135,165,.20);
      border-radius:16px;
      padding:10px 12px;
      background:linear-gradient(145deg,rgba(30,109,165,.06),rgba(116,87,217,.04));
    }

    .stButton > button[kind="primary"]{
      border:0;
      background:linear-gradient(90deg,#1B6CA8,#2FC3D8 56%,#7457D9);
      color:white;
      font-weight:800;
      box-shadow:0 8px 22px rgba(47,195,216,.20);
    }
    .stButton > button[kind="primary"]:hover{
      filter:brightness(1.07);
      transform:translateY(-1px);
    }
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
        state_text = "Complete" if item["done"] else ("Current / Next" if active_step == item["step"] else "Pending")
        with cols[i]:
            st.markdown(
                f"""<div class="workflow-card {state_class}">
                <div class="step-no">STEP {item['step']}</div>
                <div class="step-title">{item['label']}</div>
                <div class="step-status">{'✅' if item['done'] else '●'} {state_text}</div>
                </div>""",
                unsafe_allow_html=True
            )

def case_sidebar():
    with st.sidebar:
        st.markdown("### 🛡️ Current Case")
        st.caption(st.session_state.case_id)
        st.write("**Scene:**", st.session_state.scene_type)
        st.write("**Location:**", st.session_state.location or "Not recorded")
        st.write("**Authority:**", st.session_state.agency)
        st.divider()
        st.markdown("### 📈 Progress")
        done = sum(1 for x in workflow_status() if x["done"])
        st.progress(done / 6)
        st.caption(f"{done}/6 workflow stages complete")
