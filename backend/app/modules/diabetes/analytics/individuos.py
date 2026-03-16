"""
Listagem operacional de individuos em acompanhamento de diabetes.

Regra aplicada:
- Considera apenas exames de HbA1c dos ultimos 12 meses.
- Seleciona somente o ultimo exame por individuo.
- Inclui todos (controlados e descontrolados). Filtro opcional por status.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

from app.core.config import settings
from app.core.database import execute_query


def buscar_individuos_diabetes_descontrolados(
    *,
    co_cidadao: Optional[int] = None,
    no_cidadao: Optional[str] = None,
    bairro: Optional[str] = None,
    sexo: Optional[str] = None,
    faixa_etaria: Optional[str] = None,
    nu_area: Optional[str] = None,
    nu_micro_area: Optional[str] = None,
    controle_status: Optional[str] = None,
    data_ultimo_exame_inicio: Optional[date] = None,
    data_ultimo_exame_fim: Optional[date] = None,
    limite: int = 50,
    offset: int = 0,
) -> dict:
    """Retorna total e pagina de individuos por ultimo HbA1c (controlados e/ou descontrolados)."""
    schema = settings.DB_SCHEMA
    filtros = ["1=1"]
    params: dict = {"limite": limite, "offset": offset}

    if co_cidadao is not None:
        filtros.append("ult.co_cidadao = :co_cidadao")
        params["co_cidadao"] = co_cidadao

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

    if bairro:
        filtros.append("UPPER(ult.no_bairro_filtro) = UPPER(:bairro)")
        params["bairro"] = bairro

    if sexo:
        filtros.append("UPPER(ult.sg_sexo) = :sexo")
        params["sexo"] = sexo.upper()

    if faixa_etaria:
        filtros.append("ult.faixa_etaria = :faixa_etaria")
        params["faixa_etaria"] = faixa_etaria

    if nu_area:
        filtros.append("tc.nu_area = :nu_area")
        params["nu_area"] = nu_area

    if nu_micro_area:
        filtros.append("tc.nu_micro_area = :nu_micro_area")
        params["nu_micro_area"] = nu_micro_area

    if controle_status in ("Controlado", "Descontrolado"):
        filtros.append("ult.controle_glicemico = :controle_status")
        params["controle_status"] = controle_status

    if data_ultimo_exame_inicio is not None:
        filtros.append("ult.dt_exame::date >= :data_ultimo_exame_inicio")
        params["data_ultimo_exame_inicio"] = data_ultimo_exame_inicio

    if data_ultimo_exame_fim is not None:
        filtros.append("ult.dt_exame::date <= :data_ultimo_exame_fim")
        params["data_ultimo_exame_fim"] = data_ultimo_exame_fim

    where = " AND ".join(filtros)

    cte_sql = f"""
    WITH exames_12m AS (
        SELECT
            dm.co_seq_hemoglobina_glicada,
            dm.co_cidadao,
            dm.dt_exame,
            dm.hba1c,
            dm.controle_glicemico,
            dm.idade_no_exame,
            dm.sg_sexo,
            dm.faixa_etaria,
            dm.no_bairro_filtro,
            dm.st_hipertensao,
            dm.st_doenca_cardiaca,
            dm.st_insuf_cardiaca,
            dm.st_infarto,
            dm.st_problema_rins,
            dm.st_avc,
            dm.st_fumante,
            dm.st_alcool,
            dm.st_doenca_respiratoria,
            dm.st_cancer,
            ROW_NUMBER() OVER (
                PARTITION BY dm.co_cidadao
                ORDER BY dm.dt_exame DESC, dm.co_seq_hemoglobina_glicada DESC
            ) AS rn
        FROM {schema}.mv_dm_hemoglobina dm
        WHERE dm.dt_exame >= (CURRENT_DATE - INTERVAL '12 months')
    ),
    ultimo_exame AS (
        SELECT
            co_seq_hemoglobina_glicada,
            co_cidadao,
            dt_exame,
            hba1c,
            controle_glicemico,
            idade_no_exame,
            sg_sexo,
            faixa_etaria,
            no_bairro_filtro,
            st_hipertensao,
            st_doenca_cardiaca,
            st_insuf_cardiaca,
            st_infarto,
            st_problema_rins,
            st_avc,
            st_fumante,
            st_alcool,
            st_doenca_respiratoria,
            st_cancer
        FROM exames_12m
        WHERE rn = 1
    )
    """

    from_sql = """
    FROM ultimo_exame ult
    LEFT JOIN pec.tb_cidadao tc
        ON tc.co_seq_cidadao = ult.co_cidadao
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
        COUNT(*) FILTER (WHERE ult.controle_glicemico = 'Controlado') AS total_controlados,
        COUNT(*) FILTER (WHERE ult.controle_glicemico = 'Descontrolado') AS total_descontrolados
    {from_sql}
    {where_sql}
    """

    dados_sql = f"""
    {cte_sql}
    SELECT
        ult.co_cidadao,
        COALESCE(
            NULLIF(TRIM(to_jsonb(tc)->>'no_cidadao'), ''),
            NULLIF(TRIM(to_jsonb(tc)->>'no_nome'), ''),
            NULLIF(TRIM(to_jsonb(tc)->>'no_nome_social'), ''),
            NULLIF(TRIM(to_jsonb(tc)->>'ds_nome'), '')
        ) AS nome_paciente,
        ult.idade_no_exame,
        ult.sg_sexo,
        tc.nu_area,
        tc.nu_micro_area,
        ROUND(ult.hba1c::NUMERIC, 2) AS hba1c_ultimo,
        ult.dt_exame::date AS dt_ultimo_exame,
        ult.controle_glicemico,
        JSONB_BUILD_ARRAY(
            JSONB_BUILD_OBJECT(
                'data_medicao', ult.dt_exame::date,
                'hba1c', ROUND(ult.hba1c::NUMERIC, 2),
                'exame', 'HbA1c'
            )
        ) AS ultimas_medicoes,
        ARRAY_REMOVE(
            ARRAY[
                CASE WHEN COALESCE(ult.st_hipertensao, 0) = 1 THEN 'Hipertensao' END,
                CASE WHEN COALESCE(ult.st_doenca_cardiaca, 0) = 1 THEN 'Doenca Cardiaca' END,
                CASE WHEN COALESCE(ult.st_insuf_cardiaca, 0) = 1 THEN 'Insuficiencia Cardiaca' END,
                CASE WHEN COALESCE(ult.st_infarto, 0) = 1 THEN 'Infarto' END,
                CASE WHEN COALESCE(ult.st_problema_rins, 0) = 1 THEN 'Problema Renal' END,
                CASE WHEN COALESCE(ult.st_avc, 0) = 1 THEN 'AVC' END,
                CASE WHEN COALESCE(ult.st_doenca_respiratoria, 0) = 1 THEN 'Doenca Respiratoria' END,
                CASE WHEN COALESCE(ult.st_cancer, 0) = 1 THEN 'Cancer' END,
                CASE WHEN COALESCE(ult.st_fumante, 0) = 1 THEN 'Tabagismo' END,
                CASE WHEN COALESCE(ult.st_alcool, 0) = 1 THEN 'Uso de Alcool' END
            ],
            NULL
        ) AS outras_condicoes
    {from_sql}
    {where_sql}
    ORDER BY ult.co_cidadao ASC
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
            "nome": row.get("nome_paciente"),
            "idade": row.get("idade_no_exame"),
            "sexo": row.get("sg_sexo"),
        }
        row["territorio"] = {
            "area": row.get("nu_area"),
            "microarea": row.get("nu_micro_area"),
        }
        row["hba1c_atual"] = {
            "valor": row.get("hba1c_ultimo"),
            "data": row.get("dt_ultimo_exame"),
        }
        row["ultimas_medicoes"] = ultimas_medicoes
        row["outras_condicoes"] = row.get("outras_condicoes") or []
        row["status_atual"] = row.get("controle_glicemico")

        row.pop("nome_paciente", None)
        row.pop("idade_no_exame", None)
        row.pop("sg_sexo", None)
        row.pop("nu_area", None)
        row.pop("nu_micro_area", None)
        row.pop("hba1c_ultimo", None)
        row.pop("dt_ultimo_exame", None)
        row.pop("controle_glicemico", None)

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
