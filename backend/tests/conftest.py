"""
Fixtures compartilhadas para os testes.
"""

import sys
from pathlib import Path

import pytest

# Garante que 'app' seja importável
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def perfil_paciente_base():
    """Perfil base de paciente para testes de predição."""
    return {
        "idade": 55,
        "co_dim_sexo": 1,
        "st_diabetes": 0,
        "st_fumante": 0,
        "st_alcool": 0,
        "st_outra_droga": 0,
        "st_doenca_cardiaca": 0,
        "st_problema_rins": 0,
        "st_avc": 0,
        "st_infarto": 0,
        "st_doenca_respiratoria": 0,
        "st_cancer": 0,
        "st_hanseniase": 0,
        "st_tuberculose": 0,
    }


@pytest.fixture
def perfil_alto_risco(perfil_paciente_base):
    """Perfil de paciente com múltiplos fatores de risco."""
    return {
        **perfil_paciente_base,
        "idade": 72,
        "st_diabetes": 1,
        "st_fumante": 1,
        "st_doenca_cardiaca": 1,
        "st_problema_rins": 1,
    }
