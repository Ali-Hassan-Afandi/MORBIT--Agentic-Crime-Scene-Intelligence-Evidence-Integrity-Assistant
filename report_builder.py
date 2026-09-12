from __future__ import annotations
import io, re
from datetime import datetime
from typing import Any
import pandas as pd
from PIL import Image
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

NAVY="17324D"; BLUE="2E5D9F"; PALE="F4F7FB"; GREY="6B7785"; RED="A63C46"; WHITE="FFFFFF"

def _shade(cell, fill):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd"); shd.set(qn("w:fill"), fill); tc_pr.append(shd)

def _cell(cell, text, bold=False, color="172033", size=9):
    cell.text=""
    p=cell.paragraphs[0]; r=p.add_run(str(text or ""))
    r.bold=bold; r.font.name="Aptos"; r.font.size=Pt(size); r.font.color.rgb=RGBColor.from_string(color)

def _heading(doc,text,level=1):
    p=doc.add_paragraph(style=f"Heading {level}")
    r=p.add_run(text); r.font.color.rgb=RGBColor.from_string(NAVY if level==1 else BLUE)
    return p

def _bullet(doc,text):
    p=doc.add_paragraph(style="List Bullet")
    r=p.add_run(str(text)); r.font.name="Aptos"; r.font.size=Pt(9.5)

def _number(doc,text):
    p=doc.add_paragraph(style="List Number")
    r=p.add_run(str(text)); r.font.name="Aptos"; r.font.size=Pt(9.5)

def _clean_inline_md(text: str) -> str:
    text = text or ""
    # Markdown links -> visible label (URL omitted from prose; source URLs have their own section).
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove common inline Markdown decoration.
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("```", "")
    text = text.replace("~~", "")
    text = re.sub(r"^\s*>\s?", "", text)
    return text.strip()


def _tokens(text):
    """
    Convert model text or Markdown-like text into clean Word structure.
    Output tokens: h1/h2/h3, bullet, number, paragraph.
    Markdown symbols never reach the final DOCX.
    """
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue

        # Markdown headings.
        if line.startswith("### "):
            out.append(("h3", _clean_inline_md(line[4:])))
            continue
        if line.startswith("## "):
            out.append(("h2", _clean_inline_md(line[3:])))
            continue
        if line.startswith("# "):
            out.append(("h1", _clean_inline_md(line[2:])))
            continue

        # Bullets: -, *, +, •
        m = re.match(r"^(?:[-*+•])\s+(.*)$", line)
        if m:
            out.append(("bullet", _clean_inline_md(m.group(1))))
            continue

        # Numbered lists: 1. / 1) / (1)
        m = re.match(r"^(?:\(?\d+\)?[.)])\s+(.*)$", line)
        if m:
            out.append(("number", _clean_inline_md(m.group(1))))
            continue

        cleaned = _clean_inline_md(line)

        # Plain section labels from the RAG prompt become subheadings.
        if (
            len(cleaned) <= 90
            and cleaned.endswith(":")
            and not cleaned.lower().startswith(("http://", "https://"))
        ):
            out.append(("h3", cleaned[:-1].strip()))
        else:
            out.append(("p", cleaned))
    return out

