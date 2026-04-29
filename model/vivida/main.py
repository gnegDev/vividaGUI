"""
main.py — GBM Treatment Optimization API v3.0 (FastAPI)
"""

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

import logging

import optimizer

MODEL_VERSION = "3.0"
MODEL_FEATURES = 115


# ---------------------------------------------------------------------------
# Startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    optimizer.load_models()
    yield

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="GBM Treatment Optimization API",
    version=MODEL_VERSION,
    description="Glioblastoma treatment optimization via Gompertz model + stacking ensemble.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class ChemotherapyIn(BaseModel):
    drug: Optional[str] = None
    dose_mg_per_m2: float = 0.0
    cycles: Optional[int] = None
    interval_days: Optional[int] = None


class RadiotherapyIn(BaseModel):
    total_dose_Gy: float = 0.0
    fraction_dose_Gy: Optional[float] = None
    fractions: int = 0
    technique: Optional[str] = None


class PatientIn(BaseModel):
    id: str
    age: float = Field(..., ge=0, le=120)
    tumor_size_before: float = Field(..., gt=0)
    kps: float = Field(..., ge=0, le=100)
    treatment: str

    # Basic
    gender: Optional[str] = None
    resection_extent: Optional[str] = None
    molecular_subtype: Optional[str] = None
    tumor_location: Optional[str] = None
    contrast_enhancement: Optional[str] = None
    stage: Optional[str] = None

    # Dosage structs
    chemotherapy: Optional[ChemotherapyIn] = None
    radiotherapy: Optional[RadiotherapyIn] = None

    # Genetic markers
    mgmt_methylation: Optional[bool] = None
    idh_mutation: Optional[bool] = None
    egfr_amplification: Optional[bool] = None
    tert_mutation: Optional[bool] = None
    atrx_mutation: Optional[bool] = None

    # Clinical
    edema_volume: Optional[float] = Field(default=None, ge=0)
    steroid_dose: Optional[float] = Field(default=None, ge=0)
    antiseizure_meds: Optional[bool] = None

    # Neurological symptoms
    neurological_symptoms: Optional[str] = None
    has_headache: Optional[bool] = None
    has_motor_deficit: Optional[bool] = None
    has_seizures: Optional[bool] = None
    has_sensory_deficit: Optional[bool] = None
    has_cognitive_decline: Optional[bool] = None
    has_speech_disturbance: Optional[bool] = None
    has_visual_disturbance: Optional[bool] = None
    symptom_count: Optional[int] = None

    # Other
    lateralization: Optional[str] = None
    rano_response: Optional[str] = None
    family_history: Optional[bool] = None
    previous_radiation: Optional[bool] = None

    model_config = {"extra": "allow"}

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "service": f"GBM Treatment Optimization API v{MODEL_VERSION}",
        "version": MODEL_VERSION,
        "features": MODEL_FEATURES,
    }


@app.get("/model/info", tags=["System"])
def model_info():
    return {
        "version": MODEL_VERSION,
        "features": MODEL_FEATURES,
        "accuracy": {
            "r_target": "99.98%",
            "K_target": "99.99%",
            "alpha_target": "99.93%",
            "beta_target": "99.48%",
        },
        "supported_features": {
            "required": ["id", "age", "tumor_size_before", "kps", "treatment"],
            "basic": ["gender", "resection_extent", "molecular_subtype",
                      "tumor_location", "contrast_enhancement"],
            "genetic": ["mgmt_methylation", "idh_mutation", "egfr_amplification",
                        "tert_mutation", "atrx_mutation"],
            "clinical": ["edema_volume", "steroid_dose", "antiseizure_meds"],
            "neurological": ["neurological_symptoms", "has_headache", "has_seizures",
                             "has_motor_deficit", "has_sensory_deficit",
                             "has_cognitive_decline", "has_speech_disturbance",
                             "has_visual_disturbance", "symptom_count"],
            "other": ["lateralization", "rano_response",
                      "family_history", "previous_radiation"],
        },
    }


@app.post("/optimize", tags=["Optimization"])
def optimize_full(patient: PatientIn):
    """Full grid-search optimization. Returns all tested regimens."""
    try:
        patient_data = patient.to_dict()
        logger.info(patient_data)

        result = optimizer.optimize(patient_data)
        result["model_version"] = MODEL_VERSION

        logger.info(result)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/optimize/summary", tags=["Optimization"])
def optimize_summary(patient: PatientIn):
    """Simplified optimization result for UI consumption."""
    try:
        patient_data = patient.to_dict()
        logger.info(patient_data)

        result = optimizer.optimize(patient_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    gb = result["global_best"]
    lb = result.get("local_best")
    global_improvement = result.get("global_improvement", 0)

    summary: Dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "patient_id": result["patient_id"],
        "doctor_plan": {
            "treatment_type": result["doctor_treatment_type"],
            "prediction": result["doctor_plan_prediction"],
        },
        "global_optimal": {
            "treatment_type": gb["treatment_type"],
            "prediction": gb["pred_12m"],
            "improvement_percent": global_improvement,
            "chemotherapy": {"dose_mg_per_m2": gb["chemo_dose_mg_per_m2"]}
                if gb.get("chemo_dose_mg_per_m2", 0) > 0 else None,
            "radiotherapy": {
                "total_dose_Gy": gb["radio_total_Gy"],
                "fractions": gb["radio_fractions"],
                "BED": gb["BED"],
            } if gb.get("radio_total_Gy", 0) > 0 else None,
        },
        "local_optimal": {
            "treatment_type": lb["treatment_type"],
            "prediction": lb["pred_12m"],
            "improvement_percent": result.get("local_improvement", 0),
        } if lb else None,
        "recommendation": (
            "major_change" if global_improvement >= 10
            else "minor_change" if global_improvement >= 3
            else "optimal"
        ),
    }

    # Add relevant patient characteristics
    p = patient
    characteristics: Dict[str, Any] = {}
    if p.mgmt_methylation:
        characteristics["mgmt_status"] = "methylated"
    if p.idh_mutation:
        characteristics["idh_status"] = "mutant"
    if p.edema_volume and p.edema_volume > 0:
        characteristics["edema_volume"] = p.edema_volume
    if p.symptom_count and p.symptom_count > 0:
        characteristics["symptom_count"] = p.symptom_count
    if characteristics:
        summary["patient_characteristics"] = characteristics

    logger.info(summary)
    return summary


@app.post("/validate", tags=["Validation"])
def validate(patient: PatientIn):
    """
    Validate patient data without running optimization.
    Pydantic handles type/range checks; this confirms the data is accepted.
    """
    return {"valid": True, "message": "Patient data is valid",
            "model_version": MODEL_VERSION}
