"""
Análise de tendência temporal das medições de pressão arterial.

Agrega medições por mês/ano e retorna:
- Contagem total de medições
- Distribuição por classificação de PA (normal, elevada, HAS I, II, III)
- Média de PAS e PAD no período
"""

from app.core.database import execute_query
from app.core.config import settings


def buscar_tendencia(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    co_unidade_saude: int | None = None,
    bairro: str | None = None,
) -> list[dict]:
    """
    Retorna evolução mensal das medições de PA.
    Usa mv_pa_medicoes_cidadaos (já tem bairro e UBS).
    """
    schema = settings.DB_SCHEMA
    filtros = ["1=1"]
    params: dict = {}

    if ano_inicio:
        filtros.append("ano >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("ano <= :ano_fim")
        params["ano_fim"] = ano_fim
    if co_unidade_saude:
        filtros.append("co_unidade_saude = :co_unidade_saude")
        params["co_unidade_saude"] = co_unidade_saude
    if bairro:
        filtros.append("UPPER(no_bairro_filtro) = UPPER(:bairro)  -- mv_pa_medicoes_cidadaos ainda usa no_bairro_filtro")
        params["bairro"] = bairro

    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        mes_ano,
        ano,
        mes,
        COUNT(*) AS total_medicoes,
        COUNT(DISTINCT co_cidadao) AS total_cidadaos,

        -- Classificação de PA baseada em PAS/PAD extraídas
        COUNT(*) FILTER (WHERE
            SPLIT_PART(nu_medicao_pressao_arterial, '/', 1)::NUMERIC < 120
            AND SPLIT_PART(nu_medicao_pressao_arterial, '/', 2)::NUMERIC < 80
        ) AS normal,

        COUNT(*) FILTER (WHERE
            SPLIT_PART(nu_medicao_pressao_arterial, '/', 1)::NUMERIC BETWEEN 120 AND 129
            AND SPLIT_PART(nu_medicao_pressao_arterial, '/', 2)::NUMERIC < 80
        ) AS elevada,

        COUNT(*) FILTER (WHERE
            SPLIT_PART(nu_medicao_pressao_arterial, '/', 1)::NUMERIC BETWEEN 130 AND 139
            OR SPLIT_PART(nu_medicao_pressao_arterial, '/', 2)::NUMERIC BETWEEN 80 AND 89
        ) AS has_estagio_1,

        COUNT(*) FILTER (WHERE
            SPLIT_PART(nu_medicao_pressao_arterial, '/', 1)::NUMERIC BETWEEN 140 AND 179
            OR SPLIT_PART(nu_medicao_pressao_arterial, '/', 2)::NUMERIC BETWEEN 90 AND 119
        ) AS has_estagio_2,

        COUNT(*) FILTER (WHERE
            SPLIT_PART(nu_medicao_pressao_arterial, '/', 1)::NUMERIC >= 180
            OR SPLIT_PART(nu_medicao_pressao_arterial, '/', 2)::NUMERIC >= 120
        ) AS has_estagio_3,

        ROUND(AVG(SPLIT_PART(nu_medicao_pressao_arterial, '/', 1)::NUMERIC), 1) AS media_pas,
        ROUND(AVG(SPLIT_PART(nu_medicao_pressao_arterial, '/', 2)::NUMERIC), 1) AS media_pad

    FROM {schema}.mv_pa_medicoes_cidadaos
    WHERE {where}
      AND nu_medicao_pressao_arterial ~ '^[0-9]+/[0-9]+$'

    GROUP BY mes_ano, ano, mes
    ORDER BY mes_ano
    """

    return execute_query(sql, params)
