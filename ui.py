import streamlit as st
from core import APP_NAME, init_state, workflow_status

PAGE_TARGETS = {
    1: ("pages/1_Scene_Intake.py", "Case Intake", "📝"),
    2: ("pages/2_Visual_Intelligence.py", "Visual Intelligence", "📷"),
    3: ("pages/3_Agentic_Analysis.py", "Agentic Analysis", "🧠"),
    4: ("pages/4_Search_and_Scene_Map.py", "Search & Scene Map", "🧭"),
    5: ("pages/5_Evidence_Integrity.py", "Evidence Integrity", "🔐"),
    6: ("pages/6_Rich_Report.py", "Rich Report", "📄"),
}

def apply_ui():
    init_state()
    st.markdown("""
    <style>
    :root{
      --morbit-navy:#071827;
      --morbit-blue:#176EA5;
      --morbit-cyan:#31C6D8;
      --morbit-violet:#7A5CE5;
      --morbit-green:#2FB47C;
      --morbit-amber:#F0A53C;
      --morbit-soft:#F4F8FC;
      --morbit-muted:#8FA8BC;
    }

    .block-container{
      max-width:1450px;
      padding-top:1.05rem;
      padding-bottom:3.5rem;
    }

    [data-testid="stSidebar"]{
      border-right:1px solid rgba(104,143,173,.20);
      background:
        radial-gradient(circle at 12% 7%, rgba(49,198,216,.12), transparent 25%),
        radial-gradient(circle at 90% 28%, rgba(122,92,229,.10), transparent 28%),
        linear-gradient(180deg,rgba(7,24,39,.98),rgba(10,30,49,.98));
    }
    [data-testid="stSidebar"] *{
      scrollbar-width:thin;
    }

    .morbit-brand{
      padding:14px 14px 12px;
      border:1px solid rgba(49,198,216,.18);
      border-radius:18px;
      background:linear-gradient(145deg,rgba(49,198,216,.10),rgba(122,92,229,.08));
      margin-bottom:14px;
    }
    .morbit-brand-title{
      font-size:17px;
      font-weight:900;
      letter-spacing:.01em;
    }
    .morbit-brand-sub{
      color:#9FB8CB;
      font-size:11px;
      margin-top:3px;
    }

    .morbit-hero{
      position:relative;
      overflow:hidden;
      background:
        radial-gradient(circle at 82% 17%, rgba(49,198,216,.27), transparent 25%),
        radial-gradient(circle at 12% 90%, rgba(122,92,229,.23), transparent 31%),
        linear-gradient(135deg,#071827 0%,#103956 58%,#176A86 100%);
      border-radius:26px;
      padding:34px 38px;
      margin-bottom:20px;
      color:white;
      box-shadow:0 20px 50px rgba(0,0,0,.22);
      border:1px solid rgba(255,255,255,.08);
    }
    .morbit-kicker{
      font-size:11px;
      letter-spacing:.18em;
      font-weight:850;
      color:#91F0FF;
    }
    .morbit-title{
      font-size:36px;
      font-weight:900;
      line-height:1.08;
      margin-top:8px;
    }
    .morbit-sub{
      font-size:14px;
      color:#D9EAF6;
      margin-top:9px;
      max-width:1000px;
    }

    .workflow-card{
      border:1px solid rgba(122,146,170,.24);
      border-radius:17px;
      padding:14px;
      min-height:112px;
      background:linear-gradient(180deg,rgba(255,255,255,.025),rgba(80,120,160,.045));
      box-shadow:0 7px 18px rgba(16,40,65,.055);
      transition:.18s ease;
    }
    .workflow-card.done{
      border-color:rgba(47,180,124,.52);
      background:linear-gradient(180deg,rgba(47,180,124,.13),rgba(47,180,124,.05));
    }
    .workflow-card.active{
      border-color:#31C6D8;
      background:linear-gradient(180deg,rgba(49,198,216,.15),rgba(122,92,229,.07));
      box-shadow:0 9px 24px rgba(49,198,216,.13);
      transform:translateY(-2px);
    }
    .step-no{font-size:10px;font-weight:900;letter-spacing:.08em;opacity:.72}
    .step-title{font-size:15px;font-weight:850;margin-top:6px}
    .step-status{font-size:11px;opacity:.80;margin-top:8px}

    .sidebar-step{
      border-radius:13px;
      border:1px solid rgba(116,145,170,.18);
      padding:9px 11px;
      margin:6px 0;
      background:rgba(255,255,255,.025);
    }
    .sidebar-step.done{
      border-color:rgba(47,180,124,.38);
      background:rgba(47,180,124,.08);
    }
    .sidebar-step.active{
      border-color:rgba(49,198,216,.52);
      background:linear-gradient(90deg,rgba(49,198,216,.14),rgba(122,92,229,.09));
      box-shadow:0 6px 18px rgba(49,198,216,.08);
    }
    .sidebar-step-title{
      font-size:12px;
      font-weight:800;
      margin-bottom:2px;
    }
    .sidebar-step-status{
      font-size:10px;
      color:#9FB8CB;
    }

    .next-card{
      border-left:5px solid #31C6D8;
      background:linear-gradient(90deg,rgba(49,198,216,.11),rgba(122,92,229,.05));
      border-radius:13px;
      padding:15px 17px;
      box-shadow:0 8px 20px rgba(33,84,120,.06);
    }

    .input-banner{
      padding:14px 16px;
      border-radius:14px;
      background:linear-gradient(90deg,rgba(23,110,165,.11),rgba(122,92,229,.08));
      border:1px solid rgba(49,198,216,.20);
      margin-bottom:10px;
    }

    .safety-card{
      padding:12px 14px;
      border-radius:12px;
      background:linear-gradient(90deg,rgba(240,165,60,.10),rgba(217,91,138,.07));
      border:1px solid rgba(240,165,60,.22);
    }

    .evidence-card{
      border:1px solid rgba(90,135,168,.22);
      border-radius:15px;
      padding:12px 14px;
      margin:8px 0;
      background:linear-gradient(145deg,rgba(23,110,165,.06),rgba(122,92,229,.035));
    }
    .evidence-meta{
      font-size:11px;
      color:#8FA8BC;
      margin-top:4px;
    }

    div[data-testid="stMetric"]{
      border:1px solid rgba(105,135,165,.20);
      border-radius:16px;
      padding:10px 12px;
      background:linear-gradient(145deg,rgba(30,109,165,.06),rgba(122,92,229,.04));
      box-shadow:0 5px 16px rgba(0,0,0,.04);
    }

    div[data-testid="stFileUploader"]{
      border:1px dashed rgba(49,198,216,.35);
      border-radius:18px;
      padding:8px;
      background:linear-gradient(145deg,rgba(49,198,216,.04),rgba(122,92,229,.025));
    }

    .stButton > button{
      border-radius:12px;
      transition:.16s ease;
    }
    .stButton > button[kind="primary"]{
      border:0;
      background:linear-gradient(90deg,#176EA5,#31C6D8 56%,#7A5CE5);
      color:white;
      font-weight:800;
      box-shadow:0 8px 22px rgba(49,198,216,.19);
    }
    .stButton > button[kind="primary"]:hover{
      filter:brightness(1.07);
      transform:translateY(-1px);
    }

    .next-action{
      margin-top:14px;
      padding:18px 20px;
      border-radius:16px;
      background:linear-gradient(100deg,rgba(23,110,165,.16),rgba(49,198,216,.14),rgba(122,92,229,.13));
      border:1px solid rgba(49,198,216,.32);
      box-shadow:0 10px 26px rgba(30,105,150,.10);
      font-size:15px;
    }
    .next-action strong{
      color:#31C6D8;
      font-size:16px;
    }

    @media (max-width: 900px){
      .morbit-title{font-size:29px}
      .morbit-hero{padding:27px 24px}
      .block-container{padding-left:1rem;padding-right:1rem}
    }
    </style>
    """, unsafe_allow_html=True)


