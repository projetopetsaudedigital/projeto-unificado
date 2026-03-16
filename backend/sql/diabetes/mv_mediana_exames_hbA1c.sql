-- =====================================================================
-- VIEW MATERIALIZADA: MEDIANA DE EXAMES DE HbA1c POR USF NO ÚLTIMO ANO (HbA1c)
-- Schema: dashboard.mv_mediana_exames_hbA1c
-- Usado para: Verificar frequência de realização de exames
--
-- Join path (corrigido em relação ao projeto anterior):
--   tb_exame_hemoglobina_glicada
--   → tb_exame_requisitado               (data do exame)
--   → tb_prontuario                      (prontuário do cidadão)
--   → tb_cidadao                         (dados demográficos)
--   → tb_fat_cidadao_pec                 (ID unificado PEC)
--   → tb_fat_cad_individual             (cadastro individual)
--   → tb_dim_unidade_saude              (unidade de saúde)
-- =====================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_mediana_exames_hbA1c AS

WITH exames_por_usf AS (
    SELECT
        USF.co_seq_dim_unidade_saude AS codigo_usf,
        USF.no_unidade_saude AS nome_usf,
        COUNT(EHG.co_exame_requisitado) AS qtd_exames
    FROM tb_exame_requisitado ER
    JOIN tb_prontuario P 
        ON P.co_seq_prontuario = ER.co_prontuario
    JOIN tb_cidadao IND 
        ON IND.co_seq_cidadao = P.co_cidadao
	JOIN tb_fat_cidadao_pec PEC 
	     ON PEC.co_cidadao = IND.co_seq_cidadao
    JOIN tb_fat_cad_individual CI 
	     ON CI.co_fat_cidadao_pec = PEC.co_seq_fat_cidadao_pec  
    JOIN tb_dim_unidade_saude USF 
	     ON USF.co_seq_dim_unidade_saude = CI.co_dim_unidade_saude
    JOIN tb_exame_hemoglobina_glicada EHG 
        ON EHG.co_exame_requisitado = ER.co_seq_exame_requisitado
    WHERE ER.dt_realizacao >= CURRENT_DATE - INTERVAL '1 year'
      AND ER.dt_realizacao IS NOT NULL
    GROUP BY USF.co_seq_dim_unidade_saude, USF.no_unidade_saude
)

SELECT 
    PERCENTILE_CONT(0.5) 
    WITHIN GROUP (ORDER BY qtd_exames) AS mediana_exames_por_usf
FROM exames_por_usf;