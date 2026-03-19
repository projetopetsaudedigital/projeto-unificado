-- =====================================================================
-- VIEW MATERIALIZADA: CADASTROS COM FATORES DE RISCO E GEOLOCALIZAÇÃO
-- Schema: dashboard.mv_pa_cadastros
-- Usado para: análise de prevalência, fatores de risco, mapa por bairro
--
-- DEDUPLICAÇÃO: DISTINCT ON (co_fat_cidadao_pec) mantém apenas a ficha
-- mais recente por cidadão (co_dim_tempo DESC). Sem isso, um cidadão
-- recadastrado N vezes seria contado N vezes.
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_pa_cadastros AS

SELECT DISTINCT ON (cad.co_fat_cidadao_pec)

    -- Identificadores
    cad.co_seq_fat_cad_individual,
    cad.co_fat_cidadao_pec,
    pec.co_cidadao,

    -- Temporal do cadastro (ficha mais recente)
    cad.co_dim_tempo,
    TO_DATE(CAST(cad.co_dim_tempo AS TEXT), 'YYYYMMDD')             AS data_cadastro,
    EXTRACT(YEAR  FROM TO_DATE(CAST(cad.co_dim_tempo AS TEXT), 'YYYYMMDD'))::INTEGER AS ano_cadastro,
    EXTRACT(MONTH FROM TO_DATE(CAST(cad.co_dim_tempo AS TEXT), 'YYYYMMDD'))::INTEGER AS mes_cadastro,
    DATE_TRUNC('month', TO_DATE(CAST(cad.co_dim_tempo AS TEXT), 'YYYYMMDD'))::DATE   AS mes_ano_cadastro,

    -- Demográficas
    cad.dt_nascimento,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, cad.dt_nascimento))::INTEGER AS idade,
    CASE
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, cad.dt_nascimento)) < 30 THEN '18-29'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, cad.dt_nascimento)) < 40 THEN '30-39'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, cad.dt_nascimento)) < 50 THEN '40-49'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, cad.dt_nascimento)) < 60 THEN '50-59'
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, cad.dt_nascimento)) < 65 THEN '60-64'
        ELSE '65+'
    END                                                              AS faixa_etaria,
    -- grupo_idade alinhado com faixa_etaria: idosos a partir de 65 anos
    CASE
        WHEN EXTRACT(YEAR FROM AGE(CURRENT_DATE, cad.dt_nascimento)) < 65
            THEN 'Adultos (18-64)'
        ELSE 'Idosos (65+)'
    END                                                              AS grupo_idade,

    -- Sexo
    cad.co_dim_sexo,
    s.ds_sexo,
    s.sg_sexo,

    -- Raça/Cor e Escolaridade
    cad.co_dim_raca_cor,
    r.ds_raca_cor,
    cad.co_dim_tipo_escolaridade,
    e.ds_dim_tipo_escolaridade,

    -- Geolocalização
    c.no_bairro,
    c.no_bairro_filtro,
    c.co_localidade,
    c.nu_area,
    COALESCE(
        NULLIF(TRIM(terr.nu_micro_area), ''),
        NULLIF(TRIM(c.nu_micro_area), '')
    )                                                         AS nu_micro_area,
    c.co_uf,
    c.ds_logradouro,
    c.nu_numero,
    c.ds_cep,

    -- ── VARIÁVEL-ALVO ────────────────────────────────────────────────
    cad.st_hipertensao_arterial,

    -- ── FATORES DE RISCO COMPORTAMENTAIS ────────────────────────────
    cad.st_fumante,
    cad.st_alcool,
    cad.st_outra_droga,

    -- ── COMORBIDADES ────────────────────────────────────────────────
    cad.st_diabete                          AS st_diabetes,
    cad.st_doenca_cardiaca,
    cad.st_doenca_card_insuficiencia,
    cad.st_problema_rins,
    cad.st_problema_rins_insuficiencia      AS st_doenca_renal_insuficiencia,
    cad.st_avc,
    cad.st_infarto,
    cad.st_doenca_respiratoria,
    cad.st_cancer,
    cad.st_hanseniase,
    cad.st_tuberculose,

    -- ── OUTROS STATUS ────────────────────────────────────────────────
    cad.st_gestante,
    cad.st_acamado,
    cad.st_domiciliado,
    pec.st_faleceu

