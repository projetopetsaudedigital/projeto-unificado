"""
Router de analytics — Pressão Arterial.

Endpoints:
  GET /tendencia             → evolução mensal de medições e classificação PA
  GET /prevalencia           → hipertensos por bairro VDC, sexo, faixa etária
  GET /distribuicao-area       → distribuição de cadastros e hipertensão por nu_area
  GET /distribuicao-microarea  → distribuição de cadastros e hipertensão por nu_micro_area
  GET /fatores-risco           → comparativo comorbidades hipertensos vs não
  GET /mapa                    → dados por bairro VDC para mapa coroplético
  GET /cobertura-bairros       → resumo de cobertura VDC vs não-identificados
  GET /bairros                 → lista de bairros VDC disponíveis
"""

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from app.modules.pressao_arterial.analytics.tendencia import buscar_tendencia
from app.modules.pressao_arterial.analytics.prevalencia import (
    buscar_prevalencia_por_bairro,
    buscar_prevalencia_por_sexo,
    buscar_prevalencia_por_faixa_etaria,
    buscar_kpis_gerais,
    buscar_resumo_nao_identificados,
)
from app.modules.pressao_arterial.analytics.fatores_risco import (
    buscar_comparativo_comorbidades,
    buscar_multiplos_fatores,
)
from app.modules.pressao_arterial.analytics.mapa import (
    buscar_dados_mapa,
    buscar_bairros_disponiveis,
    buscar_cobertura_bairros,
    buscar_dados_mapa_loteamentos,
)
from app.modules.pressao_arterial.analytics.ubs import buscar_dados_ubs
from app.modules.pressao_arterial.analytics.individuos import buscar_individuos_hipertensos
from app.modules.pressao_arterial.analytics.area import buscar_distribuicao_por_area
from app.modules.pressao_arterial.analytics.microarea import buscar_distribuicao_por_microarea
from app.modules.pressao_arterial.analytics.gestor import buscar_painel_gestor_controle_pressorico

from app.auth.jwt import get_usuario_obrigatorio
from app.modules.pressao_arterial.schemas import (
    KPIsResponse,
    TendenciaResponse,
    PrevalenciaResponse,
    FatoresRiscoResponse,
    MapaResponse,
    BairrosResponse,
    UbsResponse,
    IndividuosHipertensaoResponse,
    DistribuicaoAreaResponse,
    DistribuicaoMicroareaResponse,
)

router = APIRouter()


@router.get("/gestor/controle", summary="Painel do gestor: agregações de controle pressórico")
def painel_gestor_controle(
    co_unidade_saude: Optional[int] = Query(default=None, ge=1, description="Filtrar por UBS/USF"),
    usuario: dict = Depends(get_usuario_obrigatorio),
):
    _ = usuario
    return buscar_painel_gestor_controle_pressorico(co_unidade_saude=co_unidade_saude)


