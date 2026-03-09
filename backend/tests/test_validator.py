"""
Testes para o validador de medições de PA.

Cobre:
  - Parsing de strings "PAS/PAD"
  - Validação de ranges (válido, inválido, suspeito)
  - Classificação de PA por diretrizes brasileiras
  - Ajuste de classificação para idosos (≥65)
"""

import pytest
from app.modules.pressao_arterial.quality.validator import (
    validar_pa,
    classificar_pa,
    ResultadoValidacao,
)


# ═══════════════════════════════════════════════════════════════════════════════
# validar_pa
# ═══════════════════════════════════════════════════════════════════════════════


class TestValidarPa:
    """Testes para validar_pa()."""

    # ── Valores válidos ──

    def test_valor_normal(self):
        r = validar_pa("120/80")
        assert r.status == "valido"
        assert r.pas == 120.0
        assert r.pad == 80.0
        assert r.motivo is None

    def test_valor_com_espacos(self):
        r = validar_pa("  130 / 85  ")
        assert r.status == "valido"
        assert r.pas == 130.0
        assert r.pad == 85.0

    def test_valor_com_mmhg(self):
        r = validar_pa("140/90 mmHg")
        assert r.status == "valido"
        assert r.pas == 140.0
        assert r.pad == 90.0

    def test_hipertensao_leve(self):
        r = validar_pa("150/95")
        assert r.status == "valido"

    def test_limite_inferior_valido(self):
        r = validar_pa("80/40")
        assert r.status == "valido"

    # ── Valores inválidos ──

    def test_vazio(self):
        r = validar_pa("")
        assert r.status == "invalido"

    def test_none(self):
        r = validar_pa(None)
        assert r.status == "invalido"

    def test_nan_string(self):
        r = validar_pa("nan")
        assert r.status == "invalido"

    def test_null_string(self):
        r = validar_pa("NULL")
        assert r.status == "invalido"

    def test_formato_invalido_sem_barra(self):
        r = validar_pa("12080")
        assert r.status == "invalido"
        assert "formato" in r.motivo.lower()

    def test_formato_invalido_texto(self):
        r = validar_pa("alta/normal")
        assert r.status == "invalido"
        assert "numérico" in r.motivo.lower()

    def test_pas_acima_maximo(self):
        r = validar_pa("350/90")
        assert r.status == "invalido"
        assert "PAS" in r.motivo

    def test_pad_abaixo_minimo(self):
        r = validar_pa("120/20")
        assert r.status == "invalido"
        assert "PAD" in r.motivo

    def test_pas_menor_que_pad(self):
        r = validar_pa("80/90")
        assert r.status == "invalido"
        assert "maior" in r.motivo.lower()

    def test_pas_igual_pad(self):
        r = validar_pa("100/100")
        assert r.status == "invalido"

    # ── Valores suspeitos ──

    def test_pas_muito_alta(self):
        r = validar_pa("260/100")
        assert r.status == "suspeito"
        assert "extrema" in r.motivo.lower()

    def test_pad_muito_alta(self):
        r = validar_pa("180/160")
        assert r.status == "suspeito"
        assert "PAD" in r.motivo

    def test_pas_muito_baixa(self):
        r = validar_pa("60/35")
        assert r.status == "suspeito"
        assert "PAS" in r.motivo


# ═══════════════════════════════════════════════════════════════════════════════
# classificar_pa
# ═══════════════════════════════════════════════════════════════════════════════


class TestClassificarPa:
    """Testes para classificar_pa() — diretrizes brasileiras."""

    def test_otima_normal(self):
        assert classificar_pa(110, 70) == "Ótima/Normal"

    def test_pre_hipertensao(self):
        assert classificar_pa(130, 85) == "Pré-Hipertensão"

    def test_hipertensao_por_pas(self):
        assert classificar_pa(140, 80) == "Hipertensão"

    def test_hipertensao_por_pad(self):
        assert classificar_pa(130, 90) == "Hipertensão"

    def test_hipertensao_ambos(self):
        assert classificar_pa(160, 100) == "Hipertensão"

    def test_limiar_pas_119(self):
        assert classificar_pa(119, 79) == "Ótima/Normal"

    def test_limiar_pas_120(self):
        assert classificar_pa(120, 79) == "Pré-Hipertensão"

    def test_limiar_pas_139(self):
        assert classificar_pa(139, 89) == "Pré-Hipertensão"

    # ── Idosos (≥65) ──

    def test_idoso_normal(self):
        assert classificar_pa(140, 85, idade=70) == "Ótima/Normal (Idoso)"

    def test_idoso_hipertensao(self):
        assert classificar_pa(155, 85, idade=70) == "Hipertensão"

    def test_idoso_limiar_150(self):
        assert classificar_pa(150, 90, idade=65) == "Ótima/Normal (Idoso)"

    def test_idoso_limiar_151(self):
        assert classificar_pa(151, 90, idade=65) == "Hipertensão"

    # ── Nulos ──

    def test_pas_nan(self):
        import pandas as pd
        assert classificar_pa(pd.NA, 80) == "Desconhecido"
