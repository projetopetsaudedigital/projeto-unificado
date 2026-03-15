-- =========================================================
--  DISTRIBUIÇÃO DE HIPERTENSÃO POR FAIXA ETÁRIA
--
--  Objetivo:
--  Identificar a prevalência de hipertensão nas
--  diferentes faixas etárias da população cadastrada.
--
--  Fonte:
--  dashboard.mv_cidadao_info
-- =========================================================

SELECT

    -- 1. CLASSIFICAÇÃO DA FAIXA ETÁRIA
    CASE
        WHEN idade < 18 THEN '0-17 anos'
        WHEN idade BETWEEN 18 AND 39 THEN '18-39 anos'
        WHEN idade BETWEEN 40 AND 59 THEN '40-59 anos'
        ELSE '60 anos ou mais'
    END AS faixa_etaria,

    -- 2. TOTAL DE HIPERTENSOS
    COUNT(*) FILTER (
        WHERE st_hipertensao_arterial = 1
    ) AS hipertensos,

    -- 3. POPULAÇÃO TOTAL DA FAIXA
    COUNT(*) AS populacao_total

-- 4. FONTE DE DADOS
FROM dashboard.mv_cidadao_info

-- 5. AGREGAÇÃO
GROUP BY
    faixa_etaria

-- 6. ORDENAÇÃO
ORDER BY
    faixa_etaria;