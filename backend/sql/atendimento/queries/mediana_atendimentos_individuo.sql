-- =====================================================================
-- QUERY: Mediana de atendimentos por cidadão no último ano
--
-- Usa COUNT(DISTINCT co_seq_atend) para evitar inflação por medições
-- múltiplas no mesmo atendimento.
-- =====================================================================

SELECT
    PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY total_atendimentos) AS mediana_atendimentos_por_cidadao
FROM (
    SELECT
        co_seq_cidadao,
        COUNT(DISTINCT co_seq_atend) AS total_atendimentos
    FROM dashboard.vw_atendimento_ultimo_ano
    GROUP BY co_seq_cidadao
) sub;

-- =====================================================================
-- VARIAÇÃO: Atendimentos por cidadão em uma USF específica
-- Substituir o placeholder pelo co_seq_unidade_saude desejado.
-- =====================================================================

-- SELECT
--     co_seq_cidadao,
--     COUNT(DISTINCT co_seq_atend) AS total_atendimentos
-- FROM dashboard.vw_atendimento_ultimo_ano
-- WHERE co_seq_unidade_saude = :usf_id
-- GROUP BY co_seq_cidadao
-- ORDER BY total_atendimentos DESC;
