-- =====================================================================
-- VIEW MATERIALIZADA: listagem de pacientes em controle e descontrole da glicemia
-- Schema: dashboard.mv_dm_cidadaos_usf
-- Usado para: controle glicêmico, tendências, risco individual
--
-- Join path (corrigido em relação ao projeto anterior):
--   tb_exame_hemoglobina_glicada
--   → tb_exame_requisitado               (data do exame)
--   → tb_prontuario                      (prontuário do cidadão)
--   → tb_cidadao                         (dados demográficos)
--   → tb_fat_cidadao_pec                 (ID unificado PEC)
--   → tb_fat_cad_individual             (cadastro individual)
--   → tb_dim_unidade_saude              (unidade de saúde)
--   → tb_problema                       (código CIAP)
--   → tb_ciap                            (classificação de problema de saúde)
--
-- Classificação de controle glicêmico (SBD 2024):
--   Adultos (18-64):  < 7.0%  = Controlado   /  >= 7.0%  = Descontrolado
--   Idosos (65-79):   < 7.5%  = Controlado   /  >= 7.5%  = Descontrolado
--   Idosos (80+):     < 8.0%  = Controlado   /  >= 8.0%  = Descontrolado
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_dm_cidadaos_usf AS

SELECT
    -- Identificadores
    c.co_seq_cidadao                                          AS co_cidadao,

    -- Temporal do exame
    er.dt_realizacao                                          AS dt_exame,

    -- Valor do exame
    hg.vl_hemoglobina_glicada                                 AS hba1c,

    -- Unidade de saúde
    usf.co_seq_dim_unidade_saude                              AS co_usf,
    usf.no_unidade_saude                                      AS usf,

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
    c.no_sexo AS sexo

FROM tb_exame_hemoglobina_glicada hg

INNER JOIN tb_exame_requisitado er
    ON hg.co_exame_requisitado = er.co_seq_exame_requisitado

INNER JOIN tb_prontuario p
    ON er.co_prontuario = p.co_seq_prontuario

INNER JOIN tb_problema pb
    ON pb.co_prontuario = p.co_seq_prontuario

INNER JOIN tb_ciap ciap
   ON ciap.co_seq_ciap = pb.co_ciap

INNER JOIN tb_cidadao c
    ON p.co_cidadao = c.co_seq_cidadao

LEFT JOIN tb_fat_cidadao_pec pec
    ON pec.co_cidadao = c.co_seq_cidadao

-- Cadastro individual mais recente para o cidadão (DISTINCT ON)
LEFT JOIN LATERAL (
    SELECT co_seq_fat_cad_individual, co_dim_unidade_saude
    FROM tb_fat_cad_individual ci
    WHERE ci.co_fat_cidadao_pec = pec.co_seq_fat_cidadao_pec
      AND ci.st_diabete = 1
    ORDER BY ci.co_dim_tempo DESC
    LIMIT 1
) cad ON true

LEFT JOIN tb_dim_unidade_saude usf
    ON cad.co_dim_unidade_saude = usf.co_seq_dim_unidade_saude

WHERE
    hg.vl_hemoglobina_glicada IS NOT NULL
    AND hg.vl_hemoglobina_glicada BETWEEN 3 AND 20  
    AND er.dt_realizacao IS NOT NULL
    AND er.dt_realizacao >= (CURRENT_DATE - INTERVAL '10 years')
    AND c.dt_nascimento IS NOT NULL
    AND EXTRACT(YEAR FROM AGE(er.dt_realizacao, c.dt_nascimento)) >= 18
    AND er.dt_realizacao = (
                            SELECT MAX(er1.dt_realizacao)
                            FROM tb_exame_requisitado er1
                            JOIN tb_prontuario p1 
                            ON p1.co_seq_prontuario = er1.co_prontuario
                            WHERE p1.co_cidadao = c.co_seq_cidadao
							)
    AND (pec.st_faleceu = 0 OR pec.st_faleceu IS NULL)
    -- Só quem tem diabetes no cadastro
    AND (ciap.co_ciap = 'T89' OR ciap.co_ciap = 'T90')
    AND cad.co_seq_fat_cad_individual IS NOT NULL

ORDER BY c.co_seq_cidadao, er.dt_realizacao DESC;
