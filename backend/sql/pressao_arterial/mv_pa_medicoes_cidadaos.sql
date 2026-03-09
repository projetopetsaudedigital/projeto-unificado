-- =====================================================================
-- VIEW MATERIALIZADA: MEDIÇÕES + CIDADÃO (LONGITUDINAL)
-- Schema: dashboard.mv_pa_medicoes_cidadaos
-- Usado para: análise individual, séries temporais por paciente,
--             detecção de outliers por histórico individual
-- Join path:
--   tb_medicao
--   → tb_atend_prof → tb_lotacao           (UBS/equipe)
--   → LATERAL tb_exame_requisitado
--   → tb_prontuario → tb_cidadao           (dados demográficos)
--   → tb_fat_cidadao_pec                   (ID unificado PEC)
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_pa_medicoes_cidadaos AS

SELECT
    -- Identificadores
    m.co_seq_medicao,
    m.co_atend_prof,

    -- Unidade de saúde e equipe
    -- tb_atend_prof.co_lotacao → tb_lotacao.co_ator_papel (PK)
    lot.co_unidade_saude,
    lot.co_equipe,

    -- Cidadão (ID unificado PEC)
    pec.co_seq_fat_cidadao_pec,
    c.co_seq_cidadao                                   AS co_cidadao,

    -- Temporal da medição
    m.dt_medicao,
    EXTRACT(YEAR  FROM m.dt_medicao)::INTEGER          AS ano,
    EXTRACT(MONTH FROM m.dt_medicao)::INTEGER          AS mes,
    EXTRACT(QUARTER FROM m.dt_medicao)::INTEGER        AS trimestre,
    DATE_TRUNC('month', m.dt_medicao)::DATE            AS mes_ano,

    -- Pressão arterial
    m.nu_medicao_pressao_arterial,

    -- Medidas complementares (úteis para correlação)
    m.nu_medicao_peso,
    m.nu_medicao_altura,
    m.nu_medicao_imc,
    m.nu_medicao_frequencia_cardiaca,
    m.nu_medicao_glicemia,
    m.nu_medicao_circunf_abdominal,

    -- Dados demográficos do cidadão
    c.dt_nascimento,
    EXTRACT(YEAR FROM AGE(m.dt_medicao, c.dt_nascimento))::INTEGER AS idade_na_medicao,
    CASE
        WHEN EXTRACT(YEAR FROM AGE(m.dt_medicao, c.dt_nascimento)) < 30 THEN '18-29'
        WHEN EXTRACT(YEAR FROM AGE(m.dt_medicao, c.dt_nascimento)) < 40 THEN '30-39'
        WHEN EXTRACT(YEAR FROM AGE(m.dt_medicao, c.dt_nascimento)) < 50 THEN '40-49'
        WHEN EXTRACT(YEAR FROM AGE(m.dt_medicao, c.dt_nascimento)) < 60 THEN '50-59'
        WHEN EXTRACT(YEAR FROM AGE(m.dt_medicao, c.dt_nascimento)) < 65 THEN '60-64'
        ELSE '65+'
    END                                                AS faixa_etaria_na_medicao,

    -- Geolocalização do cidadão
    c.no_bairro,
    c.no_bairro_filtro,
    c.co_localidade,
    c.nu_area,
    c.nu_micro_area,

    -- Status vital
    pec.st_faleceu

FROM pec.tb_medicao m

-- UBS e equipe responsável pelo atendimento
LEFT JOIN pec.tb_atend_prof ap
    ON m.co_atend_prof = ap.co_seq_atend_prof

-- tb_lotacao: PK é co_ator_papel (não co_seq_lotacao)
LEFT JOIN pec.tb_lotacao lot
    ON ap.co_lotacao = lot.co_ator_papel

-- Caminho para o cidadão via exame_requisitado → prontuario
-- LATERAL + DISTINCT ON garante no máximo 1 exame por co_atend_prof
INNER JOIN LATERAL (
    SELECT er.co_prontuario
    FROM pec.tb_exame_requisitado er
    WHERE er.co_atend_prof = m.co_atend_prof
      AND er.co_prontuario IS NOT NULL
    ORDER BY er.co_seq_exame_requisitado
    LIMIT 1
) er ON true

INNER JOIN pec.tb_prontuario p
    ON er.co_prontuario = p.co_seq_prontuario

INNER JOIN pec.tb_cidadao c
    ON p.co_cidadao = c.co_seq_cidadao

-- ID unificado no PEC (pode ser NULL se cidadão não tiver registro PEC)
LEFT JOIN pec.tb_fat_cidadao_pec pec
    ON pec.co_cidadao = c.co_seq_cidadao

WHERE
    m.nu_medicao_pressao_arterial IS NOT NULL
    AND m.nu_medicao_pressao_arterial != ''
    AND m.dt_medicao IS NOT NULL
    AND m.dt_medicao >= (CURRENT_DATE - INTERVAL '10 years')
    AND c.dt_nascimento IS NOT NULL
    AND EXTRACT(YEAR FROM AGE(m.dt_medicao, c.dt_nascimento)) >= 18
    AND (pec.st_faleceu = 0 OR pec.st_faleceu IS NULL)
    AND (c.no_bairro IS NOT NULL OR c.no_bairro_filtro IS NOT NULL)

ORDER BY c.co_seq_cidadao, m.dt_medicao DESC;

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_pa_mc_pk
    ON dashboard.mv_pa_medicoes_cidadaos (co_seq_medicao);

CREATE INDEX IF NOT EXISTS idx_mv_pa_mc_cidadao
    ON dashboard.mv_pa_medicoes_cidadaos (co_cidadao);

CREATE INDEX IF NOT EXISTS idx_mv_pa_mc_pec
    ON dashboard.mv_pa_medicoes_cidadaos (co_seq_fat_cidadao_pec);

CREATE INDEX IF NOT EXISTS idx_mv_pa_mc_dt
    ON dashboard.mv_pa_medicoes_cidadaos (dt_medicao);

CREATE INDEX IF NOT EXISTS idx_mv_pa_mc_mes_ano
    ON dashboard.mv_pa_medicoes_cidadaos (mes_ano);

CREATE INDEX IF NOT EXISTS idx_mv_pa_mc_ubs
    ON dashboard.mv_pa_medicoes_cidadaos (co_unidade_saude);

CREATE INDEX IF NOT EXISTS idx_mv_pa_mc_bairro
    ON dashboard.mv_pa_medicoes_cidadaos (no_bairro_filtro);

COMMENT ON MATERIALIZED VIEW dashboard.mv_pa_medicoes_cidadaos IS
    'Medições de PA vinculadas ao cidadão — visão longitudinal. '
    'Apenas adultos (>=18) vivos com bairro preenchido, últimos 10 anos. '
    'Join: tb_medicao → tb_atend_prof → tb_lotacao (UBS) + LATERAL tb_exame_requisitado → tb_prontuario → tb_cidadao. '
    'Atualizar com: REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_pa_medicoes_cidadaos';
