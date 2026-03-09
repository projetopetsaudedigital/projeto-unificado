"""
Análise de hipertensos por Unidade Básica de Saúde (UBS).

Usa:
  - mv_pa_medicoes_cidadaos: cidadão → UBS (co_unidade_saude via tb_lotacao)
  - mv_pa_cadastros:         cidadão → st_hipertensao_arterial
  - tb_unidade_saude:        UBS → nome e bairro

Join key: mv_pa_medicoes_cidadaos.co_cidadao = mv_pa_cadastros.co_cidadao
(preferido sobre co_seq_fat_cidadao_pec que pode ser NULL)
"""

from app.core.database import execute_query
from app.core.config import settings


def buscar_dados_ubs(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    """
    Retorna, por UBS, o total de pacientes únicos com medição de PA,
    quantos têm hipertensão declarada no cadastro e a prevalência (%).

    Apenas UBS com ao menos uma medição de PA são incluídas.
    """
    schema = settings.DB_SCHEMA
    filtros = ["1=1"]
    params: dict = {}

    if ano_inicio:
        filtros.append("mc.ano >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("mc.ano <= :ano_fim")
        params["ano_fim"] = ano_fim

    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        ubs.co_seq_unidade_saude,
        ubs.nu_cnes,
        ubs.no_unidade_saude,
        ubs.no_bairro                                              AS bairro_ubs,
        ubs.no_bairro_filtro,
        COUNT(DISTINCT mc.co_cidadao)                              AS total_pacientes,
        COUNT(DISTINCT CASE
            WHEN cad.st_hipertensao_arterial = 1 THEN mc.co_cidadao
        END)                                                       AS hipertensos,
        ROUND(
            COUNT(DISTINCT CASE
                WHEN cad.st_hipertensao_arterial = 1 THEN mc.co_cidadao
            END)::NUMERIC
            / NULLIF(COUNT(DISTINCT mc.co_cidadao), 0) * 100, 1
        )                                                          AS prevalencia_pct,
        COUNT(mc.co_seq_medicao)                                   AS total_medicoes
    FROM tb_unidade_saude ubs
    INNER JOIN {schema}.mv_pa_medicoes_cidadaos mc
        ON mc.co_unidade_saude = ubs.co_seq_unidade_saude
    LEFT JOIN {schema}.mv_pa_cadastros cad
        ON mc.co_cidadao = cad.co_cidadao
    WHERE {where}
    GROUP BY
        ubs.co_seq_unidade_saude,
        ubs.nu_cnes,
        ubs.no_unidade_saude,
        ubs.no_bairro,
        ubs.no_bairro_filtro
    HAVING COUNT(mc.co_seq_medicao) > 0
    ORDER BY hipertensos DESC NULLS LAST
    """

    rows = execute_query(sql, params)

    return [
        {k: float(v) if hasattr(v, "__float__") and k in ("prevalencia_pct",) else v
         for k, v in r.items()}
        for r in rows
    ]
