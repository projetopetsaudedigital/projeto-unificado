"""
Distribuição das 6 classes de IMC por classificação, sexo e faixa etária.
"""

from __future__ import annotations
from typing import Optional

from app.core.database import execute_query
from app.core.logging_config import setup_logging

logger = setup_logging("ob.analytics.distribuicao")

_VIEW = "dashboard.mv_obesidade"


def _where(ano_inicio, ano_fim, bairro, co_unidade_saude) -> tuple[str, dict]:
    clauses = ["1=1"]
    params: dict = {}
    if ano_inicio:
        clauses.append("ano >= :ano_inicio"); params["ano_inicio"] = ano_inicio
    if ano_fim:
        clauses.append("ano <= :ano_fim"); params["ano_fim"] = ano_fim
    if bairro:
        clauses.append("no_bairro_filtro = :bairro"); params["bairro"] = bairro
    if co_unidade_saude:
        clauses.append("co_unidade_saude = :ubs"); params["ubs"] = co_unidade_saude
    return " AND ".join(clauses), params


def get_distribuicao(
    ano_inicio: Optional[int] = None,
    ano_fim: Optional[int] = None,
    bairro: Optional[str] = None,
    co_unidade_saude: Optional[int] = None,
) -> dict:
    where, params = _where(ano_inicio, ano_fim, bairro, co_unidade_saude)

    # Por classificação
    sql_class = f"""
        SELECT
            classificacao_imc,
            COUNT(*) AS total
        FROM {_VIEW}
        WHERE {where}
        GROUP BY classificacao_imc
        ORDER BY
            CASE classificacao_imc
                WHEN 'Baixo Peso'   THEN 1
                WHEN 'Normal'       THEN 2
                WHEN 'Sobrepeso'    THEN 3
                WHEN 'Obesidade I'  THEN 4
                WHEN 'Obesidade II' THEN 5
                ELSE 6
            END
    """
    rows_class = execute_query(sql_class, params)
    total = sum(r["total"] for r in rows_class) or 1
    por_classificacao = [
        {
            "classificacao": r["classificacao_imc"],
            "total": int(r["total"]),
            "percentual": round(100.0 * int(r["total"]) / total, 1),
        }
        for r in rows_class
    ]

    # Por sexo
    sql_sexo = f"""
        SELECT
            COALESCE(ds_sexo, 'Não informado')                             AS sexo,
            COUNT(*)                                                        AS total,
            ROUND(AVG(imc)::NUMERIC, 2)                                    AS imc_medio,
            ROUND(100.0 * SUM(CASE WHEN imc >= 30 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_obesidade
        FROM {_VIEW}
        WHERE {where}
        GROUP BY ds_sexo
        ORDER BY total DESC
    """
    rows_sexo = execute_query(sql_sexo, params)
    por_sexo = [
        {
            "sexo": r["sexo"],
            "total": int(r["total"]),
            "imc_medio": float(r["imc_medio"] or 0),
            "pct_obesidade": float(r["pct_obesidade"] or 0),
        }
        for r in rows_sexo
    ]

    # Por faixa etária
    sql_faixa = f"""
        SELECT
            faixa_etaria,
            COUNT(*)                                                        AS total,
            ROUND(AVG(imc)::NUMERIC, 2)                                    AS imc_medio,
            ROUND(100.0 * SUM(CASE WHEN imc >= 30 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_obesidade
        FROM {_VIEW}
        WHERE {where}
        GROUP BY faixa_etaria
        ORDER BY faixa_etaria
    """
    rows_faixa = execute_query(sql_faixa, params)
    por_faixa_etaria = [
        {
            "faixa_etaria": r["faixa_etaria"],
            "total": int(r["total"]),
            "imc_medio": float(r["imc_medio"] or 0),
            "pct_obesidade": float(r["pct_obesidade"] or 0),
        }
        for r in rows_faixa
    ]

    return {
        "por_classificacao": por_classificacao,
        "por_sexo": por_sexo,
        "por_faixa_etaria": por_faixa_etaria,
    }