def hero(page_name: str, subtitle: str):
    st.markdown(f"""
    <div class="morbit-hero">
      <div class="morbit-kicker">HUMAN-SUPERVISED FORENSIC INTELLIGENCE</div>
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
                <div class="step-status">{'✅' if item['done'] else ('◉' if active_step == item['step'] else '○')} {state_text}</div>
                </div>""",
                unsafe_allow_html=True
            )


def case_sidebar(active_step: int | None = None):
    status = workflow_status()
    done = sum(1 for x in status if x["done"])
    next_pending = next((x["step"] for x in status if not x["done"]), 6)

    with st.sidebar:
        st.markdown(
            f"""<div class="morbit-brand">
            <div class="morbit-brand-title">🛡️ {APP_NAME}</div>
            <div class="morbit-brand-sub">Guided case workflow • Human supervised</div>
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown("### Current Case")
        st.caption(st.session_state.case_id)
        c1, c2 = st.columns(2)
        c1.metric("Progress", f"{done}/6")
        c2.metric("Evidence", len(st.session_state.evidence_df) if st.session_state.evidence_df is not None else 0)
        st.progress(done / 6)

        st.markdown("### Workflow Tracker")
        for item in status:
            step = item["step"]
            is_active = active_step == step or (active_step is None and step == next_pending)
            cls = "done" if item["done"] else ("active" if is_active else "")
            status_text = "Completed" if item["done"] else ("Current step" if is_active else "Pending")
            icon = "✅" if item["done"] else ("●" if is_active else "○")
            st.markdown(
                f"""<div class="sidebar-step {cls}">
                <div class="sidebar-step-title">{icon} {step}. {item['label']}</div>
                <div class="sidebar-step-status">{status_text}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.markdown("### Quick Navigation")
        st.page_link("app.py", label="Command Dashboard", icon="🏠")
        for step, (target, label, icon) in PAGE_TARGETS.items():
            st.page_link(target, label=label, icon=icon)

        st.divider()
        st.caption(f"Scene: {st.session_state.scene_type}")
        st.caption(f"Authority: {st.session_state.agency}")
        st.caption("AI observations remain proposals until investigator verification.")
