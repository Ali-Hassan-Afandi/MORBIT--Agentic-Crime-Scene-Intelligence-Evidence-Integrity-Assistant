from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Any

import pandas as pd
from PIL import Image
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn


NAVY = "17324D"
BLUE = "2E5D9F"
LIGHT_BLUE = "EAF1FA"
PALE = "F4F7FB"
GREY = "6B7785"
RED = "A63C46"
WHITE = "FFFFFF"


def _shade(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tc_pr.append(shd)


def _cell_text(cell, text: str, bold=False, color="172033", size=9):
    cell.text = ""
    p = cell.paragraphs[0]
    r = p.add_run(str(text or ""))
    r.bold = bold
    r.font.name = "Aptos"
    r.font.size = Pt(size)
    r.font.color.rgb = RGBColor.from_string(color)


def _add_heading(doc, text: str, level=1):
    p = doc.add_paragraph(style=f"Heading {level}")
    r = p.add_run(text)
    r.font.color.rgb = RGBColor.from_string(NAVY if level == 1 else BLUE)
    return p


def _add_bullet(doc, text: str):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(str(text))
    r.font.name = "Aptos"
    r.font.size = Pt(9.5)


def _clean_markdown(text: str) -> list[tuple[str, str]]:
    """
    Convert lightweight model markdown into structured Word-friendly tokens.
    Returned type: heading|bullet|body.
    """
    out = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"\*\*(.*?)\*\*", r"\1", line)
        if line.startswith("### "):
            out.append(("heading3", line[4:]))
        elif line.startswith("## "):
            out.append(("heading2", line[3:]))
        elif line.startswith("# "):
            out.append(("heading1", line[2:]))
        elif line.startswith(("- ", "• ")):
            out.append(("bullet", line[2:]))
        else:
            out.append(("body", line))
    return out