@router.get(
    "/individuos",
    summary="Lista operacional de individuos com hipertensao",
    response_model=IndividuosHipertensaoResponse,
)
def listar_individuos_hipertensos(
    co_cidadao: Optional[int] = Query(default=None, description="Filtro por codigo do cidadao (co_cidadao)"),
    no_cidadao: Optional[str] = Query(default=None, description="Filtro por nome do paciente (contendo)"),
    bairro: Optional[str] = Query(default=None, description="Filtro por bairro normalizado (no_bairro_filtro)"),
    sexo: Optional[str] = Query(default=None, pattern="^[MF]$", description="Filtro por sexo: M ou F"),
    faixa_etaria: Optional[str] = Query(
        default=None,
        pattern="^(18-29|30-39|40-49|50-59|60-64|65\\+)$",
        description="Filtro por faixa etaria",
    ),
    nu_area: Optional[str] = Query(default=None, description="Filtro por area de adscricao (nu_area)"),
    nu_micro_area: Optional[str] = Query(default=None, description="Filtro por microarea de adscricao (nu_micro_area)"),
    co_unidade_saude: Optional[int] = Query(default=None, ge=1, description="Codigo da UBS"),
    st_diabetes: Optional[bool] = Query(default=None, description="Filtro por comorbidade diabetes"),
    data_ultima_medicao_inicio: Optional[date] = Query(default=None, description="Data inicial da ultima medicao"),
    data_ultima_medicao_fim: Optional[date] = Query(default=None, description="Data final da ultima medicao"),
    limite: int = Query(default=50, ge=1, le=500, description="Tamanho da pagina"),
    offset: int = Query(default=0, ge=0, description="Deslocamento para paginacao"),
    usuario: dict = Depends(get_usuario_obrigatorio),
):
    """Lista individuos hipertensos usando filtros clinico-demograficos."""
    _ = usuario

    if (
        data_ultima_medicao_inicio is not None
        and data_ultima_medicao_fim is not None
        and data_ultima_medicao_inicio > data_ultima_medicao_fim
    ):
        raise HTTPException(
            status_code=422,
            detail="data_ultima_medicao_inicio nao pode ser maior que data_ultima_medicao_fim",
        )

    resultado = buscar_individuos_hipertensos(
        co_cidadao=co_cidadao,
        no_cidadao=no_cidadao,
        bairro=bairro,
        sexo=sexo,
        faixa_etaria=faixa_etaria,
        nu_area=nu_area,
        nu_micro_area=nu_micro_area,
        co_unidade_saude=co_unidade_saude,
        st_diabetes=st_diabetes,
        data_ultima_medicao_inicio=data_ultima_medicao_inicio,
        data_ultima_medicao_fim=data_ultima_medicao_fim,
        limite=limite,
        offset=offset,
    )

    return {
        "total": resultado["total"],
        "total_controlados": resultado["total_controlados"],
        "total_descontrolados": resultado["total_descontrolados"],
        "limite": limite,
        "offset": offset,
        "filtros_aplicados": {
            "co_cidadao": co_cidadao,
            "no_cidadao": no_cidadao,
            "bairro": bairro,
            "sexo": sexo,
            "faixa_etaria": faixa_etaria,
            "nu_area": nu_area,
            "nu_micro_area": nu_micro_area,
            "co_unidade_saude": co_unidade_saude,
            "st_diabetes": st_diabetes,
            "data_ultima_medicao_inicio": data_ultima_medicao_inicio,
            "data_ultima_medicao_fim": data_ultima_medicao_fim,
        },
        "dados": resultado["dados"],
    }


@router.get("/kpis", summary="KPIs gerais para o painel do gestor", response_model=KPIsResponse)
def kpis_gerais():
    """
    Retorna os indicadores-chave de saúde:
    total de cadastros, hipertensos e prevalência geral.
    """
    dados = buscar_kpis_gerais()
    return {"dados": dados}


@router.get("/tendencia", summary="Evolução mensal das medições de PA", response_model=TendenciaResponse)
def tendencia(
    ano_inicio: Optional[int] = Query(default=None, description="Ano inicial do período"),
    ano_fim: Optional[int] = Query(default=None, description="Ano final do período"),
    co_unidade_saude: Optional[int] = Query(default=None, description="Código da UBS"),
    bairro: Optional[str] = Query(default=None, description="Nome normalizado do bairro"),
):
    """
    Evolução mensal de medições de pressão arterial.
    Retorna contagem por classificação (normal, elevada, HAS I/II/III) e médias de PAS/PAD.
    """
    dados = buscar_tendencia(
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
        co_unidade_saude=co_unidade_saude,
        bairro=bairro,
    )
    return {
        "total": len(dados),
        "filtros_aplicados": {
            "ano_inicio": ano_inicio,
            "ano_fim": ano_fim,
            "co_unidade_saude": co_unidade_saude,
            "bairro": bairro,
        },
        "dados": dados,
    }


