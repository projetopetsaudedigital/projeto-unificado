"""
Evolução mensal do IMC e distribuição de classificação ao longo do tempo.
"""

from __future__ import annotations
from typing import Optional

from app.core.database import execute_query
from app.core.logging_config import setup_logging

logger = setup_logging("ob.analytics.tendencia")

_VIEW = "dashboard.mv_obesidade"


def get_tendencia(
    ano_inicio: Optional[int] = None,
    ano_fim: Optional[int] = None,
    bairro: Optional[str] = None,
    co_unidade_saude: Optional[int] = None,
) -> list[dict]:
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
    where = " AND ".join(clauses)

    sql = f"""
        SELECT
            TO_CHAR(mes_ano, 'YYYY-MM')                                    AS mes_ano,
            ROUND(AVG(imc)::NUMERIC, 2)                                    AS imc_medio,
            COUNT(*)                                                        AS total_medicoes,
            ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Baixo Peso'    THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_baixo_peso,
            ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Normal'        THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_normal,
            ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Sobrepeso'     THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_sobrepeso,
            ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Obesidade I'   THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_obesidade_i,
            ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Obesidade II'  THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_obesidade_ii,
            ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Obesidade III' THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_obesidade_iii
        FROM {_VIEW}
        WHERE {where}
        GROUP BY mes_ano
        HAVING COUNT(*) >= 5
        ORDER BY mes_ano
    """
    rows = execute_query(sql, params)
    return [
        {
            "mes_ano": r["mes_ano"],
            "imc_medio": float(r["imc_medio"] or 0),
            "total_medicoes": int(r["total_medicoes"]),
            "pct_baixo_peso": float(r["pct_baixo_peso"] or 0),
            "pct_normal": float(r["pct_normal"] or 0),
            "pct_sobrepeso": float(r["pct_sobrepeso"] or 0),
            "pct_obesidade_i": float(r["pct_obesidade_i"] or 0),
            "pct_obesidade_ii": float(r["pct_obesidade_ii"] or 0),
            "pct_obesidade_iii": float(r["pct_obesidade_iii"] or 0),
        }
        for r in rows
    ]
