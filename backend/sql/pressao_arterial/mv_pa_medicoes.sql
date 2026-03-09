-- =====================================================================
-- VIEW MATERIALIZADA: MEDIÇÕES DE PRESSÃO ARTERIAL
-- Schema: dashboard.mv_pa_medicoes
-- Melhoria vs projeto anterior: inclui co_unidade_saude e co_equipe
-- via join com tb_atend_prof (necessário para análise por UBS)
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_pa_medicoes AS

SELECT
    -- Identificadores
    m.co_seq_medicao,
    m.co_atend_prof,

    -- Unidade de saúde e equipe (NOVO — faltava na versão anterior)
    -- tb_atend_prof.co_lotacao → tb_lotacao.co_ator_papel (PK de tb_lotacao)
    lot.co_unidade_saude,
    lot.co_equipe,

    -- Temporal
    m.dt_medicao,
    EXTRACT(YEAR  FROM m.dt_medicao)::INTEGER          AS ano,
    EXTRACT(MONTH FROM m.dt_medicao)::INTEGER          AS mes,
    EXTRACT(QUARTER FROM m.dt_medicao)::INTEGER        AS trimestre,
    DATE_TRUNC('month', m.dt_medicao)::DATE            AS mes_ano,
    EXTRACT(DOW FROM m.dt_medicao)::INTEGER            AS dia_semana,

    -- Pressão arterial (formato "160/80")
    m.nu_medicao_pressao_arterial,

    -- Medidas antropométricas
    m.nu_medicao_peso,
    m.nu_medicao_altura,
    m.nu_medicao_imc,

    -- Sinais vitais
    m.nu_medicao_frequencia_cardiaca,
    m.nu_medicao_temperatura,
    m.nu_medicao_saturacao_o2,
    m.nu_medicao_frequnca_resprtria,

    -- Glicemia
    m.tp_glicemia,
    m.nu_medicao_glicemia,

    -- Outros
    m.nu_medicao_circunf_abdominal

FROM pec.tb_medicao m

-- LEFT JOIN: garante que medições sem vínculo a atendimento não sejam perdidas
LEFT JOIN pec.tb_atend_prof ap
    ON m.co_atend_prof = ap.co_seq_atend_prof

-- tb_lotacao traz co_unidade_saude e co_equipe (PK de tb_lotacao é co_ator_papel)
LEFT JOIN pec.tb_lotacao lot
    ON ap.co_lotacao = lot.co_ator_papel

WHERE
    m.nu_medicao_pressao_arterial IS NOT NULL
    AND m.nu_medicao_pressao_arterial != ''
    AND m.dt_medicao IS NOT NULL
    AND m.dt_medicao >= (CURRENT_DATE - INTERVAL '10 years')

ORDER BY m.dt_medicao DESC;

-- Índices para queries frequentes
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_pa_medicoes_pk
    ON dashboard.mv_pa_medicoes (co_seq_medicao);

CREATE INDEX IF NOT EXISTS idx_mv_pa_medicoes_dt
    ON dashboard.mv_pa_medicoes (dt_medicao);

CREATE INDEX IF NOT EXISTS idx_mv_pa_medicoes_ano
    ON dashboard.mv_pa_medicoes (ano);

CREATE INDEX IF NOT EXISTS idx_mv_pa_medicoes_mes_ano
    ON dashboard.mv_pa_medicoes (mes_ano);

CREATE INDEX IF NOT EXISTS idx_mv_pa_medicoes_ubs
    ON dashboard.mv_pa_medicoes (co_unidade_saude);

COMMENT ON MATERIALIZED VIEW dashboard.mv_pa_medicoes IS
    'Medições de PA dos últimos 10 anos com vínculo a UBS e equipe. '
    'Atualizar com: REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_pa_medicoes';
