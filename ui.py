import html
import streamlit as st
from core import APP_NAME, init_state, workflow_status


def apply_ui():
    init_state()
    st.markdown("""
    <style>
      [data-testid="stSidebar"],
      [data-testid="collapsedControl"]{
        display:none !important;
      }

      .block-container{
        max-width:none;
        padding-top:1rem;
        padding-bottom:4rem;
        padding-left:2rem;
        padding-right:338px;
      }

      .morbit-hero{
        padding:30px 34px;
        border-radius:24px;
        margin-bottom:18px;
        color:white;
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
      .evidence-card.body-first{
        border-color:rgba(240,165,60,.48);
        background:linear-gradient(145deg,rgba(240,165,60,.12),rgba(217,91,138,.05));
      }
      .evidence-rank{
        display:inline-block;min-width:25px;text-align:center;padding:3px 7px;
        border-radius:10px;background:#176EA5;color:white;font-weight:900;margin-right:6px;
      }
      .evidence-card.body-first .evidence-rank{background:#C87819}
      .evidence-meta{font-size:11px;opacity:.76;margin-top:5px}

      div[data-testid="stMetric"]{
        border:1px solid rgba(110,145,170,.18);
        border-radius:15px;
        padding:9px 11px;
        background:linear-gradient(145deg,rgba(23,110,165,.06),rgba(122,92,229,.035));
      }
      div[data-testid="stFileUploader"]{
        border:1px dashed rgba(49,198,216,.35);
        border-radius:17px;
        padding:8px;
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

      .morbit-right-rail{
        position:fixed;
        top:68px;
        right:18px;
        width:294px;
        max-height:calc(100vh - 88px);
        overflow:auto;
        z-index:99999;
        padding:16px;
        border-radius:20px;
        color:#EAF6FF;
        border:1px solid rgba(49,198,216,.24);
        background:
          radial-gradient(circle at 20% 8%,rgba(49,198,216,.12),transparent 24%),
          radial-gradient(circle at 90% 35%,rgba(122,92,229,.10),transparent 28%),
          linear-gradient(180deg,rgba(7,24,39,.97),rgba(11,34,55,.97));
        box-shadow:0 18px 44px rgba(0,0,0,.28);
        backdrop-filter:blur(14px);
      }
      .rail-title{font-size:15px;font-weight:900}
      .rail-sub{font-size:10px;color:#9FB8CB;margin-top:2px;margin-bottom:10px}
      .rail-summary{
        display:grid;
        grid-template-columns:1fr 1fr;
        gap:7px;
        margin-bottom:12px;
      }
      .rail-metric{
        padding:9px 8px;
        border-radius:12px;
        background:rgba(255,255,255,.04);
        border:1px solid rgba(255,255,255,.06);
      }
      .rail-metric b{font-size:16px}
      .rail-metric span{display:block;font-size:9px;color:#9FB8CB;margin-top:2px}
      .rail-progress-bg{
        height:7px;border-radius:999px;background:rgba(255,255,255,.08);
        overflow:hidden;margin:8px 0 13px;
      }
      .rail-progress-fill{
        height:100%;
        background:linear-gradient(90deg,#2FB47C,#31C6D8,#7A5CE5);
        border-radius:999px;
      }
      .rail-step{
        padding:9px 10px;
        margin:6px 0;
        border-radius:12px;
        border:1px solid rgba(130,155,178,.14);
        background:rgba(255,255,255,.025);
      }
      .rail-step.done{
        border-color:rgba(47,180,124,.40);
        background:rgba(47,180,124,.08);
      }
      .rail-step.current{
        border-color:rgba(49,198,216,.55);
        background:linear-gradient(90deg,rgba(49,198,216,.13),rgba(122,92,229,.08));
        box-shadow:0 7px 18px rgba(49,198,216,.08);
      }
      .rail-step-title{font-size:11px;font-weight:850}
      .rail-step-status{font-size:9px;color:#9FB8CB;margin-top:2px}
      .rail-case{
        margin-top:12px;
        padding-top:10px;
        border-top:1px solid rgba(255,255,255,.08);
        font-size:9px;
        color:#9FB8CB;
        line-height:1.55;
      }

      @media(max-width:1050px){
        .block-container{
          padding-right:1rem;
          padding-left:1rem;
          padding-bottom:150px;
        }
        .morbit-right-rail{
          top:auto;
          right:10px;
          left:10px;
          bottom:10px;
          width:auto;
          max-height:none;
          overflow:hidden;
          padding:10px 12px;
          border-radius:17px;
        }
        .rail-title,.rail-sub,.rail-summary,.rail-case{display:none}
        .rail-progress-bg{margin:4px 0 8px}
        .rail-steps{
          display:grid;
          grid-template-columns:repeat(6,1fr);
          gap:4px;
        }
        .rail-step{
          margin:0;
          padding:7px 5px;
          text-align:center;
        }
        .rail-step-title{font-size:9px}
        .rail-step-status{display:none}
      }

      @media(max-width:700px){
        .morbit-title{font-size:28px}
        .morbit-hero{padding:23px 20px}
        .rail-step-title{font-size:0}
        .rail-step-title .rail-mobile-icon{font-size:14px}
      }
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


def progress_rail():
    status = workflow_status()
    done = sum(1 for x in status if x["done"])
    next_step = next((x["step"] for x in status if not x["done"]), 6)
    pct = int(round((done / 6) * 100))
    evidence_count = (
        len(st.session_state.evidence_df)
        if st.session_state.evidence_df is not None else 0
    )

    step_html = []
    for item in status:
        if item["done"]:
            cls, icon, text = "done", "✅", "Completed"
        elif item["step"] == next_step:
            cls, icon, text = "current", "●", "Current / Next"
        else:
            cls, icon, text = "", "○", "Pending"

        step_html.append(
            f"""<div class="rail-step {cls}">
              <div class="rail-step-title"><span class="rail-mobile-icon">{icon}</span> {item['step']}. {html.escape(item['label'])}</div>
              <div class="rail-step-status">{text}</div>
            </div>"""
        )

    case_id = html.escape(str(st.session_state.case_id))
    scene_type = html.escape(str(st.session_state.scene_type))

    st.markdown(
        f"""<div class="morbit-right-rail">
          <div class="rail-title">🛡️ Case Progress</div>
          <div class="rail-sub">Permanent guided workflow tracker</div>
          <div class="rail-summary">
            <div class="rail-metric"><b>{done}/6</b><span>Functions complete</span></div>
            <div class="rail-metric"><b>{evidence_count}</b><span>Evidence rows</span></div>
          </div>
          <div class="rail-progress-bg">
            <div class="rail-progress-fill" style="width:{pct}%"></div>
          </div>
          <div class="rail-steps">{''.join(step_html)}</div>
          <div class="rail-case">
            <b>Case:</b> {case_id}<br>
            <b>Scene:</b> {scene_type}<br>
            AI visual findings remain proposals until investigator verification.
          </div>
        </div>""",
        unsafe_allow_html=True,
    )


def evidence_card(obs: dict):
    rank = obs.get("priority_rank", "")
    is_body = obs.get("possible_category") == "possible_human_body_or_remains"
    body_class = "body-first" if is_body else ""
    prefix = "Possible body/remains priority" if is_body else "Evidence priority"

    st.markdown(
        f"""<div class="evidence-card {body_class}">
        <span class="evidence-rank">{rank}</span>
        <b>{html.escape(str(obs.get('observation','')))}</b>
        <div class="evidence-meta">
        {prefix} &nbsp; • &nbsp;
        📍 {html.escape(str(obs.get('location_in_image','Location not specified')))} &nbsp; • &nbsp;
        {html.escape(str(obs.get('possible_category','other')))} &nbsp; • &nbsp;
        {html.escape(str(obs.get('confidence','unspecified')))} confidence
        </div>
        <div class="evidence-meta">{html.escape(str(obs.get('importance_reason','')))}</div>
        </div>""",
        unsafe_allow_html=True,
    )
