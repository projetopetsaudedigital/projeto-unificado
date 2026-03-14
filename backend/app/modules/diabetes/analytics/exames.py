"""
Registros brutos de exames de hemoglobina glicada.

Join: tb_exame_hemoglobina_glicada → tb_exame_requisitado → tb_prontuario → tb_cidadao.
"""

from datetime import date, datetime
from typing import Optional

from app.core.database import execute_query_pec


def buscar_exames_hemoglobina_glicada(
    co_cidadao: Optional[int] = None,
    co_prontuario: Optional[int] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limit: int = 100,
) -> list[dict]:
    """
    Retorna registros brutos de exames de HbA1c (tabela PEC).
    """
    params = {"limit": min(max(1, limit), 500)}
    conditions = ["hg.vl_hemoglobina_glicada IS NOT NULL"]

    if co_cidadao is not None:
        conditions.append("p.co_cidadao = :co_cidadao")
        params["co_cidadao"] = co_cidadao
    if co_prontuario is not None:
        conditions.append("p.co_seq_prontuario = :co_prontuario")
        params["co_prontuario"] = co_prontuario
    if data_inicio is not None:
        conditions.append("er.dt_realizacao::date >= :data_inicio")
        params["data_inicio"] = data_inicio
    if data_fim is not None:
        conditions.append("er.dt_realizacao::date <= :data_fim")
        params["data_fim"] = data_fim

    where_clause = " AND ".join(conditions)

    sql = f"""
    SELECT
        hg.co_seq_exame_hemoglobina_glicd,
        hg.co_exame_requisitado,
        hg.vl_hemoglobina_glicada,
        er.dt_realizacao AS dt_exame,
        p.co_seq_prontuario,
        c.co_seq_cidadao AS co_cidadao
    FROM pec.tb_exame_hemoglobina_glicada hg
    INNER JOIN pec.tb_exame_requisitado er
        ON hg.co_exame_requisitado = er.co_seq_exame_requisitado
    INNER JOIN pec.tb_prontuario p
        ON er.co_prontuario = p.co_seq_prontuario
    INNER JOIN pec.tb_cidadao c
        ON p.co_cidadao = c.co_seq_cidadao
    WHERE {where_clause}
    ORDER BY er.dt_realizacao DESC
    LIMIT :limit
    """
    rows = execute_query_pec(sql, params)

    for row in rows:
        dt = row.get("dt_exame")
        if isinstance(dt, (date, datetime)):
            row["dt_exame"] = dt.isoformat() if dt else None

    return rows
