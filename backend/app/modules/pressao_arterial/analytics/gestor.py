"""
Analytics para painel do gestor — controle pressórico.

Constrói uma base por cidadão (últimos 365 dias) usando a mesma regra do operacional:
- Mediana diária de PAS/PAD
- Considera até os 3 dias mais recentes por cidadão
- Status: Controlado se mediana recente < 140/90, senão Descontrolado

E agrega por:
- USF/UBS (co_unidade_saude_ultima)
- Área e microárea
- Sexo
- Faixa etária
"""

from __future__ import annotations

from typing import Optional

from app.core.config import settings
from app.core.database import execute_query


def buscar_painel_gestor_controle_pressorico(
    *,
    co_unidade_saude: Optional[int] = None,
) -> dict:
    """
    Retorna agregações para o painel do gestor.

    Se co_unidade_saude for informado, filtra a base para aquela unidade (útil para equipe/leitor).
    """
    schema = settings.DB_SCHEMA
    filtros = ["1=1"]
    params: dict = {}

    if co_unidade_saude is not None:
        filtros.append("hip.co_unidade_saude_ultima = :co_unidade_saude")
        params["co_unidade_saude"] = co_unidade_saude

    where = " AND ".join(filtros)

    base_cte = f"""
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
    ),
    base AS (
        SELECT
            hip.co_cidadao,
            hip.n_medicoes_usadas,
            hip.co_unidade_saude_ultima,
            c.nu_area,
            c.nu_micro_area,
            c.sg_sexo,
            c.faixa_etaria,
            CASE
                WHEN hip.mediana_pas < 140 AND hip.mediana_pad < 90 THEN 'Controlado'
                ELSE 'Descontrolado'
            END AS status_atual
        FROM hipertensao_por_mediana hip
        INNER JOIN {schema}.mv_pa_cadastros c
            ON c.co_cidadao = hip.co_cidadao
    )
    """

    # 1) Controlados vs descontrolados por USF (unidade)
    por_usf_sql = f"""
    {base_cte}
    SELECT
        b.co_unidade_saude_ultima AS co_unidade_saude,
        u.no_unidade_saude,
        COUNT(*) FILTER (WHERE b.status_atual = 'Controlado') AS controlados,
        COUNT(*) FILTER (WHERE b.status_atual = 'Descontrolado') AS descontrolados,
        COUNT(*) AS total
    FROM base b
    LEFT JOIN tb_unidade_saude u
        ON u.co_seq_unidade_saude = b.co_unidade_saude_ultima
    WHERE {where}
    GROUP BY b.co_unidade_saude_ultima, u.no_unidade_saude
    ORDER BY total DESC
    """

    # 2) Distribuição em áreas e microáreas
    por_area_micro_sql = f"""
    {base_cte}
    SELECT
        b.nu_area,
        b.nu_micro_area,
        b.status_atual,
        COUNT(*) AS total
    FROM base b
    WHERE {where}
    GROUP BY b.nu_area, b.nu_micro_area, b.status_atual
    ORDER BY b.nu_area NULLS LAST, b.nu_micro_area NULLS LAST, b.status_atual
    """

    # 3) Quantidade total de medições de PA no último ano por USF
    mediana_medicoes_usf_sql = f"""
    WITH medicoes_12m AS (
        SELECT
            mc.co_unidade_saude,
            COUNT(*) AS total_medicoes
        FROM {schema}.mv_pa_medicoes_cidadaos mc
        WHERE mc.dt_medicao >= (CURRENT_DATE - INTERVAL '365 days')
          AND mc.nu_medicao_pressao_arterial ~ '^[0-9]+/[0-9]+$'
        GROUP BY mc.co_unidade_saude
    )
    SELECT
        m.co_unidade_saude,
        u.no_unidade_saude,
        m.total_medicoes
    FROM medicoes_12m m
    LEFT JOIN tb_unidade_saude u
        ON u.co_seq_unidade_saude = m.co_unidade_saude
    WHERE {where.replace("hip.co_unidade_saude_ultima", "m.co_unidade_saude")}
    ORDER BY m.total_medicoes DESC
    """

    # 4-5) Sexo por status
    sexo_sql = f"""
    {base_cte}
    SELECT
        b.status_atual,
        b.sg_sexo,
        COUNT(*) AS total
    FROM base b
    WHERE {where}
      AND b.sg_sexo IS NOT NULL
    GROUP BY b.status_atual, b.sg_sexo
    ORDER BY b.status_atual, b.sg_sexo
    """

    # 6-7) Faixa etária por status
    faixa_sql = f"""
    {base_cte}
    SELECT
        b.status_atual,
        b.faixa_etaria,
        COUNT(*) AS total
    FROM base b
    WHERE {where}
      AND b.faixa_etaria IS NOT NULL
    GROUP BY b.status_atual, b.faixa_etaria
    ORDER BY b.status_atual, b.faixa_etaria
    """

    por_usf = execute_query(por_usf_sql, params)
    por_area_micro = execute_query(por_area_micro_sql, params)
    mediana_medicoes_usf = execute_query(mediana_medicoes_usf_sql, params)
    sexo = execute_query(sexo_sql, params)
    faixa_etaria = execute_query(faixa_sql, params)

    return {
        "por_usf": por_usf,
        "por_area_microarea": por_area_micro,
        "mediana_medicoes_usf": mediana_medicoes_usf,
        "sexo_por_status": sexo,
        "faixa_etaria_por_status": faixa_etaria,
        "filtros_aplicados": {"co_unidade_saude": co_unidade_saude},
    }

