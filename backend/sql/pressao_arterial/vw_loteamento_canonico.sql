-- =====================================================================
-- VIEW: LOTEAMENTO CANÔNICO — Mapeamento Hierárquico Bairro > Loteamento
-- Schema: dashboard.vw_loteamento_canonico
--
-- ESTRATÉGIA HÍBRIDA:
--   1. Se o no_bairro_filtro mapeia DIRETAMENTE para um loteamento do
--      GeoJSON (ex: "senhorinha cairo", "miro cairo"), usa o loteamento.
--   2. Se o no_bairro_filtro mapeia para um BAIRRO (ex: "zabele"),
--      agrupa como "{bairro} — (loteamento não especificado)".
--
-- Isso preserva TODOS os cadastros sem perder dados, enquanto fornece
-- granularidade extra para quem preencheu o loteamento corretamente.
-- =====================================================================

CREATE OR REPLACE VIEW dashboard.vw_loteamento_canonico AS

WITH

-- CTE 1: Geocodificacao deduplicada por nome normalizado (remove accented duplicates)
geo_dedup AS (
    SELECT DISTINCT ON (dashboard.normaliza_bairro(no_bairro))
        no_bairro,
        nu_latitude,
        nu_longitude,
        ds_fonte,
        ds_tipo_geo,          -- 'bairro' ou 'loteamento' (se existir na tabela)
        dashboard.normaliza_bairro(no_bairro) AS nome_norm
    FROM dashboard.tb_geocodificacao
    WHERE ds_fonte = 'geojson_import'
    ORDER BY dashboard.normaliza_bairro(no_bairro), LENGTH(no_bairro)
),

-- CTE 2: Tenta match direto do bairro_canonico com a geo (bairro OU loteamento)
match_geo AS (
    SELECT
        c.*,
        g.no_bairro           AS geo_nome,
        g.nu_latitude         AS geo_lat,
        g.nu_longitude        AS geo_lng,
        g.ds_tipo_geo         AS geo_tipo
    FROM dashboard.vw_bairro_canonico c
    LEFT JOIN geo_dedup g
        ON g.nome_norm = dashboard.normaliza_bairro(c.bairro_canonico)
    WHERE c.st_bairro_vdc = TRUE
       OR c.st_bairro_vdc IS NULL  -- inclui todos os VDC identificados
)

SELECT
    -- Identificação hierárquica
    c.bairro_canonico,
    c.geo_nome,
    c.geo_tipo,
    c.geo_lat,
    c.geo_lng,

    -- Todos os campos do cadastro passam através
    c.co_seq_fat_cad_individual,
    c.co_fat_cidadao_pec,
    c.co_cidadao,
    c.data_cadastro,
    c.ano_cadastro,
    c.mes_cadastro,
    c.mes_ano_cadastro,
    c.dt_nascimento,
    c.idade,
    c.faixa_etaria,
    c.grupo_idade,
    c.co_dim_sexo,
    c.ds_sexo,
    c.sg_sexo,
    c.ds_raca_cor,
    c.ds_dim_tipo_escolaridade,
    c.no_bairro,
    c.no_bairro_filtro,
    c.co_localidade,
    c.nu_area,
    c.nu_micro_area,
    c.co_uf,
    c.ds_logradouro,
    c.nu_numero,
    c.ds_cep,
    c.st_hipertensao_arterial,
    c.st_fumante,
    c.st_alcool,
    c.st_outra_droga,
    c.st_diabetes,
    c.st_doenca_cardiaca,
    c.st_doenca_card_insuficiencia,
    c.st_problema_rins,
    c.st_doenca_renal_insuficiencia,
    c.st_avc,
    c.st_infarto,
    c.st_doenca_respiratoria,
    c.st_cancer,
    c.st_hanseniase,
    c.st_tuberculose,
    c.st_gestante,
    c.st_acamado,
    c.st_domiciliado,
    c.st_faleceu,
    c.st_bairro_vdc

FROM match_geo c;

COMMENT ON VIEW dashboard.vw_loteamento_canonico IS
    'Visão hierárquica bairro > loteamento para granularidade no mapa. '
    'Todos os cadastros VDC passam com geo_nome = nome do GeoJSON (bairro ou loteamento). '
    'Usa vw_bairro_canonico + tb_geocodificacao com join normalizado deduplicado.';
