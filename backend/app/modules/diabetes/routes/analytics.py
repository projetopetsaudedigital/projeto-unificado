"""
Endpoints de analytics do módulo Diabetes.
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.modules.diabetes.analytics.kpis import buscar_kpis_diabetes
from app.modules.diabetes.analytics.tendencia import (
    buscar_tendencia_hba1c,
    buscar_hba1c_por_faixa,
    buscar_hba1c_por_faixa_etaria,
    buscar_hba1c_por_sexo,
)
from app.modules.diabetes.analytics.controle import (
    buscar_controle_por_grupo,
    buscar_tendencia_controle_anual,
    buscar_controle_por_bairro,
    buscar_comorbidades_vs_controle,
)

router = APIRouter()


@router.get("/kpis", summary="KPIs gerais do módulo Diabetes")
def kpis():
    return buscar_kpis_diabetes()


@router.get("/tendencia", summary="Evolução mensal da HbA1c")
def tendencia(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
    bairro:     Optional[str] = Query(None),
):
    return buscar_tendencia_hba1c(ano_inicio, ano_fim, bairro)


@router.get("/hba1c/faixa", summary="Distribuição de valores de HbA1c (histograma)")
def hba1c_faixa(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
    bairro:     Optional[str] = Query(None),
):
    return buscar_hba1c_por_faixa(ano_inicio, ano_fim, bairro)


@router.get("/hba1c/faixa-etaria", summary="HbA1c média por faixa etária")
def hba1c_faixa_etaria(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
):
    return buscar_hba1c_por_faixa_etaria(ano_inicio, ano_fim)


@router.get("/hba1c/sexo", summary="HbA1c média por sexo")
def hba1c_sexo(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
):
    return buscar_hba1c_por_sexo(ano_inicio, ano_fim)


@router.get("/controle/grupo", summary="Controlados vs descontrolados por grupo etário")
def controle_grupo(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
    bairro:     Optional[str] = Query(None),
):
    return buscar_controle_por_grupo(ano_inicio, ano_fim, bairro)


@router.get("/controle/tendencia", summary="Evolução anual controlados vs descontrolados")
def controle_tendencia(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
):
    return buscar_tendencia_controle_anual(ano_inicio, ano_fim)


@router.get("/controle/bairro", summary="Controle glicêmico por bairro")
def controle_bairro(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
):
    return buscar_controle_por_bairro(ano_inicio, ano_fim)


@router.get("/controle/comorbidades", summary="Comorbidades em controlados vs descontrolados")
def comorbidades_vs_controle():
    return buscar_comorbidades_vs_controle()
