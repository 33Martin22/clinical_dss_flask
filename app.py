"""
app.py — Flask application entry point.

Local:      python app.py   OR   flask run
Render.com: gunicorn app:app
"""
from flask import Flask, render_template, redirect, url_for
from datetime import timedelta

from config   import SECRET_KEY, DEBUG
from database import init_db
from auth     import seed_defaults, get_current_user

from routes.auth_routes    import auth_bp
from routes.patient_routes import patient_bp
from routes.doctor_routes  import doctor_bp
from routes.admin_routes   import admin_bp

app = Flask(__name__)
app.secret_key              = SECRET_KEY
app.permanent_session_lifetime = timedelta(hours=8)

# Register blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(patient_bp)
app.register_blueprint(doctor_bp)
app.register_blueprint(admin_bp)


# ── Startup ───────────────────────────────────────────────────────────────────
with app.app_context():
    init_db()
    seed_defaults()


# ── Main route ────────────────────────────────────────────────────────────────
@app.route("/")
def landing():
    user = get_current_user()
    return render_template("landing.html", user=user)


# Blueprint alias for url_for("main.landing")
app.add_url_rule("/", endpoint="main.landing", view_func=landing)


# ── Error handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404,
                           message="Page not found."), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("error.html", code=500,
                           message="Internal server error."), 500


# ── Context processor — injects user into every template ──────────────────────
@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


if __name__ == "__main__":
    app.run(debug=DEBUG, host="0.0.0.0", port=5000)
