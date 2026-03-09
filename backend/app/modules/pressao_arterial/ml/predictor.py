"""
Preditor de risco de Hipertensão Arterial.

Carrega o modelo treinado (ha_risk_rf.joblib) e o metadado (ha_risk_meta.json).
Expõe funções para verificar status do modelo e fazer predições individuais.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np

from app.core.logging_config import setup_logging

logger = setup_logging("pa.ml.predictor")

MODEL_PATH = Path(__file__).parent.parent.parent.parent.parent.parent / "models" / "ha_risk_rf.joblib"
META_PATH  = MODEL_PATH.parent / "ha_risk_meta.json"

# ── Níveis de risco ───────────────────────────────────────────────────────────

def _nivel_risco(prob: float) -> dict:
    pct = round(prob * 100, 1)
    if pct < 20:
        return {"nivel": "Baixo",    "cor": "green",  "pct": pct}
    if pct < 35:
        return {"nivel": "Moderado", "cor": "amber",  "pct": pct}
    return             {"nivel": "Alto",     "cor": "red",    "pct": pct}


# ── Status do modelo ──────────────────────────────────────────────────────────

def modelo_disponivel() -> bool:
    return MODEL_PATH.exists() and META_PATH.exists()


def info_modelo() -> dict:
    if not modelo_disponivel():
        return {"disponivel": False, "mensagem": "Modelo não treinado. Execute POST /modelo/treinar."}

    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    return {
        "disponivel":         True,
        "treinado_em":        meta.get("treinado_em"),
        "total_registros":    meta.get("total_registros"),
        "prevalencia_treino": meta.get("prevalencia_treino"),
        "metricas":           meta.get("metricas"),
        "feature_importances": sorted(
            meta.get("feature_importances", {}).items(),
            key=lambda x: x[1],
            reverse=True,
        ),
    }


# ── Predição individual ───────────────────────────────────────────────────────

# Mapeamento legível de features para o usuário
FEATURE_LABELS = {
    "idade":                 "Idade",
    "co_dim_sexo":           "Sexo",
    "st_diabetes":           "Diabetes",
    "st_fumante":            "Fumante",
    "st_alcool":             "Uso de álcool",
    "st_outra_droga":        "Uso de outras drogas",
    "st_doenca_cardiaca":    "Doença cardíaca",
    "st_problema_rins":      "Problema nos rins",
    "st_avc":                "AVC/Derrame",
    "st_infarto":            "Infarto",
    "st_doenca_respiratoria":"Doença respiratória",
    "st_cancer":             "Câncer",
    "st_hanseniase":         "Hanseníase",
    "st_tuberculose":        "Tuberculose",
}


def predizer_risco(perfil: dict) -> dict:
    """
    Prediz probabilidade de hipertensão para um perfil de paciente.

    perfil: dict com as features do modelo (ver FEATURES em pipeline.py).
    Valores binários ausentes são tratados como 0 (não informado).

    Retorna:
        probabilidade (0-1), percentual, nível de risco, fatores contribuintes.
    """
    if not modelo_disponivel():
        raise RuntimeError("Modelo não encontrado. Treine primeiro via POST /modelo/treinar.")

    clf  = joblib.load(MODEL_PATH)
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    features: list[str] = meta["features"]

    # Monta vetor na ordem correta, substituindo ausentes por 0
    X = np.array([[perfil.get(f, 0) for f in features]], dtype=float)

    prob = float(clf.predict_proba(X)[0, 1])
    risco = _nivel_risco(prob)

    # Top fatores: importâncias × valor do perfil (indica quais ativaram mais)
    importancias = meta.get("feature_importances", {})
    fatores = [
        {
            "feature": f,
            "label":   FEATURE_LABELS.get(f, f),
            "valor":   perfil.get(f, 0),
            "importancia": importancias.get(f, 0.0),
        }
        for f in features
        if importancias.get(f, 0.0) > 0.01  # só os relevantes
    ]
    fatores.sort(key=lambda x: x["importancia"], reverse=True)

    return {
        "probabilidade":   round(prob, 4),
        "probabilidade_pct": risco["pct"],
        "nivel_risco":     risco["nivel"],
        "cor_risco":       risco["cor"],
        "fatores":         fatores[:8],  # top 8
        "aviso": (
            "Este resultado é apenas uma estimativa baseada em dados populacionais. "
            "Não substitui avaliação clínica."
        ),
    }
