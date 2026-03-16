-- =====================================================================
-- VIEW MATERIALIZADA: DESCONTROLE GLICÊMICO AGRUPADO POR USF (HbA1c)
-- Schema: dashboard.mv_dm_descontrole_usf
-- Usado para: listar quantidade indivíduos em descontrole glicêmico por usf
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
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_dm_descontrole_usf AS

SELECT COUNT(DISTINCT(IND.co_seq_cidadao)) AS Quantidade_Controle, USF.co_seq_dim_unidade_saude AS Codigo_USF, USF.no_unidade_saude AS Nome_USF
FROM tb_cidadao IND
JOIN tb_prontuario P ON P.co_cidadao = IND.co_seq_cidadao
JOIN tb_exame_requisitado ER ON ER.co_prontuario = P.co_seq_prontuario 
JOIN tb_exame_hemoglobina_glicada EHG ON EHG.co_exame_requisitado = ER.co_seq_exame_requisitado
JOIN tb_fat_cidadao_pec PEC ON PEC.co_cidadao = IND.co_seq_cidadao
JOIN tb_fat_cad_individual CI ON CI.co_fat_cidadao_pec = PEC.co_seq_fat_cidadao_pec  
JOIN tb_dim_unidade_saude USF ON USF.co_seq_dim_unidade_saude = CI.co_dim_unidade_saude
JOIN tb_problema PB ON PB.co_prontuario = P.co_seq_prontuario 
JOIN tb_ciap CIAP ON CIAP.co_seq_ciap = PB.co_ciap
WHERE EHG.vl_hemoglobina_glicada IS NOT NULL
    AND EHG.vl_hemoglobina_glicada BETWEEN 3 AND 20   
	AND ((EXTRACT(YEAR FROM AGE(ER.dt_realizacao, IND.dt_nascimento)) < 65
	     AND EHG.vl_hemoglobina_glicada >=  7.0)
		 OR 
		 (EXTRACT(YEAR FROM AGE(ER.dt_realizacao, IND.dt_nascimento)) BETWEEN 65 AND 79
	     AND EHG.vl_hemoglobina_glicada >=  7.5)
		 OR
		 (EXTRACT(YEAR FROM AGE(ER.dt_realizacao, IND.dt_nascimento)) >= 80
	     AND EHG.vl_hemoglobina_glicada >= 8.0))
    AND ER.dt_realizacao IS NOT NULL
	AND ER.dt_realizacao = (
                            SELECT MAX(ER1.dt_realizacao)
                            FROM tb_exame_requisitado ER1
                            JOIN tb_prontuario P1 
                            ON P1.co_seq_prontuario = ER1.co_prontuario
                            WHERE P1.co_cidadao = IND.co_seq_cidadao
							)
	AND (PEC.st_faleceu = 0 OR PEC.st_faleceu IS NULL)
    AND ER.dt_realizacao >= (CURRENT_DATE - INTERVAL '10 years')
	--filtra pela CIAP (Classificação Internacional de Atenção Primária se tem diabetes ou não)
	AND (CIAP.co_ciap = 'T89' OR CIAP.co_ciap = 'T90')
	GROUP BY Codigo_USF, Nome_USF;