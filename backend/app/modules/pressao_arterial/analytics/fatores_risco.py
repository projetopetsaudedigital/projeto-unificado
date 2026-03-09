"""
Análise de fatores de risco e comorbidades em hipertensos.

Compara a prevalência de cada comorbidade entre:
- Grupo hipertenso (st_hipertensao_arterial = 1)
- Grupo não-hipertenso (st_hipertensao_arterial = 0)

Usa vw_bairro_canonico.
"""

from app.core.database import execute_query
from app.core.config import settings


# Mapeamento das colunas de comorbidade para nome legível
_COMORBIDADES = {
    "st_diabetes": "Diabetes",
    "st_doenca_cardiaca": "Doença Cardíaca",
    "st_doenca_card_insuficiencia": "Insuficiência Cardíaca",
    "st_problema_rins": "Problema Renal",
    "st_doenca_renal_insuficiencia": "Insuficiência Renal",
    "st_avc": "AVC",
    "st_infarto": "Infarto",
    "st_doenca_respiratoria": "Doença Respiratória",
    "st_cancer": "Câncer",
    "st_hanseniase": "Hanseníase",
    "st_tuberculose": "Tuberculose",
}

_FATORES_COMPORTAMENTAIS = {
    "st_fumante": "Tabagismo",
    "st_alcool": "Uso de Álcool",
    "st_outra_droga": "Uso de Drogas",
}


def buscar_comparativo_comorbidades(
    bairro: str | None = None,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    """
    Para cada comorbidade, retorna a prevalência (%) em hipertensos vs não-hipertensos.
    Permite identificar quais comorbidades são mais associadas à HAS.
    """
    schema = settings.DB_SCHEMA
    filtros = ["1=1"]
    params: dict = {}

    if bairro:
        filtros.append("UPPER(bairro_canonico) = UPPER(:bairro)")
        params["bairro"] = bairro
    if ano_inicio:
        filtros.append("ano_cadastro >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("ano_cadastro <= :ano_fim")
        params["ano_fim"] = ano_fim

    where = " AND ".join(filtros)

    # Constrói SELECT dinâmico para cada comorbidade
    todas = {**_COMORBIDADES, **_FATORES_COMPORTAMENTAIS}
    selects = []
    for col, nome in todas.items():
        selects.append(f"""
        SELECT
            '{nome}'                                                    AS fator,
            '{col}'                                                     AS coluna,
            ROUND(
                COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1 AND {col} = 1)::NUMERIC
                / NULLIF(COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1), 0) * 100, 1
            )                                                           AS pct_hipertensos,
            ROUND(
                COUNT(*) FILTER (WHERE st_hipertensao_arterial != 1 AND {col} = 1)::NUMERIC
                / NULLIF(COUNT(*) FILTER (WHERE st_hipertensao_arterial != 1), 0) * 100, 1
            )                                                           AS pct_nao_hipertensos,
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1 AND {col} = 1) AS n_hipertensos,
            COUNT(*) FILTER (WHERE st_hipertensao_arterial != 1 AND {col} = 1) AS n_nao_hipertensos
        FROM {schema}.vw_bairro_canonico
        WHERE {where}
        """)

    sql = "\nUNION ALL\n".join(selects) + "\nORDER BY pct_hipertensos DESC NULLS LAST"

    return execute_query(sql, params)


def buscar_multiplos_fatores(
    bairro: str | None = None,
) -> list[dict]:
    """
    Distribuição do número de fatores de risco simultâneos em hipertensos.
    Útil para identificar pacientes de alto risco com múltiplas comorbidades.
    """
    schema = settings.DB_SCHEMA
    params: dict = {}
    filtros = ["st_hipertensao_arterial = 1"]

    if bairro:
        filtros.append("UPPER(bairro_canonico) = UPPER(:bairro)")
        params["bairro"] = bairro

    where = " AND ".join(filtros)

    sql = f"""
    SELECT
        (
            COALESCE((st_diabetes = 1)::INT, 0)
          + COALESCE((st_doenca_cardiaca = 1)::INT, 0)
          + COALESCE((st_problema_rins = 1)::INT, 0)
          + COALESCE((st_avc = 1)::INT, 0)
          + COALESCE((st_infarto = 1)::INT, 0)
          + COALESCE((st_fumante = 1)::INT, 0)
          + COALESCE((st_alcool = 1)::INT, 0)
        )                                                           AS n_fatores,
        COUNT(*)                                                    AS total_hipertensos,
        ROUND(COUNT(*)::NUMERIC / SUM(COUNT(*)) OVER () * 100, 1)  AS pct_do_total
    FROM {schema}.vw_bairro_canonico
    WHERE {where}
    GROUP BY n_fatores
    ORDER BY n_fatores
    """

    return execute_query(sql, params)
