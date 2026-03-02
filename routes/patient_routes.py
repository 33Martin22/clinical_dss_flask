"""routes/patient_routes.py — Patient dashboard and assessment submission."""
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response
from auth import login_required, get_current_user, log_action
from database import get_db, Patient, Assessment, DoctorNote, User
from risk_engine.hybrid import run_full_assessment
from config import CLINICAL_LIMITS, CLINICAL_WARNINGS
from pdf_utils import generate_pdf

patient_bp = Blueprint("patient", __name__)


def _validate(vitals):
    errors, warnings = [], []
    for field, (lo, hi) in CLINICAL_LIMITS.items():
        v = vitals.get(field)
        if v is not None and not (lo <= v <= hi):
            errors.append(f"{field.replace('_',' ').title()} = {v} is outside possible range ({lo}–{hi}).")
    for field, (lo, hi) in CLINICAL_WARNINGS.items():
        v = vitals.get(field)
        if v is not None and not (lo <= v <= hi):
            warnings.append(f"{field.replace('_',' ').title()} ({v}) is outside normal range ({lo}–{hi}).")
    return errors, warnings


@patient_bp.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    with get_db() as db:
        patient = db.query(Patient).filter(Patient.user_id == user["id"]).first()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("main.landing"))

        assessments = (db.query(Assessment)
                       .filter(Assessment.patient_id == patient.id)
                       .order_by(Assessment.created_at.desc()).all())

        latest      = assessments[0] if assessments else None
        latest_notes = []
        if latest:
            latest_notes = (db.query(DoctorNote, User)
                            .join(User, DoctorNote.doctor_id == User.id)
                            .filter(DoctorNote.assessment_id == latest.id).all())

        risk_counts = {"Low": 0, "Medium": 0, "High": 0}
        trend_dates, trend_risks = [], []
        for a in assessments:
            risk_counts[a.final_risk] = risk_counts.get(a.final_risk, 0) + 1
            if a.created_at:
                trend_dates.append(a.created_at.strftime("%b %d"))
                trend_risks.append({"Low":1,"Medium":2,"High":3}.get(a.final_risk, 0))

        # snapshot before session closes
        pat_data = {
            "id": patient.id, "age": patient.age,
            "gender": patient.gender, "conditions": patient.underlying_conditions
        }
        latest_data = None
        if latest:
            latest_data = {
                "id": latest.id, "final_risk": latest.final_risk,
                "rule_score": latest.rule_score, "ml_prediction": latest.ml_prediction,
                "ml_probability": latest.ml_probability or 0.0,
                "explanation": latest.explanation, "recommendation": latest.recommendation,
                "status": latest.status,
                "respiratory_rate": latest.respiratory_rate,
                "oxygen_saturation": latest.oxygen_saturation,
                "systolic_bp": latest.systolic_bp, "heart_rate": latest.heart_rate,
                "temperature": latest.temperature,
                "created_at": latest.created_at.strftime("%B %d, %Y at %H:%M") if latest.created_at else "N/A",
            }
        notes_data = [{"doctor": doc.name,
                       "date": note.created_at.strftime("%b %d, %Y") if note.created_at else "",
                       "note": note.note} for note, doc in latest_notes]

        history = []
        for a in assessments:
            history.append({
                "id": a.id, "final_risk": a.final_risk, "rule_score": a.rule_score,
                "ml_prediction": a.ml_prediction, "status": a.status,
                "created_at": a.created_at.strftime("%b %d, %Y %H:%M") if a.created_at else "N/A",
                "recommendation": a.recommendation,
            })

    return render_template("patient_dashboard.html",
        user=user, pat=pat_data, latest=latest_data,
        notes=notes_data, history=history,
        risk_counts=risk_counts,
        trend_dates=json.dumps(trend_dates),
        trend_risks=json.dumps(trend_risks),
        total=len(assessments),
        pending=sum(1 for a in history if a["status"]=="pending"),
    )


