"""risk_engine/hybrid.py — Hybrid NEWS2 + Keras decision engine."""
from risk_engine.rules    import compute_rule_score, score_to_risk
from risk_engine.ml_model import load_keras_model, load_scaler, predict, shap_explanation

_RISK_ORDER = {"Low": 0, "Medium": 1, "High": 2}
_RECS = {
    "Low":    "Continue routine self-monitoring. Reassess if new symptoms develop.",
    "Medium": "Increase monitoring frequency and contact your care team within 24 hours.",
    "High":   "Seek urgent clinical attention immediately. Contact your doctor or emergency services.",
}


def run_full_assessment(vitals: dict) -> dict:
    rule_score, abnormals = compute_rule_score(vitals)
    rule_risk             = score_to_risk(rule_score)

    model  = load_keras_model()
    scaler = load_scaler()
    ml_risk, ml_conf, ml_probs = (None, None, None)
    if model:
        ml_risk, ml_conf, ml_probs = predict(vitals, model, scaler)

    # Higher risk wins
    final_risk = rule_risk
    if ml_risk and _RISK_ORDER.get(ml_risk, 0) > _RISK_ORDER[rule_risk]:
        final_risk = ml_risk

    shap_feats = shap_explanation(vitals, model, scaler) if model else []

    return {
        "rule_score":     rule_score,
        "rule_risk":      rule_risk,
        "abnormals":      abnormals,
        "ml_prediction":  ml_risk  or "N/A",
        "ml_probability": ml_conf  or 0.0,
        "ml_class_probs": ml_probs or [],
        "final_risk":     final_risk,
        "recommendation": _RECS[final_risk],
        "shap_features":  shap_feats,
    }
