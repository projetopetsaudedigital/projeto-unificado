-- =====================================================================
-- VIEW MATERIALIZADA: EXAMES DE HEMOGLOBINA GLICADA (HbA1c)
-- Schema: dashboard.mv_dm_hemoglobina
-- Usado para: controle glicêmico, tendências, risco individual
--
-- Join path (corrigido em relação ao projeto anterior):
--   tb_exame_hemoglobina_glicada
--   → tb_exame_requisitado               (data do exame)
--   → tb_prontuario                      (prontuário do cidadão)
--   → tb_cidadao                         (dados demográficos)
--   → tb_fat_cidadao_pec                 (ID unificado PEC)
--   → tb_fat_cad_individual              (condições de saúde)
--
-- Classificação de controle glicêmico (SBD 2024):
--   Adultos (18-64):  < 7.0%  = Controlado   /  >= 7.0%  = Descontrolado
--   Idosos (65-79):   < 7.5%  = Controlado   /  >= 7.5%  = Descontrolado
--   Idosos (80+):     < 8.0%  = Controlado   /  >= 8.0%  = Descontrolado
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_dm_hemoglobina AS

SELECT
    -- Identificadores
    hg.co_seq_exame_hemoglobina_glicd AS co_seq_hemoglobina_glicada,
    er.co_seq_exame_requisitado,
    pec.co_seq_fat_cidadao_pec,
    c.co_seq_cidadao                                          AS co_cidadao,

    -- Temporal do exame
    er.dt_realizacao                                          AS dt_exame,
    EXTRACT(YEAR  FROM er.dt_realizacao)::INTEGER             AS ano,
    EXTRACT(MONTH FROM er.dt_realizacao)::INTEGER             AS mes,
    EXTRACT(QUARTER FROM er.dt_realizacao)::INTEGER           AS trimestre,
    DATE_TRUNC('month', er.dt_realizacao)::DATE               AS mes_ano,

    -- Valor do exame
    hg.vl_hemoglobina_glicada                                 AS hba1c,

    -- Demográficas (na data do exame)
    EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento))::INTEGER AS idade_no_exame,
    CASE
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 30 THEN '18-29'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 40 THEN '30-39'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 50 THEN '40-49'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 60 THEN '50-59'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 65 THEN '60-64'
        ELSE '65+'
    END                                                       AS faixa_etaria,

    -- Grupo etário para classificação de controle
    CASE
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 65  THEN 'adulto'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 80  THEN 'idoso_65_79'
        ELSE                                                                       'idoso_80+'
    END                                                       AS grupo_etario,

    -- Classificação de controle glicêmico
    CASE
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 65
            AND hg.vl_hemoglobina_glicada <  7.0 THEN 'Controlado'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) < 65
            AND hg.vl_hemoglobina_glicada >= 7.0 THEN 'Descontrolado'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) BETWEEN 65 AND 79
            AND hg.vl_hemoglobina_glicada <  7.5 THEN 'Controlado'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) BETWEEN 65 AND 79
            AND hg.vl_hemoglobina_glicada >= 7.5 THEN 'Descontrolado'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) >= 80
            AND hg.vl_hemoglobina_glicada <  8.0 THEN 'Controlado'
        WHEN EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) >= 80
            AND hg.vl_hemoglobina_glicada >= 8.0 THEN 'Descontrolado'
    END                                                       AS controle_glicemico,

    -- Sexo
    s.ds_sexo,
    s.sg_sexo,

    -- Geolocalização
    c.no_bairro,
    c.no_bairro_filtro,

    -- Condições de saúde (do cadastro individual mais recente via PEC)
    COALESCE(cad.st_hipertensao_arterial, 0)                  AS st_hipertensao,
    COALESCE(cad.st_doenca_cardiaca, 0)                       AS st_doenca_cardiaca,
    COALESCE(cad.st_doenca_card_insuficiencia, 0)             AS st_insuf_cardiaca,
    COALESCE(cad.st_infarto, 0)                               AS st_infarto,
    COALESCE(cad.st_problema_rins, 0)                         AS st_problema_rins,
    COALESCE(cad.st_avc, 0)                                   AS st_avc,
    COALESCE(cad.st_fumante, 0)                               AS st_fumante,
    COALESCE(cad.st_alcool, 0)                                AS st_alcool,
    COALESCE(cad.st_doenca_respiratoria, 0)                   AS st_doenca_respiratoria,
    COALESCE(cad.st_cancer, 0)                                AS st_cancer,

    -- Raça/cor e escolaridade
    r.ds_raca_cor,
    e.ds_dim_tipo_escolaridade                                AS ds_escolaridade,

    -- UBS (via tb_atend_prof → tb_lotacao, se disponível)
    pec.st_faleceu