@patient_bp.route("/assessment", methods=["GET", "POST"])
@login_required
def assessment():
    user   = get_current_user()
    result = None
    errors, warnings = [], []

    with get_db() as db:
        patient = db.query(Patient).filter(Patient.user_id == user["id"]).first()
        if not patient:
            flash("Patient profile not found.", "danger")
            return redirect(url_for("main.landing"))
        patient_id = patient.id

    if request.method == "POST":
        try:
            vitals = {
                "respiratory_rate":  int(request.form["respiratory_rate"]),
                "oxygen_saturation": int(request.form["oxygen_saturation"]),
                "o2_scale":          int(request.form["o2_scale"]),
                "systolic_bp":       int(request.form["systolic_bp"]),
                "heart_rate":        int(request.form["heart_rate"]),
                "temperature":       float(request.form["temperature"]),
                "consciousness":     request.form["consciousness"],
                "on_oxygen":         1 if request.form.get("on_oxygen") else 0,
            }
        except (ValueError, KeyError) as e:
            errors = [f"Invalid input: {e}"]
            return render_template("assessment.html", user=user,
                                   errors=errors, warnings=[], result=None)

        errors, warnings = _validate(vitals)
        if not errors:
            result = run_full_assessment(vitals)
            with get_db() as db:
                a = Assessment(
                    patient_id=patient_id,
                    respiratory_rate=vitals["respiratory_rate"],
                    oxygen_saturation=vitals["oxygen_saturation"],
                    o2_scale=vitals["o2_scale"],
                    systolic_bp=vitals["systolic_bp"],
                    heart_rate=vitals["heart_rate"],
                    temperature=vitals["temperature"],
                    consciousness=vitals["consciousness"],
                    on_oxygen=vitals["on_oxygen"],
                    rule_score=result["rule_score"],
                    ml_prediction=result["ml_prediction"],
                    ml_probability=result["ml_probability"],
                    final_risk=result["final_risk"],
                    explanation="\n".join(
                        ["Abnormal vitals: " + "; ".join(result["abnormals"])] +
                        [f"NEWS2 Score: {result['rule_score']} → {result['rule_risk']}",
                         f"AI: {result['ml_prediction']} ({result['ml_probability']:.1%})",
                         f"Final: {result['final_risk']}"]
                    ) if result.get("abnormals") else f"NEWS2 Score: {result['rule_score']} — all vitals normal",
                    recommendation=result["recommendation"],
                    status="pending",
                )
                db.add(a)
                db.commit()
                result["assessment_id"] = a.id
                log_action(user["id"], "SUBMIT_ASSESSMENT",
                           f"Assessment #{a.id} — Final: {result['final_risk']}")

    return render_template("assessment.html", user=user,
                           errors=errors, warnings=warnings, result=result)


@patient_bp.route("/download-pdf/<int:assessment_id>")
@login_required
def download_pdf(assessment_id):
    user = get_current_user()
    with get_db() as db:
        a       = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        patient = db.query(Patient).filter(Patient.user_id == user["id"]).first()
        if not a or not patient or a.patient_id != patient.id:
            flash("Assessment not found.", "danger")
            return redirect(url_for("patient.dashboard"))

        notes = (db.query(DoctorNote, User).join(User, DoctorNote.doctor_id == User.id)
                 .filter(DoctorNote.assessment_id == a.id).all())

        pdf_bytes = generate_pdf(
            patient_info={"name": user["name"], "email": user["email"],
                          "age": patient.age, "gender": patient.gender,
                          "conditions": patient.underlying_conditions},
            assessment={
                "id": a.id, "final_risk": a.final_risk, "rule_score": a.rule_score,
                "ml_prediction": a.ml_prediction, "ml_probability": a.ml_probability or 0.0,
                "respiratory_rate": a.respiratory_rate, "oxygen_saturation": a.oxygen_saturation,
                "o2_scale": a.o2_scale, "systolic_bp": a.systolic_bp, "heart_rate": a.heart_rate,
                "temperature": a.temperature, "consciousness": a.consciousness,
                "on_oxygen": a.on_oxygen, "explanation": a.explanation,
                "recommendation": a.recommendation,
            },
            doctor_notes=[{"doctor_name": doc.name,
                           "date": note.created_at.strftime("%b %d, %Y") if note.created_at else "",
                           "note": note.note} for note, doc in notes],
        )

    return Response(pdf_bytes, mimetype="application/pdf",
                    headers={"Content-Disposition":
                             f"attachment; filename=assessment_{assessment_id}.pdf"})
