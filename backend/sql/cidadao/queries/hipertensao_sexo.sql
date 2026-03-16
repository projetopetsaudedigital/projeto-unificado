-- =========================================================
--  DISTRIBUIÇÃO DE HIPERTENSÃO POR SEXO
--
--  Objetivo:
--  Avaliar a ocorrência de hipertensão entre homens
--  e mulheres cadastrados no sistema.
--
--  Fonte:
--  dashboard.mv_cidadao_info
-- =========================================================

SELECT

    -- 1. SEXO DO PACIENTE
    ds_sexo,

    -- 2. TOTAL DE HIPERTENSOS
    COUNT(*) FILTER (
        WHERE st_hipertensao_arterial = 1
    ) AS hipertensos,

    -- 3. POPULAÇÃO TOTAL
    COUNT(*) AS populacao_total

-- 4. FONTE
FROM dashboard.mv_cidadao_info

-- 5. AGRUPAMENTO
GROUP BY
    ds_sexo

-- 6. ORDENAÇÃO
ORDER BY
    hipertensos DESC;