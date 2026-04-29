"""
optimizer.py — GBM Treatment Optimization Logic v3.0

Gompertz-based tumor growth simulation + stacking ensemble ML.
Merged from gbm_optimize_treatment_dosage_v3.py and
gbm_optimize_treatment_extended_dosage_v3.py.
"""

import os
import re
import json
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from joblib import load

warnings.filterwarnings("ignore", category=UserWarning, module="sklearn")

# ---------------------------------------------------------------------------
# Globals — populated by load_models()
# ---------------------------------------------------------------------------

MODEL_DIR = os.environ.get("MODEL_DIR", "gbm_models_output_all90_dosage_full_features")

_stacked_models = None
_enc = None
_scaler = None
_feature_columns: List[str] = []
_metadata: Dict[str, Any] = {}

BASELINE_R: float = 0.12
R_UNTREATED: float = 0.12
SIM_MONTHS: int = 12


def load_models() -> None:
    """Load all ML artefacts from MODEL_DIR. Call once at startup."""
    global _stacked_models, _enc, _scaler, _feature_columns, _metadata
    global BASELINE_R, R_UNTREATED

    _stacked_models = load(os.path.join(MODEL_DIR, "stacked_models.joblib"))
    _enc = load(os.path.join(MODEL_DIR, "onehot_encoder.joblib"))
    _scaler = load(os.path.join(MODEL_DIR, "scaler.joblib"))

    with open(os.path.join(MODEL_DIR, "feature_columns.json"), "r") as f:
        _feature_columns = json.load(f)

    with open(os.path.join(MODEL_DIR, "metadata.json"), "r") as f:
        _metadata = json.load(f)
        BASELINE_R = _metadata.get("baseline_r", BASELINE_R)
        R_UNTREATED = _metadata.get("r_untreated", R_UNTREATED)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def parse_treatment_flags(tstr: str) -> Dict[str, int]:
    t = str(tstr).lower() if tstr else ""
    flags = {
        "chemo":      int("temozolomide" in t or "tmz" in t or "chem" in t),
        "radio":      int("radiation" in t or "radiotherapy" in t or "rt" in t or "radiother" in t),
        "beva":       int("bevacizumab" in t or "beva" in t),
        "other_drug": int("lomustine" in t or "ccnu" in t or "carboplatin" in t
                          or "etoposide" in t or "irinotecan" in t),
        "drug_temozolomide": int("temozolomide" in t or "tmz" in t),
        "drug_lomustine":    int("lomustine" in t or "ccnu" in t),
        "drug_carboplatin":  int("carboplatin" in t),
        "drug_etoposide":    int("etoposide" in t),
        "drug_irinotecan":   int("irinotecan" in t),
        "drug_bevacizumab":  int("bevacizumab" in t or "beva" in t),
    }
    return flags


def _parse_dosage_from_string(tstr: str) -> Dict[str, float]:
    t = str(tstr).lower() if tstr else ""
    result = {"chemo_dose_mg_per_m2": 0.0, "radio_total_Gy": 0.0,
               "radio_fractions": 0.0, "radio_BED": 0.0}

    for pattern in [r"(\d+)\s*mg\s*/\s*m2", r"(\d+)\s*mg/m²",
                    r"temozolomide\s+(\d+)", r"tmz\s+(\d+)"]:
        m = re.search(pattern, t)
        if m:
            result["chemo_dose_mg_per_m2"] = float(m.group(1))
            break

    for pattern in [r"(\d+)\s*gy\s*/\s*(\d+)\s*fr",
                    r"(\d+)\s*gy\s*\/\s*(\d+)",
                    r"radiation\s+(\d+)\s*gy.*?(\d+)\s*fr"]:
        m = re.search(pattern, t)
        if m:
            result["radio_total_Gy"] = float(m.group(1))
            result["radio_fractions"] = float(m.group(2))
            break

    if result["radio_total_Gy"] > 0 and result["radio_fractions"] > 0:
        n, d = result["radio_fractions"], result["radio_total_Gy"] / result["radio_fractions"]
        result["radio_BED"] = n * d * (1 + d / 10.0)

    return result


