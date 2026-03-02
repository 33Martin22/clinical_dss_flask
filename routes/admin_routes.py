"""routes/admin_routes.py — Admin dashboard."""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from auth import role_required, get_current_user, log_action
from database import get_db, User, Patient, Assessment, AuditLog

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/admin")
@role_required("admin")
def dashboard():
    user = get_current_user()
    with get_db() as db:
        all_users = db.query(User).order_by(User.created_at.desc()).all()
        all_asms  = db.query(Assessment).all()
        logs      = (db.query(AuditLog).order_by(AuditLog.timestamp.desc())
                     .limit(100).all())

        rc = {"Low":0,"Medium":0,"High":0}
        for a in all_asms:
            rc[a.final_risk] = rc.get(a.final_risk, 0) + 1

        users_data = []
        for u in all_users:
            created = u.created_at.strftime("%b %d, %Y") if u.created_at else "N/A"
            users_data.append({
                "id": u.id, "name": u.name, "email": u.email,
                "role": u.role, "is_active": u.is_active, "created_at": created,
            })

        logs_data = []
        for lg in logs:
            lu = db.query(User).filter(User.id == lg.user_id).first()
            logs_data.append({
                "time":    lg.timestamp.strftime("%b %d, %Y %H:%M") if lg.timestamp else "N/A",
                "user":    lu.name if lu else "System",
                "role":    lu.role.title() if lu else "—",
                "action":  lg.action,
                "details": (lg.details or "")[:120],
            })

    return render_template("admin_dashboard.html",
        user=user, users=users_data, risk_counts=rc,
        total_assessments=len(all_asms), logs=logs_data,
        patients_count=sum(1 for u in users_data if u["role"]=="patient"),
        doctors_count=sum(1 for u in users_data if u["role"]=="doctor"),
    )


@admin_bp.route("/admin/toggle/<int:user_id>", methods=["POST"])
@role_required("admin")
def toggle_user(user_id):
    current = get_current_user()
    if user_id == current["id"]:
        flash("You cannot deactivate your own account.", "warning")
        return redirect(url_for("admin.dashboard"))
    with get_db() as db:
        u = db.query(User).filter(User.id == user_id).first()
        if u:
            u.is_active = not u.is_active
            db.commit()
            action = "ACTIVATE_USER" if u.is_active else "DEACTIVATE_USER"
            log_action(current["id"], action, u.email)
            flash(f"{'Activated' if u.is_active else 'Deactivated'}: {u.email}", "success")
    return redirect(url_for("admin.dashboard"))
