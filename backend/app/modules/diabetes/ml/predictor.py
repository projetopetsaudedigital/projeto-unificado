"""
Preditor de controle glicêmico em pacientes diabéticos.

Carrega o modelo treinado (dm_controle_rf.joblib) e metadado (dm_controle_meta.json).
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

from app.core.logging_config import setup_logging

logger = setup_logging("dm.ml.predictor")

MODEL_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "models" / "dm_controle_rf.joblib"
META_PATH  = MODEL_PATH.parent / "dm_controle_meta.json"


# ── Níveis de probabilidade de controle ───────────────────────────────────────

def _nivel_controle(prob: float) -> dict:
    """prob = probabilidade de estar Controlado."""
    pct = round(prob * 100, 1)
    if pct >= 65:
        return {"nivel": "Provável controle",   "cor": "green",  "pct": pct}
    if pct >= 40:
        return {"nivel": "Controle incerto",    "cor": "amber",  "pct": pct}
    return     {"nivel": "Risco de descontrole","cor": "red",    "pct": pct}


# ── Status do modelo ──────────────────────────────────────────────────────────

def modelo_disponivel() -> bool:
    return MODEL_PATH.exists() and META_PATH.exists()


def info_modelo() -> dict:
    if not modelo_disponivel():
        return {"disponivel": False, "mensagem": "Modelo não treinado. Execute POST /modelo/treinar."}

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    return {
        "disponivel":          True,
        "treinado_em":         meta.get("treinado_em"),
        "total_registros":     meta.get("total_registros"),
        "prevalencia_treino":  meta.get("prevalencia_treino"),
        "metricas":            meta.get("metricas"),
        "feature_importances": sorted(
            meta.get("feature_importances", {}).items(),
            key=lambda x: x[1],
            reverse=True,
        ),
    }


# ── Predição individual ───────────────────────────────────────────────────────

FEATURE_LABELS = {
    "idade":                 "Idade",
    "co_dim_sexo":           "Sexo",
    "hba1c":                 "HbA1c (%)",
    "st_hipertensao":        "Hipertensão",
    "st_doenca_cardiaca":    "Doença cardíaca",
    "st_insuf_cardiaca":     "Insuf. cardíaca",
    "st_infarto":            "Infarto",
    "st_problema_rins":      "Problema nos rins",
    "st_avc":                "AVC/Derrame",
    "st_fumante":            "Fumante",
    "st_alcool":             "Uso de álcool",
    "st_doenca_respiratoria":"Doença respiratória",
    "st_cancer":             "Câncer",
}


def predizer_controle(perfil: dict) -> dict:
    """
    Prediz probabilidade de controle glicêmico para um paciente diabético.

    perfil: dict com as features do modelo (ver FEATURES em pipeline.py).
    Retorna probabilidade, nível e fatores contribuintes.
    """
    if not modelo_disponivel():
        raise RuntimeError("Modelo não encontrado. Treine primeiro via POST /modelo/treinar.")

    clf  = joblib.load(MODEL_PATH)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    features: list[str] = meta["features"]

    X = np.array([[perfil.get(f, 0) for f in features]], dtype=float)

    prob  = float(clf.predict_proba(X)[0, 1])  # prob de ser Controlado
    nivel = _nivel_controle(prob)

    importancias = meta.get("feature_importances", {})
    fatores = [
        {
            "feature":    f,
            "label":      FEATURE_LABELS.get(f, f),
            "valor":      perfil.get(f, 0),
            "importancia": importancias.get(f, 0.0),
        }
        for f in features
        if importancias.get(f, 0.0) > 0.01
    ]
    fatores.sort(key=lambda x: x["importancia"], reverse=True)

    return {
        "probabilidade":       round(prob, 4),
        "probabilidade_pct":   nivel["pct"],
        "nivel_controle":      nivel["nivel"],
        "cor_controle":        nivel["cor"],
        "fatores":             fatores[:8],
        "aviso": (
            "Este resultado é uma estimativa baseada em dados populacionais. "
            "O controle glicêmico real depende de avaliação clínica individualizada."
        ),
    }
