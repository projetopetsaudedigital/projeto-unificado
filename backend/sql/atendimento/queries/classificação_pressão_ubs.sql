	-- =========================================================
--  ANÁLISE  DE PRESSÃO ARTERIAL POR UNIDADE
--  DE SAÚDE (US)

--  Fonte:
--  dashboard.vw_classificacao_pressao
-- =========================================================

SELECT

    -- 1. IDENTIFICADORES DA UNIDADE DE SAÚDE
    -- Código sequencial da unidade de saúde
    co_seq_unidade_saude,

    -- Nome da unidade de saúde
    no_unidade_saude,

    -- 2. COBERTURA DE AFERIÇÃO DE PRESSÃO
    -- Total de pacientes com ao menos uma medição
    COUNT(*) AS pacientes_com_medicao,

    -- 3. PRESSÃO NORMAL
    COUNT(*) FILTER (
        WHERE classificacao_pressao = 'Normal'
    ) AS pressao_normal,

    -- 4. PRÉ-HIPERTENSÃO
    COUNT(*) FILTER (
        WHERE classificacao_pressao = 'Pré-hipertensão'
    ) AS pre_hipertensao,

    -- 5. HIPERTENSÃO EM ADOLESCENTES
    COUNT(*) FILTER (
        WHERE classificacao_pressao = 'Hipertensão (adolescente)'
    ) AS hipertensao_adolescente,

    -- 6. HIPERTENSÃO ESTÁGIO 1
    COUNT(*) FILTER (
        WHERE classificacao_pressao = 'Hipertensão Estágio 1'
    ) AS hipertensao_estagio_1,

    -- 7. HIPERTENSÃO ESTÁGIO 2
    COUNT(*) FILTER (
        WHERE classificacao_pressao = 'Hipertensão Estágio 2'
    ) AS hipertensao_estagio_2,

    -- 8. HIPERTENSÃO ESTÁGIO 3
    COUNT(*) FILTER (
        WHERE classificacao_pressao = 'Hipertensão Estágio 3'
    ) AS hipertensao_estagio_3,

    -- 9. CASOS PEDIÁTRICOS
    -- Crianças que necessitam avaliação por percentil
    COUNT(*) FILTER (
        WHERE classificacao_pressao = 'Avaliar percentil pediátrico'
    ) AS crianças_avaliacao_percentil

-- 10. FONTE DE DADOS
FROM dashboard.vw_classificacao_pressao

-- 11. AGREGAÇÃO
-- Agrupa resultados por unidade de saúde
GROUP BY
    co_seq_unidade_saude,
    no_unidade_saude

-- 12. ORDENAÇÃO
-- Ordena pela maior quantidade total de hipertensos
ORDER BY
    (COUNT(*) FILTER (
        WHERE classificacao_pressao LIKE 'Hipertensão%'
    )) DESC;