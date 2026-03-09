"""
KPIs gerais de obesidade: totais, IMC médio, prevalências e tendência.
"""

from __future__ import annotations
from typing import Optional

from app.core.database import execute_query_pec, execute_query
from app.core.logging_config import setup_logging

logger = setup_logging("ob.analytics.kpis")

_VIEW = "dashboard.mv_obesidade"


def _filtros_where(
    ano_inicio: Optional[int],
    ano_fim: Optional[int],
    bairro: Optional[str],
    co_unidade_saude: Optional[int],
    sexo: Optional[str],
) -> tuple[str, dict]:
    clauses = ["1=1"]
    params: dict = {}
    if ano_inicio:
        clauses.append("ano >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        clauses.append("ano <= :ano_fim")
        params["ano_fim"] = ano_fim
    if bairro:
        clauses.append("no_bairro_filtro = :bairro")
        params["bairro"] = bairro
    if co_unidade_saude:
        clauses.append("co_unidade_saude = :ubs")
        params["ubs"] = co_unidade_saude
    if sexo:
        clauses.append("sg_sexo = :sexo")
        params["sexo"] = sexo.upper()
    return " AND ".join(clauses), params


def get_kpis(
    ano_inicio: Optional[int] = None,
    ano_fim: Optional[int] = None,
    bairro: Optional[str] = None,
    co_unidade_saude: Optional[int] = None,
    sexo: Optional[str] = None,
) -> dict:
    where, params = _filtros_where(ano_inicio, ano_fim, bairro, co_unidade_saude, sexo)

    sql = f"""
        SELECT
            COUNT(*)                                                    AS total_medicoes,
            COUNT(DISTINCT co_cidadao)                                  AS total_adultos,
            ROUND(AVG(imc)::NUMERIC, 2)                                 AS imc_medio,
            ROUND(100.0 * SUM(CASE WHEN imc >= 25 THEN 1 ELSE 0 END) / COUNT(*), 1) AS prevalencia_sobrepeso_pct,
            ROUND(100.0 * SUM(CASE WHEN imc >= 30 THEN 1 ELSE 0 END) / COUNT(*), 1) AS prevalencia_obesidade_pct,
            ROUND(100.0 * SUM(CASE WHEN imc >= 35 THEN 1 ELSE 0 END) / COUNT(*), 1) AS prevalencia_obesidade_g2g3_pct
        FROM {_VIEW}
        WHERE {where}
    """
    rows = execute_query(sql, params)
    row = rows[0] if rows else {}

    # Tendência mensal (regressão linear simples via SQL)
    sql_trend = f"""
        SELECT
            REGR_SLOPE(imc_medio, mes_num) AS slope
        FROM (
            SELECT
                AVG(imc)                             AS imc_medio,
                ROW_NUMBER() OVER (ORDER BY mes_ano) AS mes_num
            FROM {_VIEW}
            WHERE {where}
            GROUP BY mes_ano
            HAVING COUNT(*) >= 10
        ) t
    """
    trend_rows = execute_query(sql_trend, params)
    tendencia = round(float(trend_rows[0]["slope"] or 0), 4) if trend_rows else 0.0

    return {
        "total_medicoes": int(row.get("total_medicoes") or 0),
        "total_adultos": int(row.get("total_adultos") or 0),
        "imc_medio": float(row.get("imc_medio") or 0),
        "prevalencia_sobrepeso_pct": float(row.get("prevalencia_sobrepeso_pct") or 0),
        "prevalencia_obesidade_pct": float(row.get("prevalencia_obesidade_pct") or 0),
        "prevalencia_obesidade_g2g3_pct": float(row.get("prevalencia_obesidade_g2g3_pct") or 0),
        "tendencia_mensal": tendencia,
    }