FROM pec.tb_fat_cad_individual cad

INNER JOIN pec.tb_fat_cidadao_pec pec
    ON cad.co_fat_cidadao_pec = pec.co_seq_fat_cidadao_pec

INNER JOIN pec.tb_cidadao c
    ON pec.co_cidadao = c.co_seq_cidadao

LEFT JOIN LATERAL (
    SELECT
        t.nu_micro_area
    FROM public.tb_fat_cidadao_territorio t
    WHERE t.co_fat_cidadao_pec = cad.co_fat_cidadao_pec
      AND NULLIF(TRIM(t.nu_micro_area), '') IS NOT NULL
    ORDER BY t.co_seq_fat_cidadao_territorio DESC
    LIMIT 1
) terr ON TRUE

LEFT JOIN pec.tb_dim_sexo s
    ON cad.co_dim_sexo = s.co_seq_dim_sexo

LEFT JOIN pec.tb_dim_raca_cor r
    ON cad.co_dim_raca_cor = r.co_seq_dim_raca_cor

LEFT JOIN pec.tb_dim_tipo_escolaridade e
    ON cad.co_dim_tipo_escolaridade = e.co_seq_dim_tipo_escolaridade

WHERE
    cad.dt_nascimento IS NOT NULL
    AND EXTRACT(YEAR FROM AGE(CURRENT_DATE, cad.dt_nascimento)) >= 18
    AND (pec.st_faleceu = 0 OR pec.st_faleceu IS NULL)
    AND (cad.st_recusa_cadastro = 0 OR cad.st_recusa_cadastro IS NULL)
    AND cad.co_dim_tempo IS NOT NULL
    AND (c.no_bairro IS NOT NULL OR c.no_bairro_filtro IS NOT NULL)

-- DISTINCT ON exige que a coluna de partição venha primeiro no ORDER BY
ORDER BY cad.co_fat_cidadao_pec, cad.co_dim_tempo DESC;

-- Índices
-- Nota: UNIQUE em co_seq_fat_cad_individual ainda é válido pois DISTINCT ON
-- garante uma ficha por cidadão (a mais recente), e cada ficha tem ID único.
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_pa_cad_pk
    ON dashboard.mv_pa_cadastros (co_seq_fat_cad_individual);

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_pa_cad_cidadao_pec
    ON dashboard.mv_pa_cadastros (co_fat_cidadao_pec);

CREATE INDEX IF NOT EXISTS idx_mv_pa_cad_cidadao
    ON dashboard.mv_pa_cadastros (co_cidadao);

CREATE INDEX IF NOT EXISTS idx_mv_pa_cad_tempo
    ON dashboard.mv_pa_cadastros (co_dim_tempo);

CREATE INDEX IF NOT EXISTS idx_mv_pa_cad_bairro
    ON dashboard.mv_pa_cadastros (no_bairro_filtro);

CREATE INDEX IF NOT EXISTS idx_mv_pa_cad_hipertensao
    ON dashboard.mv_pa_cadastros (st_hipertensao_arterial);

CREATE INDEX IF NOT EXISTS idx_mv_pa_cad_mes_ano
    ON dashboard.mv_pa_cadastros (mes_ano_cadastro);

COMMENT ON MATERIALIZED VIEW dashboard.mv_pa_cadastros IS
    'Um registro por cidadão (ficha mais recente via DISTINCT ON co_fat_cidadao_pec). '
    'Apenas adultos (>=18), vivos e com bairro preenchido. '
    'Idosos = 65+ anos (alinhado com faixa_etaria). '
    'Atualizar com: REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_pa_cadastros';
