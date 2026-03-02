"""
config.py — All application settings from environment variables.
Locally: reads from .env file via python-dotenv
Production (Render): reads from Render environment variables panel
"""
import os
from dotenv import load_dotenv

load_dotenv()  # loads .env file if present (local dev only)

# ── Database ─────────────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "")

# Render injects postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY    = os.environ.get("SECRET_KEY", "dev-only-key-change-in-production")
BCRYPT_ROUNDS = 12

# ── App ───────────────────────────────────────────────────────────────────────
APP_NAME    = "AI Clinical Decision Support System"
APP_VERSION = "3.0.0"
DEBUG       = os.environ.get("FLASK_DEBUG", "false").lower() == "true"

# ── Model paths ───────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH  = os.path.join(BASE_DIR, "models", "risk_model.h5")
SCALER_PATH = os.path.join(BASE_DIR, "models", "scaler.pkl")

# ── Risk engine constants ─────────────────────────────────────────────────────
ML_CLASS_LABELS     = {0: "High", 1: "Low", 2: "Medium"}
MODEL_FEATURE_COUNT = 11

# ── Clinical validation limits (hard block) ───────────────────────────────────
CLINICAL_LIMITS = {
    "respiratory_rate":  (1,    70),
    "oxygen_saturation": (50,  100),
    "systolic_bp":       (50,  300),
    "heart_rate":        (20,  250),
    "temperature":       (30.0, 44.0),
}

# ── Clinical warning thresholds (soft warn) ───────────────────────────────────
CLINICAL_WARNINGS = {
    "respiratory_rate":  (8,   30),
    "oxygen_saturation": (85, 100),
    "systolic_bp":       (80, 220),
    "heart_rate":        (40, 180),
    "temperature":       (35.0, 40.5),
}
