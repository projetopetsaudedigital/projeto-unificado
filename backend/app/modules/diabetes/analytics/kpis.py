"""KPIs gerais do módulo de Diabetes."""

from app.core.database import execute_query
from app.core.config import settings


def buscar_kpis_diabetes() -> dict:
    schema = settings.DB_SCHEMA
    sql = f"""
    SELECT
        COUNT(DISTINCT co_cidadao)                                          AS total_diabeticos,
        COUNT(*)                                                            AS total_exames,
        ROUND(AVG(hba1c)::NUMERIC, 1)                                       AS media_hba1c,
        COUNT(*) FILTER (WHERE controle_glicemico = 'Controlado')           AS total_controlados,
        COUNT(*) FILTER (WHERE controle_glicemico = 'Descontrolado')        AS total_descontrolados,
        ROUND(
            COUNT(*) FILTER (WHERE controle_glicemico = 'Controlado')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                                   AS pct_controlados,
        COUNT(DISTINCT co_cidadao) FILTER (WHERE grupo_etario = 'adulto')   AS total_adultos,
        COUNT(DISTINCT co_cidadao) FILTER (WHERE grupo_etario != 'adulto')  AS total_idosos
    FROM {schema}.mv_dm_hemoglobina
    WHERE controle_glicemico IS NOT NULL
    """
    rows = execute_query(sql, {})
    return rows[0] if rows else {}