@router.get("/prevalencia", summary="Prevalência de HAS por perfil demográfico (apenas VDC)", response_model=PrevalenciaResponse)
def prevalencia(
    agrupamento: str = Query(
        default="bairro",
        description="Como agrupar: 'bairro', 'sexo', 'faixa_etaria'",
        pattern="^(bairro|sexo|faixa_etaria)$",
    ),
    bairro: Optional[str] = Query(default=None, description="Filtro por bairro (para agrupamentos por sexo/faixa)"),
    ano_inicio: Optional[int] = Query(default=None),
    ano_fim: Optional[int] = Query(default=None),
):
    """
    Prevalência de hipertensão por bairro VDC, sexo ou faixa etária.
    Por padrão filtra apenas residentes de Vitória da Conquista (st_bairro_vdc=TRUE).
    """
    if agrupamento == "bairro":
        dados = buscar_prevalencia_por_bairro(ano_inicio=ano_inicio, ano_fim=ano_fim, apenas_vdc=True)
        nao_identificados = buscar_resumo_nao_identificados(ano_inicio=ano_inicio, ano_fim=ano_fim)
    elif agrupamento == "sexo":
        dados = buscar_prevalencia_por_sexo(bairro=bairro, ano_inicio=ano_inicio, ano_fim=ano_fim)
        nao_identificados = None
    else:
        dados = buscar_prevalencia_por_faixa_etaria(bairro=bairro, ano_inicio=ano_inicio, ano_fim=ano_fim)
        nao_identificados = None

    return {
        "total": len(dados),
        "agrupamento": agrupamento,
        "filtros_aplicados": {"bairro": bairro, "ano_inicio": ano_inicio, "ano_fim": ano_fim},
        "dados": dados,
        "nao_identificados": nao_identificados,
    }


@router.get("/fatores-risco", summary="Comorbidades e fatores de risco em hipertensos", response_model=FatoresRiscoResponse)
def fatores_risco(
    bairro: Optional[str] = Query(default=None),
    ano_inicio: Optional[int] = Query(default=None),
    ano_fim: Optional[int] = Query(default=None),
    multiplos: bool = Query(
        default=False,
        description="Se True, retorna distribuição de múltiplos fatores simultâneos",
    ),
):
    """
    Comparativo de comorbidades entre hipertensos e não-hipertensos.
    Com multiplos=True, retorna distribuição de fatores acumulados em hipertensos.
    """
    if multiplos:
        dados = buscar_multiplos_fatores(bairro=bairro)
        return {"total": len(dados), "tipo": "multiplos_fatores", "dados": dados}

    dados = buscar_comparativo_comorbidades(
        bairro=bairro,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
    )
    return {
        "total": len(dados),
        "tipo": "comparativo_comorbidades",
        "filtros_aplicados": {"bairro": bairro, "ano_inicio": ano_inicio, "ano_fim": ano_fim},
        "dados": dados,
    }


@router.get("/mapa", summary="Dados geográficos por bairro para mapa coroplético", response_model=MapaResponse)
def mapa(
    ano_inicio: Optional[int] = Query(default=None),
    ano_fim: Optional[int] = Query(default=None),
):
    """
    Agrega cadastros por bairro com prevalência de HAS.
    Use no React-Leaflet para colorir o mapa por densidade de hipertensos.
    """
    dados = buscar_dados_mapa(ano_inicio=ano_inicio, ano_fim=ano_fim)
    return {
        "total_bairros": len(dados),
        "filtros_aplicados": {"ano_inicio": ano_inicio, "ano_fim": ano_fim},
        "dados": dados,
    }


