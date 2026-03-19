"""
Distribuicao de cadastros e hipertensao por area de adscricao.

Consulta baseada na view materializada mv_pa_cadastros (um cadastro por cidadao),
com agrupamento em nu_area e filtros opcionais por periodo e bairro.
"""

from app.core.config import settings
from app.core.database import execute_query


def buscar_distribuicao_por_area(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    bairro: str | None = None,
) -> list[dict]:
    """Retorna distribuicao de hipertensao por area de adscricao (nu_area)."""
    schema = settings.DB_SCHEMA
    filtros = ["c.nu_area IS NOT NULL", "NULLIF(TRIM(c.nu_area), '') IS NOT NULL"]
    params: dict = {}

    if ano_inicio:
        filtros.append("c.ano_cadastro >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("c.ano_cadastro <= :ano_fim")
        params["ano_fim"] = ano_fim
    if bairro:
        filtros.append("UPPER(c.no_bairro_filtro) = UPPER(:bairro)")
        params["bairro"] = bairro

    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        c.nu_area                                                   AS area,
        COUNT(*)                                                    AS total_cadastros,
        COUNT(*) FILTER (WHERE c.st_hipertensao_arterial = 1)      AS hipertensos,
        ROUND(
            COUNT(*) FILTER (WHERE c.st_hipertensao_arterial = 1)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                           AS prevalencia_pct
    FROM {schema}.mv_pa_cadastros c
    WHERE {where}
    GROUP BY c.nu_area
    ORDER BY hipertensos DESC, c.nu_area
    """

    return execute_query(sql, params)
