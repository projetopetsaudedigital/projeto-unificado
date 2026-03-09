"""
Tendência temporal da hemoglobina glicada.
Evolução da média de HbA1c e controle vs descontrole por mês/ano.
"""

from app.core.database import execute_query
from app.core.config import settings


def buscar_tendencia_hba1c(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    bairro: str | None = None,
) -> list[dict]:
    """Média de HbA1c por mês."""
    schema = settings.DB_SCHEMA
    filtros = ["controle_glicemico IS NOT NULL"]
    params: dict = {}

    if ano_inicio:
        filtros.append("ano >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("ano <= :ano_fim")
        params["ano_fim"] = ano_fim
    if bairro:
        filtros.append("UPPER(no_bairro_filtro) = UPPER(:bairro)")
        params["bairro"] = bairro

    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        mes_ano,
        ano,
        mes,
        ROUND(AVG(hba1c)::NUMERIC, 2)                                        AS media_hba1c,
        COUNT(*)                                                              AS total_exames,
        COUNT(DISTINCT co_cidadao)                                           AS total_pacientes,
        COUNT(*) FILTER (WHERE controle_glicemico = 'Controlado')            AS controlados,
        COUNT(*) FILTER (WHERE controle_glicemico = 'Descontrolado')         AS descontrolados,
        ROUND(
            COUNT(*) FILTER (WHERE controle_glicemico = 'Controlado')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                                    AS pct_controlados
    FROM {schema}.mv_dm_hemoglobina
    WHERE {where}
    GROUP BY mes_ano, ano, mes
    ORDER BY mes_ano
    """
    rows = execute_query(sql, params)
    return [dict(r) for r in rows]


def buscar_hba1c_por_faixa(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    bairro: str | None = None,
) -> list[dict]:
    """Distribuição (histograma) dos valores de HbA1c."""
    schema = settings.DB_SCHEMA
    filtros = ["hba1c IS NOT NULL"]
    params: dict = {}

    if ano_inicio:
        filtros.append("ano >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("ano <= :ano_fim")
        params["ano_fim"] = ano_fim
    if bairro:
        filtros.append("UPPER(no_bairro_filtro) = UPPER(:bairro)")
        params["bairro"] = bairro

    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        ROUND(hba1c::NUMERIC, 1) AS faixa_hba1c,
        COUNT(*)                  AS quantidade
    FROM {schema}.mv_dm_hemoglobina
    WHERE {where}
    GROUP BY ROUND(hba1c::NUMERIC, 1)
    ORDER BY faixa_hba1c
    """
    return execute_query(sql, params)


def buscar_hba1c_por_faixa_etaria(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    """Média de HbA1c por faixa etária."""
    schema = settings.DB_SCHEMA
    filtros = ["hba1c IS NOT NULL"]
    params: dict = {}

    if ano_inicio:
        filtros.append("ano >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("ano <= :ano_fim")
        params["ano_fim"] = ano_fim

    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        grupo_etario,
        ROUND(AVG(hba1c)::NUMERIC, 2) AS media_hba1c,
        COUNT(*)                       AS total_exames,
        CASE grupo_etario
            WHEN 'adulto'      THEN 7.0
            WHEN 'idoso_65_79' THEN 7.5
            WHEN 'idoso_80+'   THEN 8.0
            ELSE 7.0
        END AS meta_sbd
    FROM {schema}.mv_dm_hemoglobina
    WHERE {where}
    GROUP BY grupo_etario
    ORDER BY grupo_etario
    """
    return execute_query(sql, params)


def buscar_hba1c_por_sexo(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    """Média de HbA1c por sexo."""
    schema = settings.DB_SCHEMA
    filtros = ["hba1c IS NOT NULL", "ds_sexo IS NOT NULL"]
    params: dict = {}

    if ano_inicio:
        filtros.append("ano >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("ano <= :ano_fim")
        params["ano_fim"] = ano_fim

    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        ds_sexo                        AS sexo,
        sg_sexo,
        ROUND(AVG(hba1c)::NUMERIC, 2)  AS media_hba1c,
        COUNT(*)                        AS total_exames
    FROM {schema}.mv_dm_hemoglobina
    WHERE {where}
    GROUP BY ds_sexo, sg_sexo
    ORDER BY media_hba1c DESC
    """
    return execute_query(sql, params)