FROM pec.tb_exame_hemoglobina_glicada hg

INNER JOIN pec.tb_exame_requisitado er
    ON hg.co_exame_requisitado = er.co_seq_exame_requisitado

INNER JOIN pec.tb_prontuario p
    ON er.co_prontuario = p.co_seq_prontuario

INNER JOIN pec.tb_cidadao c
    ON p.co_cidadao = c.co_seq_cidadao

LEFT JOIN pec.tb_fat_cidadao_pec pec
    ON pec.co_cidadao = c.co_seq_cidadao

-- Cadastro individual mais recente para o cidadão (DISTINCT ON)
LEFT JOIN LATERAL (
    SELECT *
    FROM pec.tb_fat_cad_individual ci
    WHERE ci.co_fat_cidadao_pec = pec.co_seq_fat_cidadao_pec
      AND ci.st_diabete = 1
    ORDER BY ci.co_dim_tempo DESC
    LIMIT 1
) cad ON true

LEFT JOIN pec.tb_dim_sexo s
    ON cad.co_dim_sexo = s.co_seq_dim_sexo

LEFT JOIN pec.tb_dim_raca_cor r
    ON cad.co_dim_raca_cor = r.co_seq_dim_raca_cor

LEFT JOIN pec.tb_dim_tipo_escolaridade e
    ON cad.co_dim_tipo_escolaridade = e.co_seq_dim_tipo_escolaridade

WHERE
    hg.vl_hemoglobina_glicada IS NOT NULL
    AND hg.vl_hemoglobina_glicada BETWEEN 3 AND 20   -- range fisiológico
    AND er.dt_realizacao IS NOT NULL
    AND er.dt_realizacao >= (CURRENT_DATE - INTERVAL '10 years')
    AND c.dt_nascimento IS NOT NULL
    AND EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) >= 18
    AND (pec.st_faleceu = 0 OR pec.st_faleceu IS NULL)
    -- Só quem tem diabetes no cadastro
    AND cad.co_seq_fat_cad_individual IS NOT NULL

ORDER BY c.co_seq_cidadao, er.dt_realizacao DESC;

-- Índices
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_dm_hba1c_pk
    ON dashboard.mv_dm_hemoglobina (co_seq_hemoglobina_glicada);

CREATE INDEX IF NOT EXISTS idx_mv_dm_hba1c_cidadao
    ON dashboard.mv_dm_hemoglobina (co_cidadao);

CREATE INDEX IF NOT EXISTS idx_mv_dm_hba1c_pec
    ON dashboard.mv_dm_hemoglobina (co_seq_fat_cidadao_pec);

CREATE INDEX IF NOT EXISTS idx_mv_dm_hba1c_dt
    ON dashboard.mv_dm_hemoglobina (dt_exame);

CREATE INDEX IF NOT EXISTS idx_mv_dm_hba1c_ano
    ON dashboard.mv_dm_hemoglobina (ano);

CREATE INDEX IF NOT EXISTS idx_mv_dm_hba1c_mes_ano
    ON dashboard.mv_dm_hemoglobina (mes_ano);

CREATE INDEX IF NOT EXISTS idx_mv_dm_hba1c_controle
    ON dashboard.mv_dm_hemoglobina (controle_glicemico);

CREATE INDEX IF NOT EXISTS idx_mv_dm_hba1c_bairro
    ON dashboard.mv_dm_hemoglobina (no_bairro_filtro);

COMMENT ON MATERIALIZED VIEW dashboard.mv_dm_hemoglobina IS
    'Exames de HbA1c de pacientes diabéticos adultos (>=18) vivos, últimos 10 anos. '
    'Join correto: tb_exame_hemoglobina_glicada → tb_exame_requisitado → tb_prontuario → tb_cidadao → tb_fat_cidadao_pec → tb_fat_cad_individual. '
    'Inclui classificação de controle glicêmico por grupo etário (SBD 2024). '
    'Atualizar com: REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_dm_hemoglobina';
