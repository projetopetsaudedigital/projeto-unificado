-- =====================================================================
-- QUERY: Mediana de atendimentos realizados por USF no último ano
--
-- Usa COUNT(DISTINCT co_seq_atend) para evitar inflação por medições
-- múltiplas no mesmo atendimento.
-- =====================================================================

SELECT
    PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY total_atendimentos) AS mediana_atendimentos_por_usf
FROM (
    SELECT
        co_seq_unidade_saude,
        no_unidade_saude,
        COUNT(DISTINCT co_seq_atend) AS total_atendimentos
    FROM dashboard.vw_atendimento_ultimo_ano
    WHERE co_seq_unidade_saude IS NOT NULL
    GROUP BY co_seq_unidade_saude, no_unidade_saude
) sub;

-- =====================================================================
-- VARIAÇÃO: Detalhamento por USF (ranking)
-- Útil para painel de gestão — mostra cada USF com seu total.
-- =====================================================================

SELECT
    co_seq_unidade_saude,
    no_unidade_saude,
    COUNT(DISTINCT co_seq_atend) AS total_atendimentos
FROM dashboard.vw_atendimento_ultimo_ano
WHERE co_seq_unidade_saude IS NOT NULL
GROUP BY co_seq_unidade_saude, no_unidade_saude
ORDER BY total_atendimentos DESC;
