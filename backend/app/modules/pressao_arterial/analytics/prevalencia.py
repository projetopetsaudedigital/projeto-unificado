"""
Análise de prevalência de hipertensão arterial por perfil demográfico.

Usa vw_bairro_canonico (cadastros individuais com st_hipertensao_arterial).
Por padrão filtra apenas bairros reconhecidos por VDC (st_bairro_vdc = TRUE).
Agrupa por bairro, sexo, faixa etária, raça/cor.
"""

from app.core.database import execute_query
from app.core.config import settings


def buscar_prevalencia_por_bairro(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
    apenas_vdc: bool = True,
) -> list[dict]:
    """
    Total de cadastros e hipertensos por bairro.
    Por padrão retorna apenas bairros de Vitória da Conquista (GeoJSON oficial).
    O nome do bairro retornado é o nome legível do GeoJSON (não o normalizado).
    """
    schema = settings.DB_SCHEMA
    filtros = ["c.bairro_canonico IS NOT NULL"]
    params: dict = {}

    if apenas_vdc:
        filtros.append("c.st_bairro_vdc = TRUE")

    if ano_inicio:
        filtros.append("c.ano_cadastro >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("c.ano_cadastro <= :ano_fim")
        params["ano_fim"] = ano_fim

    where = " AND ".join(filtros)

    if apenas_vdc:
        # Retorna nome legível do GeoJSON, deduplicado por nome normalizado
        sql = f"""
        WITH geo_vdc AS (
            SELECT DISTINCT ON ({schema}.normaliza_bairro(no_bairro))
                no_bairro,
                {schema}.normaliza_bairro(no_bairro) AS nome_norm
            FROM {schema}.tb_geocodificacao
            WHERE ds_fonte = 'geojson_import'
            ORDER BY {schema}.normaliza_bairro(no_bairro), LENGTH(no_bairro)
        )
        SELECT
            geo_vdc.no_bairro                                              AS bairro,
            COUNT(*)                                                        AS total_cadastros,
            COUNT(*) FILTER (WHERE c.st_hipertensao_arterial = 1)          AS hipertensos,
            ROUND(
                COUNT(*) FILTER (WHERE c.st_hipertensao_arterial = 1)::NUMERIC
                / NULLIF(COUNT(*), 0) * 100, 1
            )                                                               AS prevalencia_pct
        FROM {schema}.vw_bairro_canonico c
        INNER JOIN geo_vdc
            ON geo_vdc.nome_norm = {schema}.normaliza_bairro(c.bairro_canonico)
        WHERE {where}
        GROUP BY geo_vdc.no_bairro
        ORDER BY hipertensos DESC
        """
    else:
        sql = f"""
        SELECT
            bairro_canonico                            AS bairro,
            COUNT(*)                                   AS total_cadastros,
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1) AS hipertensos,
            ROUND(
                COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)::NUMERIC
                / NULLIF(COUNT(*), 0) * 100, 1
            )                                          AS prevalencia_pct
        FROM {schema}.vw_bairro_canonico c
        WHERE {where}
        GROUP BY bairro_canonico
        ORDER BY hipertensos DESC
        """

    return execute_query(sql, params)


def buscar_resumo_nao_identificados(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> dict:
    """
    Resumo de cadastros cujo bairro NÃO foi reconhecido como VDC.
    Agrupados por categoria (zona rural, exterior, inválido, etc.).
    """
    schema = settings.DB_SCHEMA
    filtros = ["(st_bairro_vdc = FALSE OR st_bairro_vdc IS NULL)"]
    params: dict = {}

    if ano_inicio:
        filtros.append("ano_cadastro >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("ano_cadastro <= :ano_fim")
        params["ano_fim"] = ano_fim

    where = " AND ".join(filtros)

    total_sql = f"""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1) AS hipertensos
        FROM {schema}.vw_bairro_canonico
        WHERE {where}
    """

    top_sql = f"""
        SELECT
            COALESCE(bairro_canonico, 'sem informação') AS categoria,
            COUNT(*) AS n,
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1) AS hipertensos
        FROM {schema}.vw_bairro_canonico
        WHERE {where}
        GROUP BY bairro_canonico
        ORDER BY n DESC
        LIMIT 30
    """

    total_row = execute_query(total_sql, params)
    top_rows = execute_query(top_sql, params)

    total = total_row[0]["total"] if total_row else 0
    hipertensos = total_row[0]["hipertensos"] if total_row else 0

    return {
        "total": total,
        "hipertensos": hipertensos,
        "prevalencia_pct": round(hipertensos / total * 100, 1) if total else 0,
        "top_categorias": [
            {"categoria": r["categoria"], "n": r["n"], "hipertensos": r["hipertensos"]}
            for r in top_rows
        ],
    }


def buscar_prevalencia_por_sexo(
    bairro: str | None = None,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    schema = settings.DB_SCHEMA
    filtros = ["1=1", "st_bairro_vdc = TRUE"]
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

    sql = f"""
    SELECT
        ds_sexo                                    AS sexo,
        sg_sexo,
        COUNT(*)                                   AS total,
        COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1) AS hipertensos,
        ROUND(
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                          AS prevalencia_pct
    FROM {schema}.vw_bairro_canonico
    WHERE {where}
      AND ds_sexo IS NOT NULL
    GROUP BY ds_sexo, sg_sexo
    ORDER BY total DESC
    """

    return execute_query(sql, params)


def buscar_prevalencia_por_faixa_etaria(
    bairro: str | None = None,
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    schema = settings.DB_SCHEMA
    filtros = ["1=1", "st_bairro_vdc = TRUE"]
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

    sql = f"""
    SELECT
        faixa_etaria,
        COUNT(*)                                   AS total,
        COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1) AS hipertensos,
        ROUND(
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                          AS prevalencia_pct
    FROM {schema}.vw_bairro_canonico
    WHERE {where}
    GROUP BY faixa_etaria
    ORDER BY faixa_etaria
    """

    return execute_query(sql, params)


def buscar_kpis_gerais() -> dict:
    """
    KPIs resumidos. Conta todos os residentes vivos e adultos (sem filtro VDC),
    alinhado com o total real exibido no mapa.
    """
    schema = settings.DB_SCHEMA

    sql = f"""
    SELECT
        COUNT(*)                                                               AS total_cadastros,
        COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)                   AS total_hipertensos,
        ROUND(
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                                      AS prevalencia_geral_pct,
        COUNT(*) FILTER (WHERE st_bairro_vdc = TRUE)                          AS total_vdc_identificados,
        COUNT(*) FILTER (WHERE st_bairro_vdc IS NOT TRUE)                     AS total_nao_identificados,
        COUNT(DISTINCT bairro_canonico) FILTER (WHERE st_bairro_vdc = TRUE)   AS total_bairros
    FROM {schema}.vw_bairro_canonico
    """

    rows = execute_query(sql, {})
    return rows[0] if rows else {}
