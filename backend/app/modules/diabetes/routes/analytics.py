"""
Endpoints de analytics do módulo Diabetes.
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.auth.jwt import get_usuario_obrigatorio
from app.modules.diabetes.analytics.kpis import buscar_kpis_diabetes
from app.modules.diabetes.analytics.individuos import buscar_individuos_diabetes_descontrolados
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
from app.modules.diabetes.schemas import IndividuosDiabetesResponse

router = APIRouter()


@router.get(
    "/individuos",
    summary="Lista operacional de individuos descontrolados em diabetes",
    response_model=IndividuosDiabetesResponse,
)
def individuos_diabetes(
    bairro: Optional[str] = Query(default=None, description="Filtro por bairro normalizado"),
    sexo: Optional[str] = Query(default=None, pattern="^[MF]$", description="Filtro por sexo: M ou F"),
    faixa_etaria: Optional[str] = Query(
        default=None,
        pattern="^(18-29|30-39|40-49|50-59|60-64|65\\+)$",
        description="Filtro por faixa etaria",
    ),
    data_ultimo_exame_inicio: Optional[date] = Query(default=None, description="Data inicial do ultimo exame"),
    data_ultimo_exame_fim: Optional[date] = Query(default=None, description="Data final do ultimo exame"),
    limite: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    usuario: dict = Depends(get_usuario_obrigatorio),
):
    """Lista individuos descontrolados pelo ultimo exame de HbA1c no periodo de 12 meses."""
    _ = usuario

    if (
        data_ultimo_exame_inicio is not None
        and data_ultimo_exame_fim is not None
        and data_ultimo_exame_inicio > data_ultimo_exame_fim
    ):
        raise HTTPException(
            status_code=422,
            detail="data_ultimo_exame_inicio nao pode ser maior que data_ultimo_exame_fim",
        )

    resultado = buscar_individuos_diabetes_descontrolados(
        bairro=bairro,
        sexo=sexo,
        faixa_etaria=faixa_etaria,
        data_ultimo_exame_inicio=data_ultimo_exame_inicio,
        data_ultimo_exame_fim=data_ultimo_exame_fim,
        limite=limite,
        offset=offset,
    )

    return {
        "total": resultado["total"],
        "limite": limite,
        "offset": offset,
        "filtros_aplicados": {
            "bairro": bairro,
            "sexo": sexo,
            "faixa_etaria": faixa_etaria,
            "data_ultimo_exame_inicio": data_ultimo_exame_inicio,
            "data_ultimo_exame_fim": data_ultimo_exame_fim,
        },
        "dados": resultado["dados"],
    }


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
