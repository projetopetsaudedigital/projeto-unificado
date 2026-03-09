"""
Prevalência de comorbidades estratificada por classificação de IMC.
"""

from __future__ import annotations
from typing import Optional

from app.core.database import execute_query
from app.core.logging_config import setup_logging

logger = setup_logging("ob.analytics.fatores_risco")

_VIEW = "dashboard.mv_obesidade"

_COMORBIDADES = {
    "Hipertensão Arterial": "st_hipertensao",
    "Diabetes": "st_diabete",
    "Doença Cardíaca": "st_doenca_cardiaca",
    "Doença Respiratória": "st_doenca_respiratoria",
    "AVC": "st_avc",
    "Problema nos Rins": "st_problema_rins",
    "Fumante": "st_fumante",
    "Uso de Álcool": "st_alcool",
}


def get_fatores_risco(
    ano_inicio: Optional[int] = None,
    ano_fim: Optional[int] = None,
    bairro: Optional[str] = None,
    co_unidade_saude: Optional[int] = None,
) -> list[dict]:
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
    where = " AND ".join(clauses)

    # Monta sub-selects para cada comorbidade por classe IMC
    selects = []
    for label, col in _COMORBIDADES.items():
        selects.append(f"""
            SELECT
                '{label}'                                                AS comorbidade,
                ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Baixo Peso'   AND {col} = 1 THEN 1 ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN classificacao_imc = 'Baixo Peso'   THEN 1 ELSE 0 END), 0), 1) AS pct_baixo_peso,
                ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Normal'       AND {col} = 1 THEN 1 ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN classificacao_imc = 'Normal'       THEN 1 ELSE 0 END), 0), 1) AS pct_normal,
                ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Sobrepeso'    AND {col} = 1 THEN 1 ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN classificacao_imc = 'Sobrepeso'    THEN 1 ELSE 0 END), 0), 1) AS pct_sobrepeso,
                ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Obesidade I'  AND {col} = 1 THEN 1 ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN classificacao_imc = 'Obesidade I'  THEN 1 ELSE 0 END), 0), 1) AS pct_obesidade_i,
                ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Obesidade II' AND {col} = 1 THEN 1 ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN classificacao_imc = 'Obesidade II' THEN 1 ELSE 0 END), 0), 1) AS pct_obesidade_ii,
                ROUND(100.0 * SUM(CASE WHEN classificacao_imc = 'Obesidade III' AND {col} = 1 THEN 1 ELSE 0 END)
                    / NULLIF(SUM(CASE WHEN classificacao_imc = 'Obesidade III' THEN 1 ELSE 0 END), 0), 1) AS pct_obesidade_iii
            FROM {_VIEW}
            WHERE {where}
        """)

    sql = " UNION ALL ".join(selects) + " ORDER BY comorbidade"
    rows = execute_query(sql, params)

    return [
        {
            "comorbidade": r["comorbidade"],
            "pct_baixo_peso": float(r["pct_baixo_peso"] or 0),
            "pct_normal": float(r["pct_normal"] or 0),
            "pct_sobrepeso": float(r["pct_sobrepeso"] or 0),
            "pct_obesidade_i": float(r["pct_obesidade_i"] or 0),
            "pct_obesidade_ii": float(r["pct_obesidade_ii"] or 0),
            "pct_obesidade_iii": float(r["pct_obesidade_iii"] or 0),
        }
        for r in rows
    ]


def get_bairros(
    ano_inicio: Optional[int] = None,
    ano_fim: Optional[int] = None,
    co_unidade_saude: Optional[int] = None,
) -> list[dict]:
    clauses = ["no_bairro_filtro IS NOT NULL"]
    params: dict = {}
    if ano_inicio:
        clauses.append("ano >= :ano_inicio"); params["ano_inicio"] = ano_inicio
    if ano_fim:
        clauses.append("ano <= :ano_fim"); params["ano_fim"] = ano_fim
    if co_unidade_saude:
        clauses.append("co_unidade_saude = :ubs"); params["ubs"] = co_unidade_saude
    where = " AND ".join(clauses)

    sql = f"""
        SELECT
            no_bairro_filtro                                               AS bairro,
            COUNT(*)                                                       AS total_medicoes,
            COUNT(DISTINCT co_cidadao)                                     AS total_adultos,
            ROUND(AVG(imc)::NUMERIC, 2)                                    AS imc_medio,
            ROUND(100.0 * SUM(CASE WHEN imc >= 30 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_obesidade,
            ROUND(100.0 * SUM(CASE WHEN imc >= 35 THEN 1 ELSE 0 END) / COUNT(*), 1) AS pct_obesidade_g2g3
        FROM {_VIEW}
        WHERE {where}
        GROUP BY no_bairro_filtro
        HAVING COUNT(*) >= 10
        ORDER BY pct_obesidade DESC
    """
    rows = execute_query(sql, params)
    return [
        {
            "bairro": r["bairro"],
            "total_medicoes": int(r["total_medicoes"]),
            "total_adultos": int(r["total_adultos"]),
            "imc_medio": float(r["imc_medio"] or 0),
            "pct_obesidade": float(r["pct_obesidade"] or 0),
            "pct_obesidade_g2g3": float(r["pct_obesidade_g2g3"] or 0),
        }
        for r in rows
    ]