def extract_dosages(patient: Dict[str, Any], treatment_string: str) -> Dict[str, float]:
    dosages = {"chemo_dose_mg_per_m2": 0.0, "radio_total_Gy": 0.0, "radio_BED": 0.0}

    if isinstance(patient.get("chemotherapy"), dict):
        dosages["chemo_dose_mg_per_m2"] = float(
            patient["chemotherapy"].get("dose_mg_per_m2", 0))

    if isinstance(patient.get("radiotherapy"), dict):
        rt = patient["radiotherapy"]
        total_Gy = float(rt.get("total_dose_Gy", 0))
        fractions = int(rt.get("fractions", 0))
        if total_Gy > 0:
            dosages["radio_total_Gy"] = total_Gy
            if fractions > 0:
                d = total_Gy / fractions
                dosages["radio_BED"] = fractions * d * (1 + d / 10.0)

    if dosages["chemo_dose_mg_per_m2"] == 0 or dosages["radio_total_Gy"] == 0:
        parsed = _parse_dosage_from_string(treatment_string)
        if dosages["chemo_dose_mg_per_m2"] == 0:
            dosages["chemo_dose_mg_per_m2"] = parsed["chemo_dose_mg_per_m2"]
        if dosages["radio_total_Gy"] == 0:
            dosages["radio_total_Gy"] = parsed["radio_total_Gy"]
            dosages["radio_BED"] = parsed["radio_BED"]

    flags = parse_treatment_flags(treatment_string)
    if flags["chemo"] and dosages["chemo_dose_mg_per_m2"] == 0:
        dosages["chemo_dose_mg_per_m2"] = 75.0
    if flags["radio"] and dosages["radio_total_Gy"] == 0:
        dosages["radio_total_Gy"] = 60.0
        dosages["radio_BED"] = 30 * 2.0 * (1 + 2.0 / 10.0)

    return dosages


def _parse_neurological_symptoms(patient: Dict[str, Any]) -> Dict[str, int]:
    s = str(patient.get("neurological_symptoms", "")).lower()
    symptoms = {
        "has_headache":          int(patient["has_headache"])          if "has_headache"          in patient else int("headache" in s),
        "has_motor_deficit":     int(patient["has_motor_deficit"])     if "has_motor_deficit"     in patient else int("motor_deficit" in s or "motor deficit" in s),
        "has_seizures":          int(patient["has_seizures"])          if "has_seizures"          in patient else int("seizure" in s),
        "has_sensory_deficit":   int(patient["has_sensory_deficit"])   if "has_sensory_deficit"   in patient else int("sensory_deficit" in s or "sensory deficit" in s),
        "has_cognitive_decline": int(patient["has_cognitive_decline"]) if "has_cognitive_decline" in patient else int("cognitive" in s),
        "has_speech_disturbance":int(patient["has_speech_disturbance"])if "has_speech_disturbance"in patient else int("speech" in s),
        "has_visual_disturbance":int(patient["has_visual_disturbance"])if "has_visual_disturbance"in patient else int("visual" in s),
    }
    if "symptom_count" in patient:
        symptoms["symptom_count"] = int(patient["symptom_count"])
    elif "asymptomatic" in s:
        symptoms["symptom_count"] = 0
    else:
        symptoms["symptom_count"] = sum(symptoms.values())
    return symptoms


# ---------------------------------------------------------------------------
# Feature vector
# ---------------------------------------------------------------------------

