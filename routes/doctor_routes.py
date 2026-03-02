"""routes/doctor_routes.py — Doctor dashboard and review."""
import json
from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth import role_required, get_current_user, log_action
from database import get_db, Patient, Assessment, DoctorNote, User

doctor_bp = Blueprint("doctor", __name__)


@doctor_bp.route("/doctor")
@role_required("doctor", "admin")
def dashboard():
    user = get_current_user()
    with get_db() as db:
        all_assessments = (db.query(Assessment)
                           .order_by(Assessment.created_at.desc()).all())
        pending = [a for a in all_assessments if a.status == "pending"]
        rc = {"Low":0,"Medium":0,"High":0}
        for a in all_assessments:
            rc[a.final_risk] = rc.get(a.final_risk,0) + 1

        pending_data = []
        for a in pending:
            pat  = db.query(Patient).filter(Patient.id == a.patient_id).first()
            puser = db.query(User).filter(User.id == pat.user_id).first() if pat else None
            pending_data.append({
                "id": a.id, "patient_name": puser.name if puser else "Unknown",
                "final_risk": a.final_risk, "rule_score": a.rule_score,
                "ml_prediction": a.ml_prediction,
                "ml_probability": a.ml_probability or 0.0,
                "respiratory_rate": a.respiratory_rate,
                "oxygen_saturation": a.oxygen_saturation,
                "systolic_bp": a.systolic_bp, "heart_rate": a.heart_rate,
                "temperature": a.temperature, "on_oxygen": a.on_oxygen,
                "consciousness": a.consciousness,
                "explanation": a.explanation, "recommendation": a.recommendation,
                "created_at": a.created_at.strftime("%b %d, %Y %H:%M") if a.created_at else "N/A",
            })

        all_patients = db.query(Patient).all()
        patients_data = []
        for p in all_patients:
            pu   = db.query(User).filter(User.id == p.user_id).first()
            pasm = (db.query(Assessment).filter(Assessment.patient_id == p.id)
                    .order_by(Assessment.created_at.desc()).all())
            lr   = pasm[0].final_risk if pasm else "No data"
            patients_data.append({
                "name": pu.name if pu else "Unknown",
                "email": pu.email if pu else "",
                "age": p.age, "gender": p.gender,
                "conditions": p.underlying_conditions,
                "latest_risk": lr, "total": len(pasm),
            })

    return render_template("doctor_dashboard.html",
        user=user, pending=pending_data, patients=patients_data,
        risk_counts=rc, total_assessments=len(all_assessments),
    )


@doctor_bp.route("/doctor/review/<int:assessment_id>", methods=["POST"])
@role_required("doctor", "admin")
def review(assessment_id):
    user = get_current_user()
    note_text = request.form.get("note", "").strip()
    if not note_text:
        flash("Please enter a clinical note.", "warning")
        return redirect(url_for("doctor.dashboard"))

    with get_db() as db:
        a = db.query(Assessment).filter(Assessment.id == assessment_id).first()
        if not a:
            flash("Assessment not found.", "danger")
            return redirect(url_for("doctor.dashboard"))
        db.add(DoctorNote(assessment_id=a.id, doctor_id=user["id"], note=note_text))
        a.status = "reviewed"
        db.commit()
        log_action(user["id"], "REVIEW_ASSESSMENT", f"Reviewed #{assessment_id}")

    flash("Assessment reviewed and note submitted.", "success")
    return redirect(url_for("doctor.dashboard"))
