"""
Análise de controle glicêmico por grupo etário e ao longo do tempo.
Baseado nos critérios SBD 2024 (diferentes limiares para adultos e idosos).
"""

from app.core.database import execute_query
from app.core.config import settings


def buscar_controle_por_grupo(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    bairro: str | None = None,
) -> list[dict]:
    """Controlados vs descontrolados por grupo etário."""
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
        grupo_etario,
        controle_glicemico,
        COUNT(*)                                                    AS total,
        ROUND(AVG(hba1c)::NUMERIC, 2)                               AS media_hba1c,
        ROUND(MIN(hba1c)::NUMERIC, 1)                               AS min_hba1c,
        ROUND(MAX(hba1c)::NUMERIC, 1)                               AS max_hba1c
    FROM {schema}.mv_dm_hemoglobina
    WHERE {where}
    GROUP BY grupo_etario, controle_glicemico
    ORDER BY grupo_etario, controle_glicemico
    """
    return execute_query(sql, params)


def buscar_tendencia_controle_anual(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    """Evolução anual de controlados vs descontrolados (para gráfico de área empilhada)."""
    schema = settings.DB_SCHEMA
    filtros = ["controle_glicemico IS NOT NULL"]
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
        ano,
        controle_glicemico,
        grupo_etario,
        COUNT(*)                       AS quantidade,
        ROUND(AVG(hba1c)::NUMERIC, 2)  AS media_hba1c
    FROM {schema}.mv_dm_hemoglobina
    WHERE {where}
    GROUP BY ano, controle_glicemico, grupo_etario
    ORDER BY ano, grupo_etario, controle_glicemico
    """
    return execute_query(sql, params)


def buscar_controle_por_bairro(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    """Controle glicêmico por bairro — para mapa."""
    schema = settings.DB_SCHEMA
    filtros = ["controle_glicemico IS NOT NULL", "no_bairro_filtro IS NOT NULL"]
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
        no_bairro_filtro                                                   AS bairro,
        COUNT(DISTINCT co_cidadao)                                         AS total_pacientes,
        COUNT(*)                                                           AS total_exames,
        COUNT(*) FILTER (WHERE controle_glicemico = 'Controlado')          AS controlados,
        COUNT(*) FILTER (WHERE controle_glicemico = 'Descontrolado')       AS descontrolados,
        ROUND(AVG(hba1c)::NUMERIC, 2)                                      AS media_hba1c,
        ROUND(
            COUNT(*) FILTER (WHERE controle_glicemico = 'Controlado')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                                  AS pct_controlados
    FROM {schema}.mv_dm_hemoglobina
    WHERE {where}
    GROUP BY no_bairro_filtro
    HAVING COUNT(DISTINCT co_cidadao) >= 5
    ORDER BY total_pacientes DESC
    """
    return execute_query(sql, params)


def buscar_comorbidades_vs_controle() -> list[dict]:
    """
    Taxa de comorbidades em pacientes controlados vs descontrolados.
    Mostra o impacto de cada condição no controle glicêmico.
    """
    schema = settings.DB_SCHEMA

    condicoes = [
        ("st_hipertensao",       "Hipertensão"),
        ("st_doenca_cardiaca",   "Doença cardíaca"),
        ("st_insuf_cardiaca",    "Insuf. cardíaca"),
        ("st_infarto",           "Infarto"),
        ("st_problema_rins",     "Problema renal"),
        ("st_avc",               "AVC/Derrame"),
        ("st_fumante",           "Fumante"),
        ("st_alcool",            "Álcool"),
        ("st_doenca_respiratoria","Doença respiratória"),
        ("st_cancer",            "Câncer"),
    ]

    resultados = []
    for coluna, label in condicoes:
        sql = f"""
        SELECT
            :label                                                          AS fator,
            :coluna                                                         AS coluna,
            SUM(CASE WHEN controle_glicemico = 'Controlado'   AND {coluna} = 1 THEN 1 ELSE 0 END)   AS n_controlados_com,
            SUM(CASE WHEN controle_glicemico = 'Controlado'                     THEN 1 ELSE 0 END)   AS n_controlados_total,
            SUM(CASE WHEN controle_glicemico = 'Descontrolado' AND {coluna} = 1 THEN 1 ELSE 0 END)   AS n_descontrolados_com,
            SUM(CASE WHEN controle_glicemico = 'Descontrolado'                  THEN 1 ELSE 0 END)   AS n_descontrolados_total
        FROM {schema}.mv_dm_hemoglobina
        WHERE controle_glicemico IS NOT NULL
        """
        rows = execute_query(sql, {"label": label, "coluna": coluna})
        if rows:
            r = rows[0]
            nc   = int(r["n_controlados_com"]    or 0)
            nt_c = int(r["n_controlados_total"]  or 0)
            nd   = int(r["n_descontrolados_com"] or 0)
            nt_d = int(r["n_descontrolados_total"] or 0)
            resultados.append({
                "fator":               label,
                "coluna":              coluna,
                "pct_controlados":     round(nc / nt_c * 100, 1) if nt_c else None,
                "pct_descontrolados":  round(nd / nt_d * 100, 1) if nt_d else None,
                "n_controlados":       nc,
                "n_descontrolados":    nd,
            })

    return resultados
