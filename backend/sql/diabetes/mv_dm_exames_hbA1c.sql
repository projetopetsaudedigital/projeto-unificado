-- =====================================================================
-- VIEW MATERIALIZADA: ÚLTIMO EXAME DE HEMOGLOBINA GLICADA (HbA1c)
-- Schema: dashboard.mv_dm_exames_hbA1c
-- Usado para: mapear exames de hbA1c
--
-- Join path (corrigido em relação ao projeto anterior):
--   tb_exame_hemoglobina_glicada
--   → tb_exame_requisitado               (data do exame)
--   → tb_prontuario                      (prontuário do cidadão)
--   → tb_cidadao                         (dados demográficos)
--   → tb_fat_cidadao_pec                 (ID unificado PEC)
--   → tb_problema                       (código CIAP)
--   → tb_ciap                            (classificação de problema de saúde)
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_dm_exames_hbA1c AS
SELECT DISTINCT 
-- Identificadores
IND.co_seq_cidadao AS codigo_cidadao, 
-- Valor do exame
EHG.vl_hemoglobina_glicada AS valor_hbA1c, 
-- Temporal do exame
ER.dt_realizacao AS data_exame,
EXTRACT (DAY FROM ER.dt_realizacao)::INTEGER AS dia, 
EXTRACT (MONTH FROM ER.dt_realizacao)::INTEGER AS mes, 
EXTRACT (YEAR FROM ER.dt_realizacao)::INTEGER AS ano
FROM tb_exame_hemoglobina_glicada EHG
JOIN tb_exame_requisitado ER ON ER.co_seq_exame_requisitado = EHG.co_exame_requisitado
JOIN tb_prontuario P ON P.co_seq_prontuario = ER.co_prontuario
JOIN tb_cidadao IND ON IND.co_seq_cidadao = P.co_cidadao
JOIN tb_fat_cidadao_pec PEC ON PEC.co_cidadao = IND.co_seq_cidadao
JOIN tb_problema PB ON PB.co_prontuario = P.co_seq_prontuario 
JOIN tb_ciap CIAP ON CIAP.co_seq_ciap = PB.co_ciap

WHERE EHG.vl_hemoglobina_glicada IS NOT NULL
    AND EHG.vl_hemoglobina_glicada BETWEEN 3 AND 20   
    AND ER.dt_realizacao IS NOT NULL
	AND ER.dt_realizacao >= ALL(SELECT ER1.dt_realizacao
	                            FROM tb_exame_requisitado ER1
								JOIN tb_prontuario P1 ON P1.co_seq_prontuario = ER1.co_prontuario
								JOIN tb_cidadao IND1 ON IND1.co_seq_cidadao = P1.co_cidadao
								JOIN tb_fat_cidadao_pec PEC1 ON PEC1.co_cidadao = IND1.co_seq_cidadao
		                        WHERE ER1.dt_realizacao IS NOT NULL AND IND1.co_seq_cidadao = IND.co_seq_cidadao)
	AND (PEC.st_faleceu = 0 OR PEC.st_faleceu IS NULL)
    AND ER.dt_realizacao >= (CURRENT_DATE - INTERVAL '10 years')
    --filtra pela CIAP (Classificação Internacional de Atenção Primária se tem diabetes ou não)
	AND (CIAP.co_ciap = 'T89' OR CIAP.co_ciap = 'T90')
	ORDER BY IND.co_seq_cidadao ASC;