"""pdf_utils.py — Clinical PDF report generation with ReportLab."""
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

_RC = {"Low": colors.HexColor("#16a34a"), "Medium": colors.HexColor("#d97706"), "High": colors.HexColor("#dc2626")}
_RBG = {"Low": colors.HexColor("#dcfce7"), "Medium": colors.HexColor("#fef3c7"), "High": colors.HexColor("#fee2e2")}


def generate_pdf(patient_info, assessment, doctor_notes=None):
    buf  = BytesIO()
    doc  = SimpleDocTemplate(buf, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    def sec(text):
        return Paragraph(text, ParagraphStyle("Sec", parent=styles["Heading2"],
                         textColor=colors.HexColor("#1e1b4b"), fontSize=12, spaceAfter=6))

    def body(text):
        return Paragraph(text, ParagraphStyle("Body", parent=styles["Normal"],
                         fontSize=9, spaceAfter=4))

    # Header
    story.append(Paragraph("🏥 Clinical Assessment Report",
        ParagraphStyle("T", parent=styles["Title"], fontSize=20,
                       textColor=colors.HexColor("#1e1b4b"), alignment=TA_CENTER)))
    story.append(Paragraph(f"AI-Powered Hybrid Clinical DSS — Generated {datetime.now().strftime('%B %d, %Y at %H:%M')}",
        ParagraphStyle("S", parent=styles["Normal"], fontSize=9, textColor=colors.grey, alignment=TA_CENTER)))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e1b4b")))
    story.append(Spacer(1, 0.3*cm))

    # Risk badge
    risk = assessment.get("final_risk","Unknown")
    story.append(Paragraph(f"Final Risk: {risk.upper()}",
        ParagraphStyle("R", fontSize=18, alignment=TA_CENTER, fontName="Helvetica-Bold",
                       textColor=_RC.get(risk, colors.grey), spaceAfter=8)))

    # Patient info
    story.append(sec("Patient Information"))
    pt = Table([
        ["Name", patient_info.get("name","N/A"), "Age", str(patient_info.get("age","N/A"))],
        ["Email", patient_info.get("email","N/A"), "Gender", patient_info.get("gender","N/A")],
        ["Conditions", patient_info.get("conditions","None"), "Assessment #", str(assessment.get("id","N/A"))],
    ], colWidths=[3*cm, 7*cm, 2.5*cm, 4*cm])
    pt.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"), ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),9), ("PADDING",(0,0),(-1,-1),6),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.HexColor("#eef2ff"),colors.HexColor("#f5f3ff")]),
        ("GRID",(0,0),(-1,-1),0.5,colors.white),
    ]))
    story.append(pt); story.append(Spacer(1,0.3*cm))

    # Vitals
    story.append(sec("Vital Signs"))
    vt = Table([
        ["Parameter","Value","Parameter","Value"],
        ["Respiratory Rate",f"{assessment.get('respiratory_rate','N/A')} breaths/min","Heart Rate",f"{assessment.get('heart_rate','N/A')} bpm"],
        ["Oxygen Saturation",f"{assessment.get('oxygen_saturation','N/A')}%","Temperature",f"{assessment.get('temperature','N/A')} °C"],
        ["Systolic BP",f"{assessment.get('systolic_bp','N/A')} mmHg","On Oxygen","Yes" if assessment.get("on_oxygen") else "No"],
        ["Consciousness",assessment.get("consciousness","N/A"),"O2 Scale",f"Scale {assessment.get('o2_scale','N/A')}"],
    ], colWidths=[4*cm, 6*cm, 4*cm, 3*cm])
    vt.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1e1b4b")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white), ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f5f3ff")]),
        ("GRID",(0,0),(-1,-1),0.5,colors.HexColor("#dee2e6")),
        ("PADDING",(0,0),(-1,-1),7), ("FONTSIZE",(0,0),(-1,-1),9),
    ]))
    story.append(vt); story.append(Spacer(1,0.3*cm))

    # Engine summary
    story.append(sec("AI Engine Summary"))
    mp = assessment.get("ml_probability",0) or 0
    et = Table([
        ["NEWS2 Score", str(assessment.get("rule_score","N/A")), "AI Prediction", assessment.get("ml_prediction","N/A")],
        ["AI Confidence", f"{mp:.1%}", "Final Risk", risk],
    ], colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    et.setStyle(TableStyle([
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"), ("FONTNAME",(2,0),(2,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),9), ("PADDING",(0,0),(-1,-1),7),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.HexColor("#eef2ff"),colors.HexColor("#f5f3ff")]),
        ("GRID",(0,0),(-1,-1),0.5,colors.white),
    ]))
    story.append(et); story.append(Spacer(1,0.3*cm))

    # Recommendation
    story.append(sec("Clinical Recommendation"))
    rec_t = Table([[assessment.get("recommendation","")]])
    rec_t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),_RBG.get(risk,colors.white)),
        ("PADDING",(0,0),(-1,-1),10), ("FONTSIZE",(0,0),(-1,-1),10),
    ]))
    story.append(rec_t); story.append(Spacer(1,0.3*cm))

    # Doctor notes
    if doctor_notes:
        story.append(sec("Physician Review Notes"))
        for n in doctor_notes:
            story.append(body(f"<b>Dr. {n.get('doctor_name','')}</b> — {n.get('date','')}<br/>{n.get('note','')}"))
            story.append(Spacer(1,0.15*cm))

    # Footer
    story.append(Spacer(1,0.4*cm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    story.append(Paragraph(
        "⚠️ This report is AI-assisted. All findings must be confirmed by a licensed medical professional.",
        ParagraphStyle("F", parent=styles["Normal"], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))

    doc.build(story)
    return buf.getvalue()
