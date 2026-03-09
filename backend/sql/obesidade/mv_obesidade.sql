-- =====================================================================
-- VIEW MATERIALIZADA: MEDICOES ANTROPOMETRICAS (IMC / OBESIDADE)
-- Schema: dashboard.mv_obesidade
-- Usado para: classificacao de IMC, tendencias, fatores de risco,
--             mapa por bairro, predicao individual de obesidade
--
-- Join path:
--   tb_medicao
--   -> tb_atend_prof -> tb_lotacao           (UBS/equipe)
--   -> LATERAL tb_exame_requisitado
--   -> tb_prontuario -> tb_cidadao           (dados demograficos)
--   -> tb_fat_cidadao_pec                   (ID unificado PEC)
--   -> LATERAL tb_fat_cad_individual        (condicoes de saude)
--   -> tb_dim_sexo, tb_dim_raca_cor, tb_dim_tipo_escolaridade
--
-- Classificacao IMC (OMS):
--   < 18.5          -> Baixo Peso
--   18.5 a < 25.0   -> Normal
--   25.0 a < 30.0   -> Sobrepeso
--   30.0 a < 35.0   -> Obesidade I
--   35.0 a < 40.0   -> Obesidade II
--   >= 40.0         -> Obesidade III
--
-- Unidades: nu_medicao_peso em kg, nu_medicao_altura em cm
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_obesidade AS

WITH medicao_valida AS (
    SELECT
        m.co_seq_medicao,
        m.co_atend_prof,
        m.dt_medicao,
        m.nu_medicao_peso::NUMERIC                                 AS peso_kg,
        m.nu_medicao_altura::NUMERIC / 100.0                      AS altura_m,
        -- Recalcula IMC a partir dos valores brutos (nu_medicao_imc pode ter erros)
        m.nu_medicao_peso::NUMERIC / POWER(m.nu_medicao_altura::NUMERIC / 100.0, 2) AS imc,
        m.nu_medicao_circunf_abdominal::NUMERIC                   AS circunf_abdominal_cm
    FROM pec.tb_medicao m
    WHERE
        m.nu_medicao_peso IS NOT NULL
        AND m.nu_medicao_altura IS NOT NULL
        AND m.nu_medicao_peso::NUMERIC BETWEEN 10 AND 350
        AND m.nu_medicao_altura::NUMERIC BETWEEN 100 AND 250
        -- Filtra IMC fisiologicamente impossivel
        AND m.nu_medicao_peso::NUMERIC / POWER(m.nu_medicao_altura::NUMERIC / 100.0, 2) BETWEEN 10 AND 80
        AND m.dt_medicao IS NOT NULL
        AND m.dt_medicao >= (CURRENT_DATE - INTERVAL '10 years')
)

SELECT
    -- Identificadores
    mv.co_seq_medicao,
    mv.co_atend_prof,

    -- UBS e equipe
    lot.co_unidade_saude,
    lot.co_equipe,

    -- ID unificado do cidadao
    pec.co_seq_fat_cidadao_pec,
    c.co_seq_cidadao                                               AS co_cidadao,

    -- Temporal da medicao
    mv.dt_medicao,
    EXTRACT(YEAR  FROM mv.dt_medicao)::INTEGER                     AS ano,
    EXTRACT(MONTH FROM mv.dt_medicao)::INTEGER                     AS mes,
    EXTRACT(QUARTER FROM mv.dt_medicao)::INTEGER                   AS trimestre,
    DATE_TRUNC('month', mv.dt_medicao)::DATE                       AS mes_ano,

    -- Medidas antropometricas
    mv.peso_kg,
    mv.altura_m,
    mv.imc,
    mv.circunf_abdominal_cm,

    -- Classificacao IMC (6 classes OMS)
    CASE
        WHEN mv.imc <  18.5 THEN 'Baixo Peso'
        WHEN mv.imc <  25.0 THEN 'Normal'
        WHEN mv.imc <  30.0 THEN 'Sobrepeso'
        WHEN mv.imc <  35.0 THEN 'Obesidade I'
        WHEN mv.imc <  40.0 THEN 'Obesidade II'
        ELSE                     'Obesidade III'
    END                                                            AS classificacao_imc,

    -- Flag de obesidade grau 2 ou 3 (target secundario)
    CASE WHEN mv.imc >= 35.0 THEN 1 ELSE 0 END                    AS is_obeso_g2_g3,

    -- Dados demograficos do cidadao
    c.dt_nascimento,
    EXTRACT(YEAR FROM AGE(mv.dt_medicao, c.dt_nascimento))::INTEGER AS idade_no_exame,
    CASE
        WHEN EXTRACT(YEAR FROM AGE(mv.dt_medicao, c.dt_nascimento)) < 30 THEN '18-29'
        WHEN EXTRACT(YEAR FROM AGE(mv.dt_medicao, c.dt_nascimento)) < 40 THEN '30-39'
        WHEN EXTRACT(YEAR FROM AGE(mv.dt_medicao, c.dt_nascimento)) < 50 THEN '40-49'
        WHEN EXTRACT(YEAR FROM AGE(mv.dt_medicao, c.dt_nascimento)) < 60 THEN '50-59'
        WHEN EXTRACT(YEAR FROM AGE(mv.dt_medicao, c.dt_nascimento)) < 65 THEN '60-64'
        ELSE '65+'
    END                                                            AS faixa_etaria,

    -- Sexo
    s.ds_sexo,
    s.sg_sexo,

    -- Geolocalizacao
    c.no_bairro,
    c.no_bairro_filtro,
    c.co_localidade,
    c.nu_area,
    c.nu_micro_area,

    -- Condicoes de saude (cadastro individual mais recente)
    COALESCE(cad.st_hipertensao_arterial,  0)                     AS st_hipertensao,
    COALESCE(cad.st_diabete,               0)                     AS st_diabete,
    COALESCE(cad.st_fumante,               0)                     AS st_fumante,
    COALESCE(cad.st_alcool,                0)                     AS st_alcool,
    COALESCE(cad.st_doenca_cardiaca,       0)                     AS st_doenca_cardiaca,
    COALESCE(cad.st_doenca_respiratoria,   0)                     AS st_doenca_respiratoria,
    COALESCE(cad.st_avc,                   0)                     AS st_avc,
    COALESCE(cad.st_problema_rins,         0)                     AS st_problema_rins,

    -- Dimensao sexo (para ML)
    CASE cad.co_dim_sexo WHEN 1 THEN 1 ELSE 3 END                 AS co_dim_sexo,

    -- Raca/cor e escolaridade
    r.ds_raca_cor,
    e.ds_dim_tipo_escolaridade                                     AS ds_escolaridade,

    -- Status vital
    pec.st_faleceu

