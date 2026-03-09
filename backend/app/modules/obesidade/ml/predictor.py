"""
Predição individual de classificação IMC usando modelo treinado.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import joblib
import numpy as np

from app.core.logging_config import setup_logging
from app.modules.obesidade.ml.pipeline import (
    CLASSES,
    ENCODER_PATH,
    FEATURES,
    META_PATH,
    MODEL_PATH,
)

logger = setup_logging("ob.ml.predictor")

# Cache em memória — recarrega se o arquivo mudar
_clf = None
_le  = None
_meta: Optional[dict] = None


def _carregar_modelo():
    global _clf, _le, _meta
    if MODEL_PATH.exists() and META_PATH.exists() and ENCODER_PATH.exists():
        _clf  = joblib.load(MODEL_PATH)
        _le   = joblib.load(ENCODER_PATH)
        _meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        logger.info("Modelo de obesidade carregado.")
    else:
        _clf = _le = _meta = None


def get_modelo_info() -> dict:
    _carregar_modelo()
    if _clf is None:
        return {"modelo_treinado": False, "treino_em_andamento": False}

    return {
        "modelo_treinado": True,
        "treinado_em": _meta.get("treinado_em"),
        "total_registros_treino": _meta.get("total_registros"),
        "distribuicao_treino": _meta.get("distribuicao_treino"),
        "metricas": _meta.get("metricas"),
        "metricas_por_classe": _meta.get("metricas_por_classe"),
        "feature_importances": _meta.get("feature_importances"),
        "treino_em_andamento": False,
    }


def predizer(
    peso_kg: float,
    altura_m: float,
    idade: int,
    sexo: str,
    st_hipertensao: int = 0,
    st_diabete: int = 0,
    st_fumante: int = 0,
    st_alcool: int = 0,
    st_doenca_cardiaca: int = 0,
    st_doenca_respiratoria: int = 0,
) -> dict:
    _carregar_modelo()
    if _clf is None:
        raise ValueError("Modelo não treinado. Execute POST /modelo/treinar primeiro.")

    imc = peso_kg / (altura_m ** 2)
    co_dim_sexo = 1 if sexo.upper() == "M" else 3

    x = np.array([[
        peso_kg, altura_m, imc, idade, co_dim_sexo,
        st_hipertensao, st_diabete, st_fumante, st_alcool,
        st_doenca_cardiaca, st_doenca_respiratoria,
    ]])

    idx_pred = _clf.predict(x)[0]
    probs    = _clf.predict_proba(x)[0]

    # Garante que probabilidades correspondam à ordem canônica das classes
    classe_pred = _le.inverse_transform([idx_pred])[0]
    probs_dict  = dict(zip(_le.classes_, probs.tolist()))

    confianca = float(max(probs))
    if confianca < 0.5:
        nivel = "Baixa"
    elif confianca < 0.7:
        nivel = "Media"
    elif confianca < 0.9:
        nivel = "Alta"
    else:
        nivel = "Muito Alta"

    return {
        "imc_calculado": round(imc, 2),
        "classificacao_predita": classe_pred,
        "probabilidades": {
            "baixo_peso":   round(probs_dict.get("Baixo Peso",   0), 4),
            "normal":       round(probs_dict.get("Normal",       0), 4),
            "sobrepeso":    round(probs_dict.get("Sobrepeso",    0), 4),
            "obesidade_i":  round(probs_dict.get("Obesidade I",  0), 4),
            "obesidade_ii": round(probs_dict.get("Obesidade II", 0), 4),
            "obesidade_iii":round(probs_dict.get("Obesidade III",0), 4),
        },
        "confianca": round(confianca, 4),
        "nivel_confianca": nivel,
    }