def build_feature_vector(
    patient: Dict[str, Any],
    treatment_string: str,
    dosages: Dict[str, float],
) -> pd.Series:
    flags = parse_treatment_flags(treatment_string)
    neuro = _parse_neurological_symptoms(patient)

    numeric: Dict[str, Any] = {
        "age":               float(patient.get("age", 50)),
        "tumor_size_before": float(patient.get("tumor_size_before", 3.0)),
        "kps":               float(patient.get("kps", 70)),
        "chemo":             flags["chemo"],
        "radio":             flags["radio"],
        "beva":              flags["beva"],
        "other_drug":        flags["other_drug"],
        "chemo_dose_mg_per_m2": dosages["chemo_dose_mg_per_m2"],
        "radio_total_Gy":       dosages["radio_total_Gy"],
        "radio_BED":            dosages["radio_BED"],
        "drug_temozolomide": flags["drug_temozolomide"],
        "drug_lomustine":    flags["drug_lomustine"],
        "drug_carboplatin":  flags["drug_carboplatin"],
        "drug_etoposide":    flags["drug_etoposide"],
        "drug_irinotecan":   flags["drug_irinotecan"],
        "drug_bevacizumab":  flags["drug_bevacizumab"],
        "mgmt_methylation":  int(patient.get("mgmt_methylation", 0)),
        "idh_mutation":      int(patient.get("idh_mutation", 0)),
        "egfr_amplification":int(patient.get("egfr_amplification", 0)),
        "tert_mutation":     int(patient.get("tert_mutation", 0)),
        "atrx_mutation":     int(patient.get("atrx_mutation", 0)),
        "edema_volume":      float(patient.get("edema_volume", 0)),
        "steroid_dose":      float(patient.get("steroid_dose", 0)),
        "antiseizure_meds":  int(patient.get("antiseizure_meds", 0)),
        **neuro,
        "family_history":    int(patient.get("family_history", 0)),
        "previous_radiation":int(patient.get("previous_radiation", 0)),
    }

    categorical = {
        "gender":             str(patient.get("gender", "M")),
        "resection_extent":   str(patient.get("resection_extent", "subtotal")),
        "molecular_subtype":  str(patient.get("molecular_subtype", "classical")),
        "tumor_location":     str(patient.get("tumor_location", "frontal_lobe")),
        "contrast_enhancement": str(patient.get("contrast_enhancement", "ring")),
        "stage":              str(patient.get("stage", "Stage 1")),
        "lateralization":     str(patient.get("lateralization", "left")),
        "rano_response":      str(patient.get("rano_response", "stable_disease")),
    }

    cat_df = pd.DataFrame([categorical])
    enc_arr = _enc.transform(cat_df)
    cat_names = ["gender", "resection_extent", "molecular_subtype",
                 "tumor_location", "contrast_enhancement", "stage",
                 "lateralization", "rano_response"]
    enc_cols = [f"{cat}_{v}" for i, cat in enumerate(cat_names)
                for v in _enc.categories_[i]]
    combined = {**numeric, **dict(zip(enc_cols, enc_arr[0]))}

    T0 = numeric["tumor_size_before"]
    combined["r_fit"]   = 0.0
    combined["K_fit"]   = T0 * 2.0
    combined["n_obs"]   = 5
    combined["alpha_computed"] = 0.05
    combined["beta_computed"]  = 0.03
    K = combined["K_fit"]

    combined["r_fit_x_chemo"]          = combined["r_fit"] * numeric["chemo"]
    combined["r_fit_x_radio"]          = combined["r_fit"] * numeric["radio"]
    combined["K_fit_x_chemo"]          = K * numeric["chemo"]
    combined["K_fit_x_radio"]          = K * numeric["radio"]
    combined["alpha_computed_x_chemo"] = combined["alpha_computed"] * numeric["chemo"]
    combined["beta_computed_x_radio"]  = combined["beta_computed"]  * numeric["radio"]
    combined["chemo_x_radio"]          = numeric["chemo"] * numeric["radio"]
    combined["chemo_x_tumor_size"]     = numeric["chemo"] * T0
    combined["radio_x_tumor_size"]     = numeric["radio"] * T0
    combined["beva_x_chemo"]           = numeric["beva"]  * numeric["chemo"]
    combined["kps_x_chemo"]            = numeric["kps"]   * numeric["chemo"]
    combined["treatment_count"]        = numeric["chemo"] + numeric["radio"] + numeric["beva"]

    cd = numeric["chemo_dose_mg_per_m2"]
    rb = numeric["radio_BED"]
    combined["chemo_dose_x_tumor_size"]  = cd * T0
    combined["chemo_dose_x_kps"]         = cd * numeric["kps"]
    combined["chemo_dose_x_age"]         = cd * numeric["age"]
    combined["radio_BED_x_tumor_size"]   = rb * T0
    combined["radio_BED_x_kps"]          = rb * numeric["kps"]
    combined["radio_BED_x_age"]          = rb * numeric["age"]
    combined["chemo_dose_x_radio_BED"]   = cd * rb

    mg = numeric["mgmt_methylation"]
    combined["mgmt_x_chemo"]      = mg * numeric["chemo"]
    combined["mgmt_x_chemo_dose"] = mg * cd
    combined["idh_x_chemo"]       = numeric["idh_mutation"]      * numeric["chemo"]
    combined["idh_x_radio"]       = numeric["idh_mutation"]      * numeric["radio"]
    combined["egfr_x_chemo"]      = numeric["egfr_amplification"]* numeric["chemo"]

    ev = numeric["edema_volume"]
    sc = numeric["symptom_count"]
    combined["edema_x_chemo"]          = ev * numeric["chemo"]
    combined["edema_x_radio"]          = ev * numeric["radio"]
    combined["steroid_x_chemo"]        = numeric["steroid_dose"] * numeric["chemo"]
    combined["symptom_count_x_chemo"]  = sc * numeric["chemo"]
    combined["symptom_count_x_radio"]  = sc * numeric["radio"]

    combined["age_squared"]         = numeric["age"] ** 2
    combined["tumor_size_squared"]   = T0 ** 2
    combined["tumor_size_log"]       = np.log1p(T0)
    combined["r_fit_squared"]        = combined["r_fit"] ** 2
    combined["K_fit_log"]            = np.log1p(K)
    combined["chemo_dose_squared"]   = cd ** 2
    combined["radio_BED_squared"]    = rb ** 2
    combined["chemo_dose_log"]       = np.log1p(cd)
    combined["radio_BED_log"]        = np.log1p(rb)
    combined["edema_squared"]        = ev ** 2
    combined["steroid_squared"]      = numeric["steroid_dose"] ** 2
    combined["symptom_count_squared"]= sc ** 2

    feat_series = pd.Series(
        [combined.get(f, 0.0) for f in _feature_columns],
        index=_feature_columns,
    )
    scaled = _scaler.transform(feat_series.values.reshape(1, -1))
    return pd.Series(scaled[0], index=_feature_columns)


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------

