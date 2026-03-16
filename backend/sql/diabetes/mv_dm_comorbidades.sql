-- =====================================================================
-- VIEW MATERIALIZADA: COMORBIDADES DE UM CIDADÃO NO PEC
-- Schema: dashboard.mv_dm_comorbidade
-- Usado para: listar outras comorbidades dos cidadãos no PEC
--
-- Join path (corrigido em relação ao projeto anterior):
-- tb_cidadao                         (dados demográficos)
--   → tb_prontuario                      (prontuário do cidadão)
--   → tb_problema                       (código CIAP)
--   → tb_ciap                            (classificação de problema de saúde)
--   → tb_fat_cidadao_pec                 (ID unificado PEC)
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_dm_comorbidades AS

WITH individuos_diabetes AS (
    SELECT DISTINCT IND.co_seq_cidadao
    FROM tb_cidadao IND
    JOIN tb_prontuario P 
        ON P.co_cidadao = IND.co_seq_cidadao
    JOIN tb_problema PB 
        ON PB.co_prontuario = P.co_seq_prontuario
    JOIN tb_ciap CIAP 
        ON CIAP.co_seq_ciap = PB.co_ciap
    WHERE CIAP.co_ciap IN ('T89','T90')
)

SELECT 
    IND.co_seq_cidadao AS Codigo_Cidadao,
    CIAP.ds_ciap AS Condicao_Saude
FROM individuos_diabetes D
JOIN tb_cidadao IND 
    ON IND.co_seq_cidadao = D.co_seq_cidadao
JOIN tb_prontuario P 
    ON P.co_cidadao = IND.co_seq_cidadao
JOIN tb_problema PB 
    ON PB.co_prontuario = P.co_seq_prontuario
JOIN tb_ciap CIAP 
    ON CIAP.co_seq_ciap = PB.co_ciap
WHERE CIAP.co_ciap NOT IN ('T89','T90');