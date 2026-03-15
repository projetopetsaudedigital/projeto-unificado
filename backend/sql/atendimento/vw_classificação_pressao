-- =========================================================
-- View regular (não materializada) de classificação de
-- pressão arterial baseada em atendimentos recentes.
--
-- Fonte principal:
-- dashboard.mv_atendimento_completo
--
-- Objetivo:
-- Calcular idade, classificação etária, número de medições
-- no último ano e classificar clinicamente a pressão arterial
-- dos pacientes.
--
-- Estratégia:
-- • Utiliza apenas as 3 medições mais recentes de pressão.
-- • Calcula a mediana da pressão sistólica e diastólica.
-- • Aplica critérios clínicos de classificação por faixa etária.
--
-- Observações importantes:
-- • Não duplica dados — apenas analisa registros da materialized view.
-- • Utiliza vw_atendimento_ultimo_ano para limitar as medições
--   ao período de análise.
-- • Considera apenas pacientes com pelo menos uma medição
--   de pressão no último ano.
-- =========================================================
CREATE OR REPLACE VIEW dashboard.vw_classificacao_pressao AS

WITH medicoes AS (

    -- =====================================================
    -- 1. EXTRAÇÃO DAS MEDIÇÕES DE PRESSÃO
    -- =====================================================
    -- Separa pressão sistólica e diastólica a partir
    -- do campo textual de medição
    SELECT

        co_seq_cidadao,
        dt_medicao,

        split_part(nu_medicao_pressao_arterial,'/',1)::INTEGER AS sistolica,
        split_part(nu_medicao_pressao_arterial,'/',2)::INTEGER AS diastolica,

        ROW_NUMBER() OVER(
            PARTITION BY co_seq_cidadao
            ORDER BY dt_medicao DESC
        ) AS rn

    FROM dashboard.vw_atendimento_ultimo_ano

    WHERE nu_medicao_pressao_arterial IS NOT NULL
),

ultimas3 AS (

    -- =====================================================
    -- 2. SELEÇÃO DAS 3 MEDIÇÕES MAIS RECENTES
    -- =====================================================
    SELECT *
    FROM medicoes
    WHERE rn <= 3
),

mediana_pressao AS (

    -- =====================================================
    -- 3. CÁLCULO DA MEDIANA DAS PRESSÕES
    -- =====================================================
    SELECT

        co_seq_cidadao,

        COUNT(*) AS medicoes_no_ultimo_ano,

        PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY sistolica) AS mediana_sistolica,

        PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY diastolica) AS mediana_diastolica

    FROM ultimas3

    GROUP BY co_seq_cidadao
),

cidadao_base AS (

    -- =====================================================
    -- 4. BASE DEMOGRÁFICA DOS PACIENTES
    -- =====================================================
    SELECT DISTINCT

        c.co_seq_cidadao,
        c.dt_nascimento,

        c.co_seq_unidade_saude,
        c.no_unidade_saude,

        EXTRACT(YEAR FROM AGE(CURRENT_DATE,c.dt_nascimento))::INTEGER AS idade

    FROM dashboard.mv_atendimento_completo c
)

-- =========================================================
-- 5. RESULTADO FINAL
-- =========================================================
SELECT

    -- IDENTIFICADORES
    c.co_seq_cidadao,

    -- UNIDADE DE SAÚDE
    c.co_seq_unidade_saude,
    c.no_unidade_saude,

    -- IDADE
    c.idade,

    -- CLASSIFICAÇÃO ETÁRIA
    CASE
        WHEN idade < 12 THEN 'Criança'
        WHEN idade BETWEEN 13 AND 17 THEN 'Adolescente'
        WHEN idade BETWEEN 18 AND 24 THEN 'Jovem'
        WHEN idade BETWEEN 25 AND 64 THEN 'Adulto'
        WHEN idade BETWEEN 65 AND 79 THEN 'Idoso Hígido'
        WHEN idade >= 80 THEN 'Idoso Frágil'
    END AS classificacao_etaria,

    -- DADOS DE MEDIÇÃO
    m.medicoes_no_ultimo_ano,

    CONCAT(
        ROUND(m.mediana_sistolica),
        '/',
        ROUND(m.mediana_diastolica)
    ) AS mediana_pressao,

    -- CLASSIFICAÇÃO CLÍNICA DA PRESSÃO
    CASE

        WHEN idade < 12
        THEN 'Avaliar percentil pediátrico'

        WHEN idade BETWEEN 13 AND 17
        AND (m.mediana_sistolica >= 130 OR m.mediana_diastolica >= 80)
        THEN 'Hipertensão (adolescente)'

        WHEN idade BETWEEN 13 AND 17
        THEN 'Normal'

        WHEN m.mediana_sistolica < 120
        AND m.mediana_diastolica < 80
        THEN 'Normal'

        WHEN m.mediana_sistolica BETWEEN 120 AND 139
        OR m.mediana_diastolica BETWEEN 80 AND 89
        THEN 'Pré-hipertensão'

        WHEN m.mediana_sistolica BETWEEN 140 AND 159
        OR m.mediana_diastolica BETWEEN 90 AND 99
        THEN 'Hipertensão Estágio 1'

        WHEN m.mediana_sistolica BETWEEN 160 AND 179
        OR m.mediana_diastolica BETWEEN 100 AND 109
        THEN 'Hipertensão Estágio 2'

        WHEN m.mediana_sistolica >= 180
        OR m.mediana_diastolica >= 110
        THEN 'Hipertensão Estágio 3'

    END AS classificacao_pressao

FROM cidadao_base c

LEFT JOIN mediana_pressao m
ON c.co_seq_cidadao = m.co_seq_cidadao

-- =====================================================
-- 6. FILTRO FINAL
-- Considera apenas pacientes com medições registradas
-- =====================================================
WHERE m.medicoes_no_ultimo_ano > 0;

COMMENT ON VIEW dashboard.vw_classificacao_pressao IS
    'View analítica de classificação de pressão arterial baseada em dados de atendimento. '
    'Calcula idade, classificação etária, número de medições no último ano e mediana das 3 medições mais recentes. '
    'Aplica critérios clínicos para classificar a pressão arterial dos pacientes. '
    'Utiliza vw_atendimento_ultimo_ano como filtro temporal e mv_atendimento_completo como base de dados. '
    'Não requer REFRESH — acompanha automaticamente as views e materialized views de origem.';