def _predict_single_target(X_input: np.ndarray, target: str) -> float:
    model = _stacked_models[target]
    base_preds = np.array(
        [m.predict(X_input)[0] for _, m in model["bases"]]
    ).reshape(1, -1)
    return float(model["meta"].predict(base_preds)[0])


def predict_gompertz_params(feat_row: pd.Series) -> Dict[str, float]:
    X = feat_row.values.reshape(1, -1)
    return {
        "r":     _predict_single_target(X, "r_target"),
        "K":     _predict_single_target(X, "K_target"),
        "alpha": _predict_single_target(X, "alpha_target"),
        "beta":  _predict_single_target(X, "beta_target"),
    }


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------

def simulate_gompertz(
    T0: float,
    params: Dict[str, float],
    chemo: int,
    radio: int,
    months: int = 12,
    dt: float = 0.01,
) -> float:
    """Return predicted tumor volume (cm³) after `months` months."""
    r, K = params["r"], max(params["K"], T0 * 1.1)
    alpha, beta = params["alpha"], params["beta"]
    T0 = max(T0, 0.1)

    V = T0
    steps = int(months / dt)
    for _ in range(steps - 1):
        V = max(V, 0.01)
        dV = r * V * np.log(K / V) - alpha * chemo * V - beta * radio * V
        V = max(V + dV * dt, 0.01)
    return float(V)


# ---------------------------------------------------------------------------
# Single-plan prediction
# ---------------------------------------------------------------------------