def build_rich_report(
    case: dict[str,Any], analysis: dict[str,Any] | None, guidance: str, sources: list[dict],
    evidence_df: pd.DataFrame | None, integrity_score: int, integrity_alerts: list[str],
    vision_records: list[dict], verified_visuals: list[str], search_plan: dict[str,Any] | None,
    investigator_notes: str, scene_map_png: bytes | None=None, map_items: pd.DataFrame | None=None
) -> bytes:
    doc=Document()
    sec=doc.sections[0]
    sec.top_margin=Inches(.55); sec.bottom_margin=Inches(.55); sec.left_margin=Inches(.65); sec.right_margin=Inches(.65)
    doc.styles["Normal"].font.name="Aptos"; doc.styles["Normal"].font.size=Pt(9.5)

    hp=sec.header.paragraphs[0]
    hp.text="MORBIT CSI CaseAssistant"
    hp.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    hp.runs[0].font.size=Pt(8); hp.runs[0].font.color.rgb=RGBColor.from_string(GREY)

    banner=doc.add_table(rows=1,cols=1); banner.alignment=WD_TABLE_ALIGNMENT.CENTER
    c=banner.cell(0,0); _shade(c,NAVY)
    p=c.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run("MORBIT CSI CaseAssistant"); r.font.name="Aptos Display"; r.font.size=Pt(28); r.font.bold=True; r.font.color.rgb=RGBColor.from_string(WHITE)
    p2=c.add_paragraph(); p2.alignment=WD_ALIGN_PARAGRAPH.CENTER
    rr=p2.add_run("Crime Scene Intelligence • Evidence Integrity • Case Reporting")
    rr.font.name="Aptos"; rr.font.size=Pt(12); rr.font.color.rgb=RGBColor.from_string("D8E8F8")

    title=doc.add_paragraph(); title.alignment=WD_ALIGN_PARAGRAPH.CENTER
    tr=title.add_run("Crime Scene Intelligence & Evidence Integrity Report")
    tr.font.size=Pt(19); tr.font.bold=True; tr.font.color.rgb=RGBColor.from_string(NAVY)

    meta=doc.add_table(rows=4,cols=4); meta.style="Table Grid"
    rows=[
        ("Case ID",case.get("case_id"),"Scene Type",case.get("scene_type")),
        ("Date / Time",case.get("scene_dt"),"Location",case.get("location")),
        ("Authority",case.get("agency"),"Environment",case.get("environment")),
        ("Scene Size",case.get("scene_size"),"Generated",datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    for i,row in enumerate(rows):
        for j,val in enumerate(row):
            _cell(meta.cell(i,j),val,bold=(j%2==0),color=WHITE if j%2==0 else "243447")
            _shade(meta.cell(i,j), BLUE if j%2==0 else PALE)

    _heading(doc,"1. Scene Intake",1)
    doc.add_paragraph(case.get("description") or "No investigator narrative supplied.")

    _heading(doc,"2. Multimodal Image Record",1)
    if not vision_records:
        doc.add_paragraph("No scene images were uploaded.")
    else:
        for rec in vision_records:
            m=rec.get("metadata",{}); a=rec.get("analysis",{})
            p=doc.add_paragraph(); q=p.add_run(f"{rec.get('image_id','IMG')} — {m.get('filename','image')}")
            q.bold=True; q.font.color.rgb=RGBColor.from_string(BLUE)
            image_bytes=rec.get("image_bytes")
            if image_bytes:
                try:
                    with Image.open(io.BytesIO(image_bytes)) as im:
                        im=im.convert("RGB"); converted=io.BytesIO(); im.save(converted,format="JPEG",quality=88); converted.seek(0)
                        pic=doc.add_paragraph(); pic.alignment=WD_ALIGN_PARAGRAPH.CENTER
                        pic.add_run().add_picture(converted,width=Inches(5.8))
                except Exception as exc:
                    doc.add_paragraph(f"[Image could not be embedded: {exc}]")
            t=doc.add_table(rows=2,cols=4); t.style="Table Grid"
            vals=[("Dimensions",f"{m.get('width','')} × {m.get('height','')}"),("Format",m.get("format","")),
                  ("SHA-256",m.get("sha256","")[:24]+"…"),("Bytes",f"{m.get('bytes',0):,}")]
            for j,(k,v) in enumerate(vals):
                _cell(t.cell(0,j),k,True,WHITE,8); _shade(t.cell(0,j),BLUE)
                _cell(t.cell(1,j),v,size=8); _shade(t.cell(1,j),PALE)
            p=doc.add_paragraph(); p.add_run("AI visual summary: ").bold=True; p.add_run(a.get("image_summary",""))
            for obs in a.get("potential_observations",[]):
                _bullet(doc,f"{obs.get('observation','')} — confidence: {obs.get('confidence','')} — category: {obs.get('possible_category','other')}")
            if a.get("limitations"):
                p=doc.add_paragraph(); p.add_run("Limitations: ").bold=True; p.add_run("; ".join(a["limitations"]))

    _heading(doc,"3. Investigator-Verified Visual Observations",1)
    if verified_visuals:
        for x in verified_visuals: _bullet(doc,x)
    else:
        doc.add_paragraph("No AI-proposed visual observations were marked as investigator-verified.")

    _heading(doc,"4. Scene Analysis Agent",1)
    analysis=analysis or {}
    doc.add_paragraph(analysis.get("scene_summary","No scene-agent analysis generated."))
    if analysis.get("visual_context_summary"):
        p=doc.add_paragraph(); p.add_run("Visual context: ").bold=True; p.add_run(analysis["visual_context_summary"])
    if analysis.get("hazards"):
        _heading(doc,"Potential Hazards / Cautions",2)
        for x in analysis["hazards"]: _bullet(doc,x)
    if analysis.get("immediate_documentation_priorities"):
        _heading(doc,"Immediate Documentation Priorities",2)
        for x in analysis["immediate_documentation_priorities"]: _bullet(doc,x)

    _heading(doc,"5. Evidence Inventory & Integrity",1)
    if evidence_df is not None and not evidence_df.empty:
        cols=[c for c in ["Evidence ID","Item","Category","Location","Basis","Photographed","Packaging Recorded","Seal Recorded","Custody Started"] if c in evidence_df.columns]
        tbl=doc.add_table(rows=1,cols=len(cols)); tbl.style="Table Grid"
        for j,cname in enumerate(cols):
            _cell(tbl.cell(0,j),cname,True,WHITE,7.5); _shade(tbl.cell(0,j),NAVY)
        for _,row in evidence_df.iterrows():
            cells=tbl.add_row().cells
            for j,cname in enumerate(cols):
                val=row[cname]
                if isinstance(val,bool): val="Yes" if val else "No"
                _cell(cells[j],val,size=7.5)
        p=doc.add_paragraph(); r=p.add_run(f"Documentation completeness: {integrity_score}%"); r.bold=True; r.font.color.rgb=RGBColor.from_string(BLUE)
        for a in integrity_alerts: _bullet(doc,a)
    else:
        doc.add_paragraph("No evidence inventory is currently recorded.")

    _heading(doc,"6. Recommended Crime Scene Search Strategy",1)
    if search_plan:
        t=doc.add_table(rows=4,cols=2); t.style="Table Grid"
        entries=[("Recommended method",search_plan.get("recommended","")),("Alternative method",search_plan.get("alternative","")),
                 ("Rationale",search_plan.get("rationale","")),("Operational caution",search_plan.get("caution",""))]
        for i,(k,v) in enumerate(entries):
            _cell(t.cell(i,0),k,True,WHITE); _shade(t.cell(i,0),BLUE); _cell(t.cell(i,1),v)
    else:
        doc.add_paragraph("No search-method recommendation generated.")

    _heading(doc,"7. Scene of Crime Map",1)
    if map_items is not None and not map_items.empty:
        _heading(doc,"Site-Plan Evidence Coordinates",2)
        map_cols=[c for c in ["Evidence ID","Evidence Item","Category","X","Y","Notes"] if c in map_items.columns]
        mt=doc.add_table(rows=1,cols=len(map_cols)); mt.style="Table Grid"
        for j,cname in enumerate(map_cols):
            _cell(mt.cell(0,j),cname,True,WHITE,7.5); _shade(mt.cell(0,j),BLUE)
        for _,row in map_items.iterrows():
            cells=mt.add_row().cells
            for j,cname in enumerate(map_cols):
                _cell(cells[j],row.get(cname,""),size=7.5)

    if scene_map_png:
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(io.BytesIO(scene_map_png),width=Inches(6.7))
        c=doc.add_paragraph("Figure: Investigator-entered schematic scene map. North is fixed at the top.")
        c.alignment=WD_ALIGN_PARAGRAPH.CENTER; c.runs[0].italic=True; c.runs[0].font.size=Pt(8)
    else:
        doc.add_paragraph("No scene map generated.")

    _heading(doc,"8. Source-Grounded Forensic Guidance",1)
    if guidance:
        for typ,text in _tokens(guidance):
            if typ=="h1": _heading(doc,text,2)
            elif typ in {"h2","h3"}: _heading(doc,text,3)
            elif typ=="bullet": _bullet(doc,text)
            elif typ=="number": _number(doc,text)
            else: doc.add_paragraph(text)
    else:
        doc.add_paragraph("No source-grounded guidance generated.")

    _heading(doc,"9. Investigator Notes",1)
    doc.add_paragraph(investigator_notes or "No additional investigator notes recorded.")

    _heading(doc,"10. Source References",1)
    if sources:
        for i,s in enumerate(sources,start=1):
            p=doc.add_paragraph(); r=p.add_run(f"[S{i}] {s.get('title','Untitled source')}"); r.bold=True; r.font.color.rgb=RGBColor.from_string(BLUE)
            doc.add_paragraph(f"Agency: {s.get('agency','')} | Type: {s.get('document_type','')} | Page: {s.get('page') or 'N/A'} | Verification: {s.get('verification','')}")
            if s.get("url"): doc.add_paragraph(s["url"])
    else:
        doc.add_paragraph("No retrieved sources attached.")

    _heading(doc,"11. Disclaimer & Human Review",1)
    p=doc.add_paragraph()
    r=p.add_run(
        "This document is an AI-assisted forensic documentation draft. Image analysis and model-generated "
        "observations are not laboratory findings and do not establish identity, guilt, cause, substance, "
        "source attribution or scientific confirmation. Investigator verification, applicable law, agency "
        "SOPs, laboratory examination and chain-of-custody requirements remain controlling."
    )
    r.font.color.rgb=RGBColor.from_string(RED)

    fp=sec.footer.paragraphs[0]; fp.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fr=fp.add_run("MORBIT CSI CaseAssistant • Human-Supervised Forensic Documentation")
    fr.font.size=Pt(8); fr.font.color.rgb=RGBColor.from_string(GREY)

    out=io.BytesIO(); doc.save(out); return out.getvalue()
