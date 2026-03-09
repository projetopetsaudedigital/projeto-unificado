"""
Dados para mapa coroplético — distribuição geográfica por bairro VDC.

Retorna apenas bairros de Vitória da Conquista reconhecidos pelo GeoJSON
da prefeitura (ds_fonte = 'geojson_import'), com coordenadas geográficas.

JOIN usa dashboard.normaliza_bairro() em ambos os lados para resolver
diferenças de case (Title Case no geocodificacao vs lowercase no mapping).
"""

from app.core.database import execute_query
from app.core.config import settings


def buscar_dados_mapa(
    ano_inicio: int | None = None,
    ano_fim: int | None = None,
) -> list[dict]:
    """
    Dados agregados por bairro VDC para o mapa coroplético.
    Retorna apenas bairros com coordenadas (st_bairro_vdc=TRUE).
    """
    schema = settings.DB_SCHEMA
    filtros = ["c.st_bairro_vdc = TRUE", "c.bairro_canonico IS NOT NULL"]
    params: dict = {}

    if ano_inicio:
        filtros.append("c.ano_cadastro >= :ano_inicio")
        params["ano_inicio"] = ano_inicio
    if ano_fim:
        filtros.append("c.ano_cadastro <= :ano_fim")
        params["ano_fim"] = ano_fim

    where = " AND ".join(filtros)

    sql = f"""
    -- Deduplica tb_geocodificacao: mantém apenas 1 entrada por nome normalizado
    WITH geo_vdc AS (
        SELECT DISTINCT ON ({schema}.normaliza_bairro(no_bairro))
            no_bairro,
            nu_latitude,
            nu_longitude,
            ds_fonte,
            {schema}.normaliza_bairro(no_bairro) AS nome_norm
        FROM {schema}.tb_geocodificacao
        WHERE ds_fonte = 'geojson_import'
        ORDER BY {schema}.normaliza_bairro(no_bairro), LENGTH(no_bairro)  -- prefere nome mais curto (sem acento)
    )
    SELECT
        geo_vdc.no_bairro                                              AS bairro,
        geo_vdc.nu_latitude                                            AS lat,
        geo_vdc.nu_longitude                                           AS lng,
        geo_vdc.ds_fonte                                               AS geo_fonte,

        -- Cadastros e hipertensão
        COUNT(*)                                                       AS total_cadastros,
        COUNT(*) FILTER (WHERE c.st_hipertensao_arterial = 1)         AS hipertensos,
        ROUND(
            COUNT(*) FILTER (WHERE c.st_hipertensao_arterial = 1)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                              AS prevalencia_pct,

        -- Fatores de risco
        COUNT(*) FILTER (WHERE c.st_diabetes = 1)                     AS n_diabetes,
        COUNT(*) FILTER (WHERE c.st_avc = 1)                          AS n_avc,
        COUNT(*) FILTER (WHERE c.st_infarto = 1)                      AS n_infarto,
        COUNT(*) FILTER (WHERE c.st_fumante = 1)                      AS n_fumantes,

        -- Perfil etário
        COUNT(*) FILTER (WHERE c.grupo_idade = 'Idosos (65+)')        AS n_idosos,
        ROUND(
            COUNT(*) FILTER (WHERE c.grupo_idade = 'Idosos (65+)')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                              AS pct_idosos

    FROM {schema}.vw_bairro_canonico c
    INNER JOIN geo_vdc
        ON geo_vdc.nome_norm = {schema}.normaliza_bairro(c.bairro_canonico)
    WHERE {where}
    GROUP BY geo_vdc.no_bairro, geo_vdc.nu_latitude, geo_vdc.nu_longitude, geo_vdc.ds_fonte
    ORDER BY hipertensos DESC
    """

    return execute_query(sql, params)


def buscar_cobertura_bairros() -> dict:
    """
    Resumo de cobertura: quantos cadastros têm bairro VDC identificado vs não-identificado.
    Retorna totais, percentual e top categorias dos não-identificados.
    """
    schema = settings.DB_SCHEMA

    total_sql = f"SELECT COUNT(*) AS n FROM {schema}.vw_bairro_canonico"
    vdc_sql = f"""
        SELECT COUNT(*) AS n
        FROM {schema}.vw_bairro_canonico
        WHERE st_bairro_vdc = TRUE
    """
    nao_id_sql = f"""
        SELECT bairro_canonico AS categoria, COUNT(*) AS n
        FROM {schema}.vw_bairro_canonico
        WHERE st_bairro_vdc = FALSE OR st_bairro_vdc IS NULL
        GROUP BY bairro_canonico
        ORDER BY n DESC
        LIMIT 30
    """

    total = execute_query(total_sql, {})[0]["n"]
    vdc = execute_query(vdc_sql, {})[0]["n"]
    nao_identificados = total - vdc
    top_nao_id = execute_query(nao_id_sql, {})

    return {
        "total_cadastros": total,
        "vdc_identificados": vdc,
        "vdc_pct": round(vdc / total * 100, 1) if total else 0,
        "nao_identificados": nao_identificados,
        "nao_id_pct": round(nao_identificados / total * 100, 1) if total else 0,
        "top_nao_identificados": [
            {"categoria": r["categoria"] or "sem informação", "n": r["n"]}
            for r in top_nao_id
        ],
    }


