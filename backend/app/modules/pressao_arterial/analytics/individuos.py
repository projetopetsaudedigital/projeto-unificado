"""
Listagem operacional de individuos hipertensos.

Regra aplicada:
- Considera apenas medições dos últimos 365 dias.
- Consolida múltiplas medições no mesmo dia por mediana diária (PAS/PAD).
- Usa até os 3 dias mais recentes por indivíduo.
- Classifica HAS por mediana final: PAS >= 140 ou PAD >= 90.
- Sem medição no período: indivíduo é excluído.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.core.config import settings
from app.core.database import execute_query


def buscar_individuos_hipertensos(
    *,
    bairro: Optional[str] = None,
    sexo: Optional[str] = None,
    faixa_etaria: Optional[str] = None,
    co_unidade_saude: Optional[int] = None,
    st_diabetes: Optional[bool] = None,
    data_ultima_medicao_inicio: Optional[date] = None,
    data_ultima_medicao_fim: Optional[date] = None,
    limite: int = 50,
    offset: int = 0,
) -> dict:
    """Retorna total e página de indivíduos com HAS pela regra de mediana."""
    schema = settings.DB_SCHEMA
    filtros = ["(hip.mediana_pas >= 140 OR hip.mediana_pad >= 90)"]
    params: dict = {"limite": limite, "offset": offset}

    if bairro:
        filtros.append("c.no_bairro_filtro = :bairro")
        params["bairro"] = bairro

    if sexo:
        filtros.append("UPPER(c.sg_sexo) = :sexo")
        params["sexo"] = sexo.upper()

    if faixa_etaria:
        filtros.append("c.faixa_etaria = :faixa_etaria")
        params["faixa_etaria"] = faixa_etaria

    if co_unidade_saude is not None:
        filtros.append("hip.co_unidade_saude_ultima = :co_unidade_saude")
        params["co_unidade_saude"] = co_unidade_saude

    if st_diabetes is not None:
        filtros.append("COALESCE(c.st_diabetes, 0) = :st_diabetes")
        params["st_diabetes"] = 1 if st_diabetes else 0

    if data_ultima_medicao_inicio is not None:
        filtros.append("hip.dt_ultima_medicao >= :data_ultima_medicao_inicio")
        params["data_ultima_medicao_inicio"] = data_ultima_medicao_inicio

    if data_ultima_medicao_fim is not None:
        filtros.append("hip.dt_ultima_medicao <= :data_ultima_medicao_fim")
        params["data_ultima_medicao_fim"] = data_ultima_medicao_fim

    where = " AND ".join(filtros)

    cte_sql = f"""
    WITH medicoes_validas AS (
        SELECT
            mc.co_cidadao,
            mc.co_seq_medicao,
            mc.dt_medicao,
            mc.dt_medicao::date AS dia_medicao,
            mc.co_unidade_saude,
            SPLIT_PART(mc.nu_medicao_pressao_arterial, '/', 1)::NUMERIC AS pas,
            SPLIT_PART(mc.nu_medicao_pressao_arterial, '/', 2)::NUMERIC AS pad,
            ROW_NUMBER() OVER (
                PARTITION BY mc.co_cidadao, mc.dt_medicao::date
                ORDER BY mc.dt_medicao DESC, mc.co_seq_medicao DESC
            ) AS rn_ultima_no_dia
        FROM {schema}.mv_pa_medicoes_cidadaos mc
        WHERE mc.dt_medicao >= (CURRENT_DATE - INTERVAL '365 days')
          AND mc.nu_medicao_pressao_arterial ~ '^[0-9]+/[0-9]+$'
    ),
    medicoes_filtradas AS (
        SELECT
            co_cidadao,
            dt_medicao,
            dia_medicao,
            co_unidade_saude,
            pas,
            pad,
            rn_ultima_no_dia
        FROM medicoes_validas
        WHERE pas BETWEEN 50 AND 300
          AND pad BETWEEN 30 AND 200
          AND pas > pad
    ),
    mediana_por_dia AS (
        SELECT
            co_cidadao,
            dia_medicao,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pas) AS pas_dia,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pad) AS pad_dia,
            MAX(co_unidade_saude) FILTER (WHERE rn_ultima_no_dia = 1) AS co_unidade_saude_ultima_dia
        FROM medicoes_filtradas
        GROUP BY co_cidadao, dia_medicao
    ),
    ultimos_tres_dias AS (
        SELECT
            co_cidadao,
            dia_medicao,
            pas_dia,
            pad_dia,
            co_unidade_saude_ultima_dia,
            ROW_NUMBER() OVER (
                PARTITION BY co_cidadao
                ORDER BY dia_medicao DESC
            ) AS rn
        FROM mediana_por_dia
    ),
    hipertensao_por_mediana AS (
        SELECT
            co_cidadao,
            COUNT(*)::INTEGER AS n_medicoes_usadas,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pas_dia) AS mediana_pas,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pad_dia) AS mediana_pad,
            MAX(dia_medicao) AS dt_ultima_medicao,
            (ARRAY_AGG(co_unidade_saude_ultima_dia ORDER BY dia_medicao DESC))[1] AS co_unidade_saude_ultima
        FROM ultimos_tres_dias
        WHERE rn <= 3
        GROUP BY co_cidadao
    )
    """

    from_sql = f"""
    FROM hipertensao_por_mediana hip
    INNER JOIN {schema}.mv_pa_cadastros c
        ON c.co_cidadao = hip.co_cidadao
    WHERE {where}
    """

    total_sql = f"""
    {cte_sql}
    SELECT COUNT(*) AS total
    {from_sql}
    """

    dados_sql = f"""
    {cte_sql}
    SELECT
        c.co_cidadao,
        ROUND(hip.mediana_pas::NUMERIC, 1) AS mediana_pas,
        ROUND(hip.mediana_pad::NUMERIC, 1) AS mediana_pad,
        hip.n_medicoes_usadas,
        hip.dt_ultima_medicao
    {from_sql}
    ORDER BY c.co_cidadao ASC
    LIMIT :limite OFFSET :offset
    """

    total_rows = execute_query(total_sql, params)
    dados = execute_query(dados_sql, params)

    total = int(total_rows[0]["total"]) if total_rows else 0
    return {
        "total": total,
        "dados": dados,
    }