@router.get("/mapa-loteamentos", summary="Dados geográficos agregados por Bairro ou Loteamento", response_model=MapaResponse)
def mapa_loteamentos(
    ano_inicio: Optional[int] = Query(default=None),
    ano_fim: Optional[int] = Query(default=None),
):
    """
    Retorna a granularidade máxima disponível.
    Se a fonte do GeoJSON contiver loteamentos e o e-SUS possuir match direto, a linha será de loteamento.
    Senão, agrupará num bloco único como '{Bairro} (loteamento não especificado)'.
    """
    dados = buscar_dados_mapa_loteamentos(ano_inicio=ano_inicio, ano_fim=ano_fim)
    return {
        "total_bairros": len(dados),
        "filtros_aplicados": {"ano_inicio": ano_inicio, "ano_fim": ano_fim},
        "dados": dados,
    }


@router.get("/ubs", summary="Hipertensos e medições por Unidade Básica de Saúde", response_model=UbsResponse)
def ubs(
    ano_inicio: Optional[int] = Query(default=None, description="Ano inicial do período"),
    ano_fim: Optional[int] = Query(default=None, description="Ano final do período"),
):
    """
    Retorna cada UBS com:
      - bairro onde está localizada (tb_unidade_saude.no_bairro)
      - total de pacientes únicos que tiveram PA medida nela
      - quantos têm hipertensão declarada no cadastro individual
      - prevalência de HAS (%)
      - total de medições registradas

    Útil para identificar unidades com maior carga de pacientes hipertensos.
    """
    dados = buscar_dados_ubs(ano_inicio=ano_inicio, ano_fim=ano_fim)
    return {
        "total": len(dados),
        "filtros_aplicados": {"ano_inicio": ano_inicio, "ano_fim": ano_fim},
        "dados": dados,
    }


@router.get("/cobertura-bairros", summary="Cobertura de bairros VDC vs endereços não identificados")
def cobertura_bairros(
    ano_inicio: Optional[int] = Query(default=None),
    ano_fim: Optional[int] = Query(default=None),
):
    """
    Resumo de cobertura geográfica:
    - Quantos cadastros têm bairro VDC identificado
    - Quantos têm endereço não identificado (rural, outro município, inválido)
    - Top categorias dos não-identificados
    """
    return buscar_cobertura_bairros()


@router.get("/bairros", summary="Lista de bairros VDC disponíveis no sistema", response_model=BairrosResponse)
def bairros():
    """Lista todos os bairros VDC com pelo menos um cadastro."""
    lista = buscar_bairros_disponiveis()
    return {"total": len(lista), "bairros": lista}


@router.get("/bairros/exportar", summary="Exporta dados completos dos bairros em JSON")
def exportar_bairros(
    minimo_cadastros: int = Query(
        default=50,
        ge=1,
        description="Mínimo de cadastros para incluir o bairro (filtra bairros com poucos registros)",
    )
):
    """
    Retorna JSON completo com todos os bairros e seus indicadores de saúde.
    Inclui: total de cadastros, hipertensos, prevalência, diabetes, AVC,
    infarto, fumantes, idosos — por bairro canônico normalizado.
    """
    from app.core.database import execute_query
    from app.core.config import settings
    from datetime import datetime

    sql = f"""
    SELECT
        g.no_bairro                                             AS bairro,
        COUNT(*)                                                AS total_cadastros,
        COUNT(*) FILTER (WHERE c.st_hipertensao_arterial = 1)   AS hipertensos,
        ROUND(
            COUNT(*) FILTER (WHERE c.st_hipertensao_arterial = 1)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                        AS prevalencia_pct,
        COUNT(*) FILTER (WHERE c.st_diabetes = 1)               AS n_diabetes,
        COUNT(*) FILTER (WHERE c.st_avc = 1)                    AS n_avc,
        COUNT(*) FILTER (WHERE c.st_infarto = 1)                AS n_infarto,
        COUNT(*) FILTER (WHERE c.st_doenca_cardiaca = 1)        AS n_doenca_cardiaca,
        COUNT(*) FILTER (WHERE c.st_problema_rins = 1)          AS n_problema_rins,
        COUNT(*) FILTER (WHERE c.st_fumante = 1)                AS n_fumantes,
        COUNT(*) FILTER (WHERE c.st_alcool = 1)                 AS n_alcool,
        COUNT(*) FILTER (WHERE c.grupo_idade = 'Idosos (65+)') AS n_idosos,
        ROUND(
            COUNT(*) FILTER (WHERE c.grupo_idade = 'Idosos (65+)')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                        AS pct_idosos
    FROM {settings.DB_SCHEMA}.vw_bairro_canonico c
    INNER JOIN {settings.DB_SCHEMA}.tb_geocodificacao g
        ON {settings.DB_SCHEMA}.normaliza_bairro(g.no_bairro) = {settings.DB_SCHEMA}.normaliza_bairro(c.bairro_canonico)
        AND g.ds_fonte = 'geojson_import'
    WHERE c.st_bairro_vdc = TRUE
    GROUP BY g.no_bairro
    HAVING COUNT(*) >= :minimo
    ORDER BY total_cadastros DESC
    """

    rows = execute_query(sql, {"minimo": minimo_cadastros})

    bairros_data = [
        {k: float(v) if hasattr(v, "__float__") else v for k, v in r.items()}
        for r in rows
    ]

    return {
        "gerado_em": datetime.now().isoformat(),
        "total_bairros": len(bairros_data),
        "minimo_cadastros_filtro": minimo_cadastros,
        "bairros": bairros_data,
    }