def predict_plan(patient: Dict[str, Any], treatment_string: str,
                 dosages: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """Predict tumor volume for one treatment plan."""
    if dosages is None:
        dosages = extract_dosages(patient, treatment_string)
    flags = parse_treatment_flags(treatment_string)
    feat = build_feature_vector(patient, treatment_string, dosages)
    params = predict_gompertz_params(feat)
    pred = simulate_gompertz(
        float(patient.get("tumor_size_before", 3.0)),
        params, flags["chemo"], flags["radio"],
    )
    return {"params": params, "pred_12m": pred, "dosages": dosages}


# ---------------------------------------------------------------------------
# Grid search optimisation
# ---------------------------------------------------------------------------

def _bed(total_Gy: float, fractions: int) -> float:
    d = total_Gy / fractions
    return fractions * d * (1 + d / 10.0)


def optimize(
    patient: Dict[str, Any],
    chemo_doses: List[float] = (50, 75, 100, 125, 150),
    radio_configs: List[Tuple[float, int]] = ((40, 15), (50, 25), (60, 30), (66, 33)),
) -> Dict[str, Any]:
    """
    Grid-search over chemo doses × radio configs × modalities.
    Returns all results, global best, and (if applicable) local best
    within the same treatment type as the doctor's plan.
    """
    T0 = float(patient.get("tumor_size_before", 3.0))
    all_results: List[Dict[str, Any]] = []

    # --- radiation only ---
    for total_Gy, fractions in radio_configs:
        dosages = {"chemo_dose_mg_per_m2": 0.0,
                   "radio_total_Gy": total_Gy,
                   "radio_BED": _bed(total_Gy, fractions)}
        feat   = build_feature_vector(patient, "radiation", dosages)
        params = predict_gompertz_params(feat)
        pred   = simulate_gompertz(T0, params, chemo=0, radio=1)
        all_results.append({
            "treatment_type": "radiation",
            "chemo_dose_mg_per_m2": 0.0,
            "radio_total_Gy": total_Gy,
            "radio_fractions": fractions,
            "BED": dosages["radio_BED"],
            "pred_12m": pred,
            "params": params,
        })

    # --- chemotherapy only ---
    for dose in chemo_doses:
        dosages = {"chemo_dose_mg_per_m2": dose,
                   "radio_total_Gy": 0.0, "radio_BED": 0.0}
        feat   = build_feature_vector(patient, "chemotherapy", dosages)
        params = predict_gompertz_params(feat)
        pred   = simulate_gompertz(T0, params, chemo=1, radio=0)
        all_results.append({
            "treatment_type": "chemotherapy",
            "chemo_dose_mg_per_m2": dose,
            "radio_total_Gy": 0.0,
            "radio_fractions": 0,
            "BED": 0.0,
            "pred_12m": pred,
            "params": params,
        })

    # --- combination ---
    for dose in chemo_doses:
        for total_Gy, fractions in radio_configs:
            dosages = {"chemo_dose_mg_per_m2": dose,
                       "radio_total_Gy": total_Gy,
                       "radio_BED": _bed(total_Gy, fractions)}
            feat   = build_feature_vector(patient, "chemoradiotherapy", dosages)
            params = predict_gompertz_params(feat)
            pred   = simulate_gompertz(T0, params, chemo=1, radio=1)
            all_results.append({
                "treatment_type": "chemoradiotherapy",
                "chemo_dose_mg_per_m2": dose,
                "radio_total_Gy": total_Gy,
                "radio_fractions": fractions,
                "BED": dosages["radio_BED"],
                "pred_12m": pred,
                "params": params,
            })

    global_best = min(all_results, key=lambda x: x["pred_12m"])

    # --- doctor's plan ---
    doctor_treatment = patient.get("treatment", "")
    doctor_dosages   = extract_dosages(patient, doctor_treatment)
    doctor_flags     = parse_treatment_flags(doctor_treatment)

    doctor_feat   = build_feature_vector(patient, doctor_treatment, doctor_dosages)
    doctor_params = predict_gompertz_params(doctor_feat)
    doctor_pred   = simulate_gompertz(
        T0, doctor_params, doctor_flags["chemo"], doctor_flags["radio"]
    )

    if doctor_flags["chemo"] and doctor_flags["radio"]:
        doctor_type = "chemoradiotherapy"
    elif doctor_flags["chemo"]:
        doctor_type = "chemotherapy"
    else:
        doctor_type = "radiation"

    same_type = [r for r in all_results if r["treatment_type"] == doctor_type]
    local_best = min(same_type, key=lambda x: x["pred_12m"]) if same_type else None

    global_improvement = (doctor_pred - global_best["pred_12m"]) / doctor_pred * 100 if doctor_pred else 0.0
    local_improvement  = (doctor_pred - local_best["pred_12m"]) / doctor_pred * 100 if (local_best and doctor_pred) else 0.0

    return {
        "patient_id":            patient.get("id", "UNKNOWN"),
        "doctor_treatment_type": doctor_type,
        "doctor_plan_prediction": doctor_pred,
        "global_best":           global_best,
        "local_best":            local_best,
        "global_improvement":    round(global_improvement, 2),
        "local_improvement":     round(local_improvement, 2),
        "all_results":           all_results,
    }
