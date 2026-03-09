"""
Endpoints de analytics de obesidade / IMC.
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.modules.obesidade.analytics.kpis import get_kpis
from app.modules.obesidade.analytics.tendencia import get_tendencia
from app.modules.obesidade.analytics.distribuicao import get_distribuicao
from app.modules.obesidade.analytics.fatores_risco import get_fatores_risco, get_bairros
from app.modules.obesidade.schemas import (
    KPIsObesidadeResponse,
    KPIsObesidade,
    TendenciaObesidadeResponse,
    DistribuicaoObesidadeResponse,
    FatoresRiscoObesidadeResponse,
    BairrosObesidadeResponse,
)
from app.core.logging_config import setup_logging

logger = setup_logging("ob.routes.analytics")
router = APIRouter()


@router.get(
    "/kpis",
    response_model=KPIsObesidadeResponse,
    summary="KPIs de obesidade",
    description="Retorna indicadores gerais: total de medições, adultos únicos, IMC médio, "
                "prevalência de sobrepeso e obesidade (graus I, II e III) e tendência mensal.",
)
def endpoint_kpis(
    ano_inicio: Optional[int] = Query(None, description="Ano inicial do filtro"),
    ano_fim:    Optional[int] = Query(None, description="Ano final do filtro"),
    bairro:     Optional[str] = Query(None, description="Filtrar por bairro (no_bairro_filtro)"),
    co_unidade_saude: Optional[int] = Query(None, description="Filtrar por UBS (co_unidade_saude)"),
    sexo:       Optional[str] = Query(None, description="Filtrar por sexo: M ou F"),
):
    try:
        data = get_kpis(ano_inicio, ano_fim, bairro, co_unidade_saude, sexo)
        return KPIsObesidadeResponse(
            kpis=KPIsObesidade(**data),
            filtros={
                "ano_inicio": ano_inicio, "ano_fim": ano_fim,
                "bairro": bairro, "co_unidade_saude": co_unidade_saude, "sexo": sexo,
            },
        )
    except Exception as e:
        logger.error(f"Erro em /kpis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/tendencia",
    response_model=TendenciaObesidadeResponse,
    summary="Evolução temporal do IMC",
    description="Série mensal com IMC médio e percentual de cada classificação de peso ao longo do tempo.",
)
def endpoint_tendencia(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
    bairro:     Optional[str] = Query(None),
    co_unidade_saude: Optional[int] = Query(None),
):
    try:
        serie = get_tendencia(ano_inicio, ano_fim, bairro, co_unidade_saude)
        return TendenciaObesidadeResponse(serie=serie)
    except Exception as e:
        logger.error(f"Erro em /tendencia: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/distribuicao",
    response_model=DistribuicaoObesidadeResponse,
    summary="Distribuição das 6 classes de IMC",
    description="Distribuição das classificações de IMC (total, por sexo e por faixa etária).",
)
def endpoint_distribuicao(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
    bairro:     Optional[str] = Query(None),
    co_unidade_saude: Optional[int] = Query(None),
):
    try:
        data = get_distribuicao(ano_inicio, ano_fim, bairro, co_unidade_saude)
        return DistribuicaoObesidadeResponse(**data)
    except Exception as e:
        logger.error(f"Erro em /distribuicao: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/fatores-risco",
    response_model=FatoresRiscoObesidadeResponse,
    summary="Comorbidades por classificação de IMC",
    description="Prevalência de comorbidades (hipertensão, diabetes, cardiopatias, etc.) "
                "estratificada por cada classificação de IMC.",
)
def endpoint_fatores_risco(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
    bairro:     Optional[str] = Query(None),
    co_unidade_saude: Optional[int] = Query(None),
):
    try:
        data = get_fatores_risco(ano_inicio, ano_fim, bairro, co_unidade_saude)
        return FatoresRiscoObesidadeResponse(comorbidades=data)
    except Exception as e:
        logger.error(f"Erro em /fatores-risco: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/bairros",
    response_model=BairrosObesidadeResponse,
    summary="IMC e obesidade por bairro",
    description="IMC médio, total de medições/adultos e prevalência de obesidade por bairro. "
                "Retorna apenas bairros com pelo menos 10 medições.",
)
def endpoint_bairros(
    ano_inicio: Optional[int] = Query(None),
    ano_fim:    Optional[int] = Query(None),
    co_unidade_saude: Optional[int] = Query(None),
):
    try:
        data = get_bairros(ano_inicio, ano_fim, co_unidade_saude)
        return BairrosObesidadeResponse(bairros=data)
    except Exception as e:
        logger.error(f"Erro em /bairros: {e}")
        raise HTTPException(status_code=500, detail=str(e))
