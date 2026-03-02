"""risk_engine/ml_model.py — Keras model loading, prediction, SHAP."""
import os, pickle, logging
import numpy as np
from config import MODEL_PATH, SCALER_PATH, ML_CLASS_LABELS, MODEL_FEATURE_COUNT

log = logging.getLogger(__name__)

_DATA_MIN = np.array([12.,  74., 1.,  50.,  64., 35.6])
_DATA_MAX = np.array([40., 100., 2., 144., 163., 41.8])

FEATURE_NAMES = [
    "Respiratory Rate", "Oxygen Saturation", "O2 Scale",
    "Systolic BP", "Heart Rate", "Temperature",
    "Consciousness (C)", "Consciousness (P)",
    "Consciousness (U)", "Consciousness (V)", "On Oxygen",
]

_model  = None
_scaler = None


def load_keras_model():
    global _model
    if _model is not None:
        return _model
    try:
        os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")
        import tensorflow as tf
        _model = tf.keras.models.load_model(MODEL_PATH, compile=False)
        log.info("Keras model loaded.")
        return _model
    except Exception as e:
        log.error(f"Model load failed: {e}")
        return None


def load_scaler():
    global _scaler
    if _scaler is not None:
        return _scaler
    try:
        with open(SCALER_PATH, "rb") as f:
            _scaler = pickle.load(f)
        return _scaler
    except Exception as e:
        log.error(f"Scaler load failed: {e}")
        return None


def build_feature_vector(vitals: dict, scaler) -> np.ndarray:
    cons = str(vitals.get("consciousness", "A")).upper()
    numeric = np.array([[
        vitals["respiratory_rate"], vitals["oxygen_saturation"],
        vitals["o2_scale"],         vitals["systolic_bp"],
        vitals["heart_rate"],       vitals["temperature"],
    ]], dtype=float)

    if scaler is not None:
        try:
            scaled = scaler.transform(numeric)[0]
        except Exception:
            scaled = np.clip((numeric[0] - _DATA_MIN) / (_DATA_MAX - _DATA_MIN + 1e-8), 0, 1)
    else:
        scaled = np.clip((numeric[0] - _DATA_MIN) / (_DATA_MAX - _DATA_MIN + 1e-8), 0, 1)

    ohe = [1 if cons=="C" else 0, 1 if cons=="P" else 0,
           1 if cons=="U" else 0, 1 if cons=="V" else 0]
    vec = np.concatenate([scaled, ohe, [int(vitals.get("on_oxygen", 0))]]).astype(np.float32)
    return vec.reshape(1, -1)


def predict(vitals: dict, model, scaler):
    try:
        x     = build_feature_vector(vitals, scaler)
        probs = model.predict(x, verbose=0)[0]
        idx   = int(np.argmax(probs))
        return ML_CLASS_LABELS.get(idx, "Low"), float(probs[idx]), probs.tolist()
    except Exception as e:
        log.error(f"Prediction failed: {e}")
        return None, None, None


def shap_explanation(vitals, model, scaler, top_n=4):
    try:
        import shap
        x          = build_feature_vector(vitals, scaler)
        background = np.zeros((1, MODEL_FEATURE_COUNT), dtype=np.float32)
        explainer  = shap.GradientExplainer(model, background)
        shap_vals  = explainer.shap_values(x)
        if isinstance(shap_vals, list):
            importance = np.abs(np.array(shap_vals)).mean(axis=0)[0]
        else:
            importance = np.abs(shap_vals[0])
        top_idx = np.argsort(importance)[::-1][:top_n]
        return [(FEATURE_NAMES[i], float(importance[i])) for i in top_idx]
    except Exception as e:
        log.warning(f"SHAP unavailable: {e}")
        return []
