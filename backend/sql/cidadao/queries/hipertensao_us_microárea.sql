-- =========================================================
--  PREVALÊNCIA DE HIPERTENSÃO POR TERRITÓRIO
--  (UBS + MICROÁREA)
--
--  Objetivo:
--  Identificar territórios com maior risco
--  cardiovascular na população cadastrada.
--
--  Fonte:
--  dashboard.mv_cidadao_info
-- =========================================================

SELECT

    -- 1. UNIDADE DE SAÚDE
    co_dim_unidade_saude,

    -- 2. MICROÁREA
    nu_micro_area,

    -- 3. TOTAL DE HIPERTENSOS
    COUNT(*) FILTER (
        WHERE st_hipertensao_arterial = 1
    ) AS hipertensos,

    -- 4. POPULAÇÃO TOTAL
    COUNT(*) AS populacao_total,

    -- 5. PREVALÊNCIA PERCENTUAL
    ROUND(
        100.0 *
        COUNT(*) FILTER (
            WHERE st_hipertensao_arterial = 1
        ) / COUNT(*),
        2
    ) AS prevalencia_percentual

-- 6. FONTE
FROM dashboard.mv_cidadao_info

-- 7. AGREGAÇÃO
GROUP BY
    co_dim_unidade_saude,
    nu_micro_area

-- 8. ORDENAÇÃO
ORDER BY
    prevalencia_percentual DESC;