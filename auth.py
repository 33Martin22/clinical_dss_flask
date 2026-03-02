"""
auth.py — Authentication, Flask session management, seeding.
Uses Flask's session (server-side cookie) instead of Streamlit session_state.
"""
import logging
from functools import wraps
from flask import session, redirect, url_for, flash
import bcrypt as _bcrypt
from database import get_db, User, Patient, AuditLog


log  = logging.getLogger(__name__)
_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ──────────────────────────────────────────────────────────


def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── Login / Register ──────────────────────────────────────────────────────────

def login_user(email: str, password: str):
    with get_db() as db:
        u = db.query(User).filter(User.email == email.lower().strip()).first()
        if not u:
            return None, "No account found with that email address."
        if not u.is_active:
            return None, "This account has been deactivated."
        if not verify_password(password, u.password_hash):
            return None, "Incorrect password."
        _audit(db, u.id, "LOGIN", f"{u.email} signed in.")
        return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}, None


def register_user(name, email, password, role="patient",
                  age=None, gender=None, conditions=None):
    with get_db() as db:
        if db.query(User).filter(User.email == email.lower().strip()).first():
            return None, "That email address is already registered."
        u = User(name=name.strip(), email=email.lower().strip(),
                 password_hash=hash_password(password), role=role)
        db.add(u)
        db.flush()
        if role == "patient":
            db.add(Patient(user_id=u.id, age=age, gender=gender,
                           underlying_conditions=conditions))
        db.commit()
        _audit(db, u.id, "REGISTER", f"New {role}: {u.email}")
        return {"id": u.id, "name": u.name, "email": u.email, "role": u.role}, None


# ── Flask session helpers ─────────────────────────────────────────────────────

def set_session(user_dict: dict):
    session["user_id"]    = user_dict["id"]
    session["user_name"]  = user_dict["name"]
    session["user_email"] = user_dict["email"]
    session["user_role"]  = user_dict["role"]
    session.permanent     = True


def clear_session():
    session.clear()


def get_current_user() -> dict | None:
    if "user_id" not in session:
        return None
    return {
        "id":    session["user_id"],
        "name":  session["user_name"],
        "email": session["user_email"],
        "role":  session["user_role"],
    }


# ── Route decorators ──────────────────────────────────────────────────────────

def login_required(f):
    """Redirect to /login if not authenticated."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not get_current_user():
            flash("Please log in to access that page.", "warning")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


def role_required(*roles):
    """Redirect to home if user does not have required role."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash("Please log in.", "warning")
                return redirect(url_for("auth.login"))
            if user["role"] not in roles:
                flash("Access denied — insufficient permissions.", "danger")
                return redirect(url_for("main.landing"))
            return f(*args, **kwargs)
        return decorated
    return decorator


# ── Audit ─────────────────────────────────────────────────────────────────────

def log_action(user_id: int, action: str, details: str = ""):
    try:
        with get_db() as db:
            db.add(AuditLog(user_id=user_id, action=action, details=details))
            db.commit()
    except Exception as e:
        log.error(f"Audit failed: {e}")


def _audit(db, user_id, action, details=""):
    try:
        db.add(AuditLog(user_id=user_id, action=action, details=details))
        db.commit()
    except Exception:
        pass


# ── Seeding ───────────────────────────────────────────────────────────────────

def seed_defaults():
    with get_db() as db:
        if db.query(User).filter(User.role == "admin").first():
            return
        db.add(User(name="System Administrator", email="admin@clinic.com",
                    password_hash=hash_password("Admin@1234"), role="admin"))
        db.add(User(name="Dr. Sarah Johnson", email="doctor@clinic.com",
                    password_hash=hash_password("Doctor@1234"), role="doctor"))
        db.commit()
        log.info("Default accounts seeded.")