def build_rich_report(
    case: dict[str, Any],
    analysis: dict[str, Any] | None,
    guidance: str,
    sources: list[dict],
    evidence_df: pd.DataFrame | None,
    integrity_score: int,
    integrity_alerts: list[str],
    vision_records: list[dict],
    verified_visuals: list[str],
    search_plan: dict[str, Any] | None,
    investigator_notes: str,
    scene_map_png: bytes | None = None,
) -> bytes:
    doc = Document()

    sec = doc.sections[0]
    sec.top_margin = Inches(0.55)
    sec.bottom_margin = Inches(0.55)
    sec.left_margin = Inches(0.65)
    sec.right_margin = Inches(0.65)

    # Base styles
    normal = doc.styles["Normal"]
    normal.font.name = "Aptos"
    normal.font.size = Pt(9.5)
    normal.font.color.rgb = RGBColor.from_string("243447")

    for level, size in [(1, 17), (2, 13), (3, 11)]:
        style = doc.styles[f"Heading {level}"]
        style.font.name = "Aptos Display"
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = RGBColor.from_string(NAVY if level == 1 else BLUE)

    # Header
    header = sec.header
    hp = header.paragraphs[0]
    hp.text = "MORBIT — Agentic Crime Scene Intelligence & Evidence Integrity Assistant"
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hp.runs[0].font.size = Pt(8)
    hp.runs[0].font.color.rgb = RGBColor.from_string(GREY)

    # Cover banner
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    _shade(cell, NAVY)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("MORBIT")
    r.font.name = "Aptos Display"; r.font.size = Pt(28); r.font.bold = True
    r.font.color.rgb = RGBColor.from_string(WHITE)
    p2 = cell.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = p2.add_run("Agentic Crime Scene Intelligence & Evidence Integrity Assistant")
    rr.font.name = "Aptos"; rr.font.size = Pt(12); rr.font.color.rgb = RGBColor.from_string("D8E8F8")

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    tr = title.add_run("Crime Scene Intelligence & Evidence Integrity Report")
    tr.font.name = "Aptos Display"; tr.font.size = Pt(19); tr.font.bold = True
    tr.font.color.rgb = RGBColor.from_string(NAVY)

    meta = doc.add_table(rows=4, cols=4)
    meta.alignment = WD_TABLE_ALIGNMENT.CENTER
    meta.style = "Table Grid"
    rows = [
        ("Case ID", case.get("case_id"), "Scene Type", case.get("scene_type")),
        ("Date / Time", case.get("scene_dt"), "Location", case.get("location")),
        ("Authority Mode", case.get("agency"), "Environment", case.get("environment")),
        ("Scene Size", case.get("scene_size"), "Report Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            c = meta.cell(i, j)
            _cell_text(c, value, bold=(j % 2 == 0), color=WHITE if j % 2 == 0 else "243447")
            if j % 2 == 0:
                _shade(c, BLUE)
            else:
                _shade(c, PALE)

    doc.add_paragraph()

    _add_heading(doc, "1. Scene Intake", 1)
    p = doc.add_paragraph(case.get("description") or "No investigator narrative supplied.")
    p.paragraph_format.space_after = Pt(6)

    _add_heading(doc, "2. Multimodal Image Record", 1)
    if not vision_records:
        doc.add_paragraph("No scene images were uploaded for this report.")
    else:
        for rec in vision_records:
            meta_i = rec.get("metadata", {})
            ana = rec.get("analysis", {})
            img_id = rec.get("image_id", "IMG")
            h = doc.add_paragraph()
            rr = h.add_run(f"{img_id} — {meta_i.get('filename','image')}")
            rr.bold = True; rr.font.color.rgb = RGBColor.from_string(BLUE)

            image_bytes = rec.get("image_bytes")
            if image_bytes:
                try:
                    stream = io.BytesIO(image_bytes)
                    # Re-save to standard RGB JPEG/PNG stream for robust Word embedding.
                    with Image.open(stream) as im:
                        im = im.convert("RGB")
                        converted = io.BytesIO()
                        im.save(converted, format="JPEG", quality=88)
                        converted.seek(0)
                        pic_p = doc.add_paragraph()
                        pic_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                        pic_p.add_run().add_picture(converted, width=Inches(5.8))
                except Exception as exc:
                    doc.add_paragraph(f"[Image could not be embedded: {exc}]")

            t = doc.add_table(rows=2, cols=4)
            t.style = "Table Grid"
            vals = [
                ("Dimensions", f"{meta_i.get('width','')} × {meta_i.get('height','')}"),
                ("Format", meta_i.get("format","")),
                ("SHA-256", meta_i.get("sha256","")[:24] + "…"),
                ("Bytes", f"{meta_i.get('bytes',0):,}"),
            ]
            for col, (k, v) in enumerate(vals):
                _cell_text(t.cell(0, col), k, bold=True, color=WHITE, size=8)
                _shade(t.cell(0, col), BLUE)
                _cell_text(t.cell(1, col), v, size=8)
                _shade(t.cell(1, col), PALE)

            p = doc.add_paragraph()
            p.add_run("AI visual summary: ").bold = True
            p.add_run(ana.get("image_summary", ""))
            proposals = ana.get("potential_observations", [])
            if proposals:
                p = doc.add_paragraph()
                p.add_run("AI-proposed observations (not laboratory findings):").bold = True
                for obs in proposals:
                    _add_bullet(
                        doc,
                        f"{obs.get('observation','')} — confidence: {obs.get('confidence','unspecified')} "
                        f"— category: {obs.get('possible_category','other')}"
                    )
            if ana.get("limitations"):
                p = doc.add_paragraph()
                p.add_run("Image-analysis limitations: ").bold = True
                p.add_run("; ".join(ana.get("limitations", [])))

    _add_heading(doc, "3. Investigator-Verified Visual Observations", 1)
    if verified_visuals:
        for item in verified_visuals:
            _add_bullet(doc, item)
    else:
        doc.add_paragraph("No AI-proposed visual observations were marked as investigator-verified.")

    _add_heading(doc, "4. Scene Analysis Agent", 1)
    analysis = analysis or {}
    p = doc.add_paragraph(analysis.get("scene_summary", "No scene-agent analysis generated."))
    if analysis.get("visual_context_summary"):
        p = doc.add_paragraph()
        p.add_run("Visual context: ").bold = True
        p.add_run(analysis["visual_context_summary"])
    if analysis.get("hazards"):
        _add_heading(doc, "Potential Hazards / Cautions", 2)
        for item in analysis["hazards"]:
            _add_bullet(doc, item)
    if analysis.get("immediate_documentation_priorities"):
        _add_heading(doc, "Immediate Documentation Priorities", 2)
        for item in analysis["immediate_documentation_priorities"]:
            _add_bullet(doc, item)
    if analysis.get("limitations"):
        _add_heading(doc, "Analysis Limitations", 2)
        for item in analysis["limitations"]:
            _add_bullet(doc, item)

    _add_heading(doc, "5. Evidence Inventory & Integrity", 1)
    if evidence_df is not None and not evidence_df.empty:
        cols = ["Evidence ID", "Item", "Category", "Location", "Basis", "Photographed", "Packaging Recorded", "Seal Recorded", "Custody Started"]
        cols = [c for c in cols if c in evidence_df.columns]
        tbl = doc.add_table(rows=1, cols=len(cols))
        tbl.style = "Table Grid"
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, c in enumerate(cols):
            _cell_text(tbl.cell(0,j), c, bold=True, color=WHITE, size=7.5)
            _shade(tbl.cell(0,j), NAVY)
        for _, row in evidence_df.iterrows():
            cells = tbl.add_row().cells
            for j, c in enumerate(cols):
                val = row[c]
                if isinstance(val, bool):
                    val = "Yes" if val else "No"
                _cell_text(cells[j], val, size=7.5)
        p = doc.add_paragraph()
        r = p.add_run(f"Documentation completeness: {integrity_score}%")
        r.bold = True; r.font.color.rgb = RGBColor.from_string(BLUE)
        if integrity_alerts:
            for a in integrity_alerts:
                _add_bullet(doc, a)
    else:
        doc.add_paragraph("No evidence inventory is currently recorded.")

    _add_heading(doc, "6. Recommended Crime Scene Search Strategy", 1)
    if search_plan:
        t = doc.add_table(rows=4, cols=2)
        t.style = "Table Grid"
        entries = [
            ("Recommended method", search_plan.get("recommended","")),
            ("Alternative method", search_plan.get("alternative","")),
            ("Rationale", search_plan.get("rationale","")),
            ("Operational caution", search_plan.get("caution","")),
        ]
        for i, (k,v) in enumerate(entries):
            _cell_text(t.cell(i,0), k, bold=True, color=WHITE)
            _shade(t.cell(i,0), BLUE)
            _cell_text(t.cell(i,1), v)
    else:
        doc.add_paragraph("No search-method recommendation has been generated.")

    _add_heading(doc, "7. Scene of Crime Map", 1)
    if scene_map_png:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(io.BytesIO(scene_map_png), width=Inches(6.7))
        c = doc.add_paragraph("Figure: Investigator-entered schematic scene map. North is fixed at the top.")
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER
        c.runs[0].italic = True
        c.runs[0].font.size = Pt(8)
        c.runs[0].font.color.rgb = RGBColor.from_string(GREY)
    else:
        doc.add_paragraph("No scene map was generated.")

    _add_heading(doc, "8. Source-Grounded Forensic Guidance", 1)
    if guidance:
        for typ, text in _clean_markdown(guidance):
            if typ == "heading1": _add_heading(doc, text, 2)
            elif typ in {"heading2","heading3"}: _add_heading(doc, text, 3)
            elif typ == "bullet": _add_bullet(doc, text)
            else: doc.add_paragraph(text)
    else:
        doc.add_paragraph("No RAG guidance has been generated.")

    _add_heading(doc, "9. Investigator Notes", 1)
    doc.add_paragraph(investigator_notes or "No additional investigator notes recorded.")

    _add_heading(doc, "10. Source References", 1)
    if sources:
        for i, s in enumerate(sources, start=1):
            p = doc.add_paragraph()
            rr = p.add_run(f"[S{i}] {s.get('title','Untitled source')}")
            rr.bold = True; rr.font.color.rgb = RGBColor.from_string(BLUE)
            detail = (
                f"Agency: {s.get('agency','')} | Type: {s.get('document_type','')} | "
                f"Page: {s.get('page') or 'N/A'} | Verification: {s.get('verification','')}"
            )
            doc.add_paragraph(detail)
            if s.get("url"):
                doc.add_paragraph(s.get("url"))
    else:
        doc.add_paragraph("No retrieved sources are attached to this report.")

    _add_heading(doc, "11. Disclaimer & Human Review", 1)
    p = doc.add_paragraph()
    r = p.add_run(
        "This document is an AI-assisted forensic documentation draft. Image analysis and model-generated "
        "observations are not laboratory findings and do not establish identity, guilt, cause, substance, "
        "source attribution or scientific confirmation. Investigator verification, applicable law, agency "
        "SOPs, laboratory examination and chain-of-custody requirements remain controlling."
    )
    r.font.color.rgb = RGBColor.from_string(RED)

    # Footer
    for section in doc.sections:
        fp = section.footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        fr = fp.add_run("MORBIT • Agentic Crime Scene Intelligence & Evidence Integrity Assistant")
        fr.font.size = Pt(8)
        fr.font.color.rgb = RGBColor.from_string(GREY)

    output = io.BytesIO()
    doc.save(output)
    return output.getvalue()
