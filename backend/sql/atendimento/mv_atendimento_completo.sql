-- =====================================================================
-- VIEW MATERIALIZADA: ATENDIMENTOS COMPLETOS
-- Schema: dashboard.mv_atendimento_completo
--
-- Objetivo: consolidar o fluxo de atendimento do cidadao, ligando
--           atendimento -> prontuario -> cidadao -> UBS -> profissional -> medicao.
--           Esta view alimenta TODAS as analises que dependem do eixo atendimento.
--
-- Join path (conforme diagrama do e-SUS PEC):
--   tb_atend
--   -> tb_prontuario         (co_prontuario -> co_seq_prontuario)
--   -> tb_cidadao            (co_cidadao -> co_seq_cidadao)
--   -> tb_unidade_saude      (co_unidade_saude -> co_seq_unidade_saude)
--   -> tb_atend_prof         (co_atend_prof -> co_seq_atend_prof)
--   -> tb_medicao            (co_atend_prof -> co_seq_atend_prof)
--
-- CUIDADO COM DUPLICACAO:
--   Um atend_prof pode ter N medicoes. Se fizer COUNT de atendimentos,
--   use sempre COUNT(DISTINCT co_seq_atend) para evitar inflacao.
-- =====================================================================


CREATE SCHEMA IF NOT EXISTS dashboard;

CREATE MATERIALIZED VIEW dashboard.mv_atendimento_completo AS
SELECT
    -- Identificadores
    a.co_seq_atend,
    p.co_seq_prontuario,
    c.co_seq_cidadao,
    ap.co_seq_atend_prof,
    m.co_seq_medicao,

    -- Temporal do Atendimento
    a.dt_inicio,
    a.dt_fim,
    EXTRACT(YEAR  FROM a.dt_inicio)::INTEGER           AS ano,
    EXTRACT(MONTH FROM a.dt_inicio)::INTEGER           AS mes,
    EXTRACT(QUARTER FROM a.dt_inicio)::INTEGER         AS trimestre,
    DATE_TRUNC('month', a.dt_inicio)::DATE             AS mes_ano,

    -- Unidade de Saude
    u.co_seq_unidade_saude,
    u.no_unidade_saude,
    u.no_unidade_saude_filtro,
    u.no_bairro        AS ubs_bairro,
    u.no_bairro_filtro AS ubs_bairro_filtro,
    u.st_ativo         AS ubs_ativa,

    -- Medicao
    m.nu_medicao_pressao_arterial,
    m.nu_medicao_peso,
    m.nu_medicao_altura,
    m.nu_medicao_imc,
    m.nu_medicao_frequencia_cardiaca,
    m.nu_medicao_glicemia,
    m.nu_medicao_circunf_abdominal,
    m.dt_medicao,

    -- Dados Demograficos do Cidadao
    c.dt_nascimento,
    c.no_bairro        AS cidadao_bairro,
    c.no_bairro_filtro AS cidadao_bairro_filtro,
    c.nu_area,
    c.nu_micro_area,
    c.co_localidade,

    -- Territorio Oficial (ACS) - O grande ganho de qualidade
    t.nu_micro_area     AS territorio_micro_area

FROM public.tb_atend a

-- Caminho obrigatorio: Atendimento -> Prontuario -> Cidadao
INNER JOIN public.tb_prontuario p
    ON a.co_prontuario = p.co_seq_prontuario

INNER JOIN public.tb_cidadao c
    ON p.co_cidadao = c.co_seq_cidadao

-- Territorio do ACS (Pega o registro mais recente de microarea)
LEFT JOIN LATERAL (
    SELECT 
        fc.nu_micro_area
    FROM public.tb_fat_cidadao_territorio fc
    WHERE fc.co_fat_cidadao_pec = c.co_seq_cidadao
    LIMIT 1
) t ON TRUE

-- Unidade de Saude
LEFT JOIN public.tb_unidade_saude u
    ON a.co_unidade_saude = u.co_seq_unidade_saude

-- Profissional
LEFT JOIN public.tb_atend_prof ap
    ON a.co_atend_prof = ap.co_seq_atend_prof

-- Medicoes
LEFT JOIN public.tb_medicao m
    ON ap.co_seq_atend_prof = m.co_atend_prof

WHERE
    a.dt_inicio IS NOT NULL
    AND a.dt_inicio >= (CURRENT_DATE - INTERVAL '10 years')

ORDER BY a.dt_inicio DESC;

-- ── INDICES PARA PERFORMANCE ─────────────────────────────────────────
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_atend_pk
    ON dashboard.mv_atendimento_completo (co_seq_atend, COALESCE(co_seq_medicao, 0));

CREATE INDEX IF NOT EXISTS idx_mv_atend_cidadao ON dashboard.mv_atendimento_completo (co_seq_cidadao);
CREATE INDEX IF NOT EXISTS idx_mv_atend_dt ON dashboard.mv_atendimento_completo (dt_inicio);
CREATE INDEX IF NOT EXISTS idx_mv_atend_ubs ON dashboard.mv_atendimento_completo (co_seq_unidade_saude);

-- ── VIEW AUXILIAR: ULTIMO ANO ────────────────────────────────────────
CREATE OR REPLACE VIEW dashboard.vw_atendimento_ultimo_ano AS
SELECT *
FROM dashboard.mv_atendimento_completo
WHERE dt_inicio >= CURRENT_DATE - INTERVAL '1 year';

COMMENT ON MATERIALIZED VIEW dashboard.mv_atendimento_completo IS
    'Atendimentos consolidados enriquecidos com dados de territorio do ACS. Use COUNT(DISTINCT co_seq_atend) para metricas.';