@router.get(
    "/distribuicao-area",
    summary="Distribuicao de hipertensao por area de adscricao",
    response_model=DistribuicaoAreaResponse,
)
def distribuicao_area(
    ano_inicio: Optional[int] = Query(default=None, description="Ano inicial do periodo"),
    ano_fim: Optional[int] = Query(default=None, description="Ano final do periodo"),
    bairro: Optional[str] = Query(default=None, description="Filtro opcional por bairro normalizado"),
    usuario: dict = Depends(get_usuario_obrigatorio),
):
    """Distribuicao de cadastros e hipertensao por area (nu_area)."""
    _ = usuario

    if ano_inicio is not None and ano_fim is not None and ano_inicio > ano_fim:
        raise HTTPException(status_code=422, detail="ano_inicio nao pode ser maior que ano_fim")

    dados = buscar_distribuicao_por_area(
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
        bairro=bairro,
    )

    return {
        "total": len(dados),
        "filtros_aplicados": {
            "ano_inicio": ano_inicio,
            "ano_fim": ano_fim,
            "bairro": bairro,
        },
        "dados": dados,
    }


@router.get(
    "/distribuicao-microarea",
    summary="Distribuicao de hipertensao por microarea de adscricao",
    response_model=DistribuicaoMicroareaResponse,
)
def distribuicao_microarea(
    area: Optional[str] = Query(default=None, description="Filtro por area de adscricao (nu_area)"),
    ano_inicio: Optional[int] = Query(default=None, description="Ano inicial do periodo"),
    ano_fim: Optional[int] = Query(default=None, description="Ano final do periodo"),
    bairro: Optional[str] = Query(default=None, description="Filtro opcional por bairro normalizado"),
    usuario: dict = Depends(get_usuario_obrigatorio),
):
    """Distribuicao de cadastros e hipertensao por microarea (nu_area + nu_micro_area)."""
    _ = usuario

    if ano_inicio is not None and ano_fim is not None and ano_inicio > ano_fim:
        raise HTTPException(status_code=422, detail="ano_inicio nao pode ser maior que ano_fim")

    dados = buscar_distribuicao_por_microarea(
        area=area,
        ano_inicio=ano_inicio,
        ano_fim=ano_fim,
        bairro=bairro,
    )

    return {
        "total": len(dados),
        "filtros_aplicados": {
            "area": area,
            "ano_inicio": ano_inicio,
            "ano_fim": ano_fim,
            "bairro": bairro,
        },
        "dados": dados,
    }