"""
Testes para o predictor de risco de HAS.

Cobre:
  - Níveis de risco (baixo, moderado, alto)
  - Verificação de disponibilidade do modelo
  - Informações do modelo
"""

import pytest
from app.modules.pressao_arterial.ml.predictor import (
    _nivel_risco,
    FEATURE_LABELS,
)


# ═══════════════════════════════════════════════════════════════════════════════
# _nivel_risco
# ═══════════════════════════════════════════════════════════════════════════════


class TestNivelRisco:
    """Testes para a classificação de nível de risco."""

    def test_risco_baixo(self):
        r = _nivel_risco(0.10)
        assert r["nivel"] == "Baixo"
        assert r["cor"] == "green"
        assert r["pct"] == 10.0

    def test_risco_moderado(self):
        r = _nivel_risco(0.25)
        assert r["nivel"] == "Moderado"
        assert r["cor"] == "amber"
        assert r["pct"] == 25.0

    def test_risco_alto(self):
        r = _nivel_risco(0.50)
        assert r["nivel"] == "Alto"
        assert r["cor"] == "red"
        assert r["pct"] == 50.0

    def test_limiar_baixo_moderado(self):
        r = _nivel_risco(0.199)
        assert r["nivel"] == "Baixo"

    def test_limiar_exato_20(self):
        r = _nivel_risco(0.20)
        assert r["nivel"] == "Moderado"

    def test_limiar_exato_35(self):
        r = _nivel_risco(0.35)
        assert r["nivel"] == "Alto"

    def test_zero(self):
        r = _nivel_risco(0.0)
        assert r["nivel"] == "Baixo"
        assert r["pct"] == 0.0

    def test_um(self):
        r = _nivel_risco(1.0)
        assert r["nivel"] == "Alto"
        assert r["pct"] == 100.0


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURE_LABELS
# ═══════════════════════════════════════════════════════════════════════════════


class TestFeatureLabels:
    """Testes para o mapeamento de features → labels legíveis."""

    def test_todas_features_tem_label(self):
        features_esperadas = [
            "idade", "co_dim_sexo", "st_diabetes", "st_fumante",
            "st_alcool", "st_outra_droga", "st_doenca_cardiaca",
            "st_problema_rins", "st_avc", "st_infarto",
            "st_doenca_respiratoria", "st_cancer",
            "st_hanseniase", "st_tuberculose",
        ]
        for f in features_esperadas:
            assert f in FEATURE_LABELS, f"Feature '{f}' sem label legível"

    def test_labels_nao_vazias(self):
        for k, v in FEATURE_LABELS.items():
            assert len(v) > 0, f"Label para '{k}' está vazia"
