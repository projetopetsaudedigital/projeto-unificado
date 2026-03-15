"""
Listagem operacional de indivíduos em acompanhamento de pressão arterial.

Regra aplicada:
- Considera apenas medições dos últimos 365 dias.
- Consolida múltiplas medições no mesmo dia por mediana diária (PAS/PAD).
- Inclui todos com ao menos 1 dia de medição (mediana dos últimos 3 dias).
- Status: Controlado = mediana recente < 140/90 mmHg; Descontrolado = caso contrário.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

from app.core.config import settings
from app.core.database import execute_query


def buscar_individuos_hipertensos(
    *,
    co_cidadao: Optional[int] = None,
    no_cidadao: Optional[str] = None,
    bairro: Optional[str] = None,
    sexo: Optional[str] = None,
    faixa_etaria: Optional[str] = None,
    nu_area: Optional[str] = None,
    nu_micro_area: Optional[str] = None,
    co_unidade_saude: Optional[int] = None,
    st_diabetes: Optional[bool] = None,
    data_ultima_medicao_inicio: Optional[date] = None,
    data_ultima_medicao_fim: Optional[date] = None,
    limite: int = 50,
    offset: int = 0,
) -> dict:
    """Retorna total e página de indivíduos em acompanhamento de PA.
    Inclusão: qualquer pessoa com ao menos 1 medição nos últimos 365 dias.
    Status: Controlado = mediana (últimos 3 dias) < 140/90; Descontrolado = caso contrário.
    """
    schema = settings.DB_SCHEMA
    # Incluir todos com mediana calculada; não exige PA alta para entrar na lista
    filtros = ["1=1"]
    params: dict = {"limite": limite, "offset": offset}

    if co_cidadao is not None:
        filtros.append("hip.co_cidadao = :co_cidadao")
        params["co_cidadao"] = co_cidadao

    if bairro:
        filtros.append("c.no_bairro_filtro = :bairro")
        params["bairro"] = bairro

    if sexo:
        filtros.append("UPPER(c.sg_sexo) = :sexo")
        params["sexo"] = sexo.upper()

    if faixa_etaria:
        filtros.append("c.faixa_etaria = :faixa_etaria")
        params["faixa_etaria"] = faixa_etaria

    if nu_area:
        filtros.append("c.nu_area = :nu_area")
        params["nu_area"] = nu_area

    if nu_micro_area:
        filtros.append("c.nu_micro_area = :nu_micro_area")
        params["nu_micro_area"] = nu_micro_area

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

    if no_cidadao:
        filtros.append(
            """
            COALESCE(
                NULLIF(TRIM(to_jsonb(tc)->>'no_cidadao'), ''),
                NULLIF(TRIM(to_jsonb(tc)->>'no_nome'), ''),
                NULLIF(TRIM(to_jsonb(tc)->>'no_nome_social'), ''),
                NULLIF(TRIM(to_jsonb(tc)->>'ds_nome'), '')
            ) ILIKE :no_cidadao
            """
        )
        params["no_cidadao"] = f"%{no_cidadao.strip()}%"

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
    mediana_anual_por_cidadao AS (
        SELECT
            co_cidadao,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pas_dia) AS mediana_anual_pas,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY pad_dia) AS mediana_anual_pad
        FROM mediana_por_dia
        GROUP BY co_cidadao
    ),
    ultimas_tres_resumo AS (
        SELECT
            u.co_cidadao,
            JSONB_AGG(
                JSONB_BUILD_OBJECT(
                    'data_medicao', u.dia_medicao,
                    'pas', ROUND(u.pas_dia::NUMERIC, 1),
                    'pad', ROUND(u.pad_dia::NUMERIC, 1),
                    'pressao', CONCAT(ROUND(u.pas_dia::NUMERIC, 0)::INT, '/', ROUND(u.pad_dia::NUMERIC, 0)::INT)
                )
                ORDER BY u.dia_medicao DESC
            ) FILTER (WHERE u.rn <= 3) AS ultimas_medicoes
        FROM ultimos_tres_dias u
        GROUP BY u.co_cidadao
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
    LEFT JOIN mediana_anual_por_cidadao ann
        ON ann.co_cidadao = hip.co_cidadao
    LEFT JOIN pec.tb_cidadao tc
        ON tc.co_seq_cidadao = c.co_cidadao
    """

    where_sql = f"""
    WHERE {where}
    """

    total_sql = f"""
    {cte_sql}
    SELECT COUNT(*) AS total
    {from_sql}
    {where_sql}
    """

    totais_status_sql = f"""
    {cte_sql}
    SELECT
        COUNT(*) FILTER (WHERE hip.mediana_pas < 140 AND hip.mediana_pad < 90) AS total_controlados,
        COUNT(*) FILTER (WHERE NOT (hip.mediana_pas < 140 AND hip.mediana_pad < 90)) AS total_descontrolados
    {from_sql}
    {where_sql}
    """

    dados_sql = f"""
    {cte_sql}
    SELECT
        c.co_cidadao,
        COALESCE(
            NULLIF(TRIM(to_jsonb(tc)->>'no_cidadao'), ''),
            NULLIF(TRIM(to_jsonb(tc)->>'no_nome'), ''),
            NULLIF(TRIM(to_jsonb(tc)->>'no_nome_social'), ''),
            NULLIF(TRIM(to_jsonb(tc)->>'ds_nome'), '')
        ) AS no_cidadao,
        c.idade,
        c.sg_sexo,
        c.nu_area,
        c.nu_micro_area,
        ROUND(hip.mediana_pas::NUMERIC, 1) AS mediana_pas,
        ROUND(hip.mediana_pad::NUMERIC, 1) AS mediana_pad,
        ROUND(COALESCE(ann.mediana_anual_pas, hip.mediana_pas)::NUMERIC, 1) AS mediana_anual_pas,
        ROUND(COALESCE(ann.mediana_anual_pad, hip.mediana_pad)::NUMERIC, 1) AS mediana_anual_pad,
        hip.n_medicoes_usadas,
        hip.dt_ultima_medicao,
        COALESCE(ult.ultimas_medicoes, '[]'::JSONB) AS ultimas_medicoes,
        ARRAY_REMOVE(
            ARRAY[
                CASE WHEN COALESCE(c.st_diabetes, 0) = 1 THEN 'Diabetes' END,
                CASE WHEN COALESCE(c.st_doenca_cardiaca, 0) = 1 THEN 'Doenca Cardiaca' END,
                CASE WHEN COALESCE(c.st_doenca_card_insuficiencia, 0) = 1 THEN 'Insuficiencia Cardiaca' END,
                CASE WHEN COALESCE(c.st_problema_rins, 0) = 1 THEN 'Problema Renal' END,
                CASE WHEN COALESCE(c.st_doenca_renal_insuficiencia, 0) = 1 THEN 'Insuficiencia Renal' END,
                CASE WHEN COALESCE(c.st_avc, 0) = 1 THEN 'AVC' END,
                CASE WHEN COALESCE(c.st_infarto, 0) = 1 THEN 'Infarto' END,
                CASE WHEN COALESCE(c.st_doenca_respiratoria, 0) = 1 THEN 'Doenca Respiratoria' END,
                CASE WHEN COALESCE(c.st_cancer, 0) = 1 THEN 'Cancer' END,
                CASE WHEN COALESCE(c.st_hanseniase, 0) = 1 THEN 'Hanseniase' END,
                CASE WHEN COALESCE(c.st_tuberculose, 0) = 1 THEN 'Tuberculose' END,
                CASE WHEN COALESCE(c.st_fumante, 0) = 1 THEN 'Tabagismo' END,
                CASE WHEN COALESCE(c.st_alcool, 0) = 1 THEN 'Uso de Alcool' END,
                CASE WHEN COALESCE(c.st_outra_droga, 0) = 1 THEN 'Uso de Drogas' END
            ],
            NULL
        ) AS outras_condicoes,
        CASE
            WHEN hip.mediana_pas < 140 AND hip.mediana_pad < 90 THEN 'Controlado'
            ELSE 'Descontrolado'
        END AS status_atual
    {from_sql}
    LEFT JOIN ultimas_tres_resumo ult
        ON ult.co_cidadao = hip.co_cidadao
    {where_sql}
    ORDER BY c.co_cidadao ASC
    LIMIT :limite OFFSET :offset
    """

    total_rows = execute_query(total_sql, params)
    totais_status_rows = execute_query(totais_status_sql, params)
    dados = execute_query(dados_sql, params)

    for row in dados:
        ultimas_medicoes = row.get("ultimas_medicoes")
        if isinstance(ultimas_medicoes, str):
            ultimas_medicoes = json.loads(ultimas_medicoes)
        if ultimas_medicoes is None:
            ultimas_medicoes = []

        row["paciente_perfil"] = {
            "nome": row.get("no_cidadao"),
            "idade": row.get("idade"),
            "sexo": row.get("sg_sexo"),
        }
        row["territorio"] = {
            "area": row.get("nu_area"),
            "microarea": row.get("nu_micro_area"),
        }
        row["mediana_anual"] = {
            "pas": row.get("mediana_anual_pas"),
            "pad": row.get("mediana_anual_pad"),
        }
        row["ultimas_medicoes"] = ultimas_medicoes
        row["outras_condicoes"] = row.get("outras_condicoes") or []

        row.pop("nu_area", None)
        row.pop("nu_micro_area", None)
        row.pop("mediana_pas", None)
        row.pop("mediana_pad", None)
        row.pop("idade", None)
        row.pop("sg_sexo", None)
        row.pop("no_cidadao", None)
        row.pop("mediana_anual_pas", None)
        row.pop("mediana_anual_pad", None)

    total = int(total_rows[0]["total"]) if total_rows else 0
    ts = totais_status_rows[0] if totais_status_rows else {}
    total_controlados = int(ts.get("total_controlados") or 0)
    total_descontrolados = int(ts.get("total_descontrolados") or 0)
    return {
        "total": total,
        "total_controlados": total_controlados,
        "total_descontrolados": total_descontrolados,
        "dados": dados,
    }