FROM medicao_valida mv

-- UBS e equipe
LEFT JOIN pec.tb_atend_prof ap
    ON mv.co_atend_prof = ap.co_seq_atend_prof

LEFT JOIN pec.tb_lotacao lot
    ON ap.co_lotacao = lot.co_ator_papel

-- Caminho para o cidadao via exame_requisitado -> prontuario
INNER JOIN LATERAL (
    SELECT er.co_prontuario
    FROM pec.tb_exame_requisitado er
    WHERE er.co_atend_prof = mv.co_atend_prof
      AND er.co_prontuario IS NOT NULL
    ORDER BY er.co_seq_exame_requisitado
    LIMIT 1
) er ON true

INNER JOIN pec.tb_prontuario p
    ON er.co_prontuario = p.co_seq_prontuario

INNER JOIN pec.tb_cidadao c
    ON p.co_cidadao = c.co_seq_cidadao

-- ID unificado PEC
LEFT JOIN pec.tb_fat_cidadao_pec pec
    ON pec.co_cidadao = c.co_seq_cidadao

-- Cadastro individual mais recente para condicoes de saude
LEFT JOIN LATERAL (
    SELECT *
    FROM pec.tb_fat_cad_individual ci
    WHERE ci.co_fat_cidadao_pec = pec.co_seq_fat_cidadao_pec
    ORDER BY ci.co_dim_tempo DESC
    LIMIT 1
) cad ON true

-- Dimensoes demograficas
LEFT JOIN pec.tb_dim_sexo s
    ON cad.co_dim_sexo = s.co_seq_dim_sexo

LEFT JOIN pec.tb_dim_raca_cor r
    ON cad.co_dim_raca_cor = r.co_seq_dim_raca_cor

LEFT JOIN pec.tb_dim_tipo_escolaridade e
    ON cad.co_dim_tipo_escolaridade = e.co_seq_dim_tipo_escolaridade

WHERE
    c.dt_nascimento IS NOT NULL
    AND EXTRACT(YEAR FROM AGE(mv.dt_medicao, c.dt_nascimento)) >= 18
    AND (pec.st_faleceu = 0 OR pec.st_faleceu IS NULL)

ORDER BY c.co_seq_cidadao, mv.dt_medicao DESC;

-- Indices
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_obesidade_pk
    ON dashboard.mv_obesidade (co_seq_medicao);

CREATE INDEX IF NOT EXISTS idx_mv_obesidade_cidadao
    ON dashboard.mv_obesidade (co_cidadao);

CREATE INDEX IF NOT EXISTS idx_mv_obesidade_pec
    ON dashboard.mv_obesidade (co_seq_fat_cidadao_pec);

CREATE INDEX IF NOT EXISTS idx_mv_obesidade_dt
    ON dashboard.mv_obesidade (dt_medicao);

CREATE INDEX IF NOT EXISTS idx_mv_obesidade_ano
    ON dashboard.mv_obesidade (ano);

CREATE INDEX IF NOT EXISTS idx_mv_obesidade_mes_ano
    ON dashboard.mv_obesidade (mes_ano);

CREATE INDEX IF NOT EXISTS idx_mv_obesidade_classificacao
    ON dashboard.mv_obesidade (classificacao_imc);

CREATE INDEX IF NOT EXISTS idx_mv_obesidade_bairro
    ON dashboard.mv_obesidade (no_bairro_filtro);

CREATE INDEX IF NOT EXISTS idx_mv_obesidade_ubs
    ON dashboard.mv_obesidade (co_unidade_saude);

COMMENT ON MATERIALIZED VIEW dashboard.mv_obesidade IS
    'Medicoes antropometricas de adultos (>=18) vivos, ultimos 10 anos. '
    'IMC recalculado a partir de peso (kg) e altura (cm) — filtra valores fisiologicamente impossíveis. '
    'Classificacao OMS em 6 classes: Baixo Peso, Normal, Sobrepeso, Obesidade I/II/III. '
    'Join: tb_medicao -> tb_atend_prof -> tb_lotacao + LATERAL tb_exame_requisitado -> tb_prontuario -> tb_cidadao -> tb_fat_cidadao_pec -> tb_fat_cad_individual. '
    'Atualizar com: REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_obesidade';