def buscar_bairros_disponiveis() -> list[str]:
    """Lista todos os bairros VDC com cadastros no sistema (nome legível do GeoJSON)."""
    schema = settings.DB_SCHEMA
    sql = f"""
    SELECT DISTINCT g.no_bairro AS bairro
    FROM {schema}.vw_bairro_canonico c
    INNER JOIN {schema}.tb_geocodificacao g
        ON {schema}.normaliza_bairro(g.no_bairro) = {schema}.normaliza_bairro(c.bairro_canonico)
        AND g.ds_fonte = 'geojson_import'
    WHERE c.bairro_canonico IS NOT NULL
    ORDER BY g.no_bairro
    """
    rows = execute_query(sql, {})
    return [r["bairro"] for r in rows]


def buscar_dados_mapa_loteamentos(
    bairros: list[str] = None,
    ano_inicio: int = None,
    ano_fim: int = None,
) -> list[dict]:
    """Retorna os dados geográficos e epidemiológicos agregados por Bairro + Loteamento
    (exibindo a granularidade máxima com base no que foi identificado)."""
    schema = settings.DB_SCHEMA

    filtros = ["geo_lat IS NOT NULL"]
    params = {}

    if bairros:
        filtros.append("geo_nome = ANY(:bairros)")
        params["bairros"] = bairros

    if ano_inicio:
        filtros.append("ano_cadastro >= :ano_inicio")
        params["ano_inicio"] = ano_inicio

    if ano_fim:
        filtros.append("ano_cadastro <= :ano_fim")
        params["ano_fim"] = ano_fim

    where = " AND ".join(filtros)

    # Agrupa por bairro_canonico e geo_nome (garantindo que exibe ambos)
    sql = f"""
    SELECT
        bairro_canonico,
        geo_nome                                                       AS bairro,
        geo_tipo,
        geo_lat                                                        AS lat,
        geo_lng                                                        AS lng,
        'geojson_import'                                               AS geo_fonte,

        -- Cadastros e hipertensão
        COUNT(*)                                                       AS total_cadastros,
        COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)           AS hipertensos,
        ROUND(
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                              AS prevalencia_pct,

        -- Fatores de risco
        COUNT(*) FILTER (WHERE st_diabetes = 1)                       AS n_diabetes,
        COUNT(*) FILTER (WHERE st_avc = 1)                            AS n_avc,
        COUNT(*) FILTER (WHERE st_infarto = 1)                        AS n_infarto,
        COUNT(*) FILTER (WHERE st_fumante = 1)                        AS n_fumantes,

        -- Perfil etário
        COUNT(*) FILTER (WHERE grupo_idade = 'Idosos (65+)')          AS n_idosos,
        ROUND(
            COUNT(*) FILTER (WHERE grupo_idade = 'Idosos (65+)')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                              AS pct_idosos

    FROM {schema}.vw_loteamento_canonico
    WHERE {where}
    GROUP BY bairro_canonico, geo_nome, geo_tipo, geo_lat, geo_lng
    ORDER BY hipertensos DESC
    """
    
    rows = execute_query(sql, params)
    
    # Tratamento final: se for do tipo 'bairro' num nível de loteamento, 
    # ele é "Bairro (loteamento não especificado)".
    for row in rows:
        if row["geo_tipo"] == "bairro":
            row["bairro"] = f"{row['bairro']} (não espec. ou todo bairro)"
        if row.get("lat") is not None:
            row["lat"] = float(row["lat"])
        if row.get("lng") is not None:
            row["lng"] = float(row["lng"])
        if row.get("prevalencia_pct") is not None:
            row["prevalencia_pct"] = float(row["prevalencia_pct"])
        if row.get("pct_idosos") is not None:
            row["pct_idosos"] = float(row["pct_idosos"])
        
    return rows
