-- =====================================================================
-- VIEW MATERIALIZADA: CADASTRO CONSOLIDADO DO CIDADAO
-- Schema: dashboard.mv_cidadao_info
--
-- Objetivo:
-- Consolidar dados cadastrais, demográficos e clínicos do cidadão
-- para análises epidemiológicas e territoriais.
--
-- Caminho de joins:
--
-- tb_cidadao
--   -> tb_prontuario
--
-- tb_cidadao
--   -> tb_fat_cidadao_pec
--        -> tb_fat_cad_individual
--             -> tb_dim_sexo
--
-- tb_prontuario
--   -> tb_atestado
--        -> tb_cid10
--
-- tb_fat_cidadao_pec
--   -> tb_fat_cidadao_territorio
--
-- Regras aplicadas:
--
-- • Remove cidadãos falecidos
-- • Normaliza flags clínicas (NULL → 0)
-- • Calcula idade
-- • Busca território oficial do ACS
-- • Evita duplicação de cidadãos causada por múltiplos CID10
-- • Mantém apenas cidadãos com prontuário
--
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS dashboard;

CREATE MATERIALIZED VIEW dashboard.mv_cidadao_info AS

SELECT DISTINCT ON (c.co_seq_cidadao)

    -- =====================================================
    -- IDENTIFICADORES
    -- =====================================================

    c.co_seq_cidadao,
    p.co_seq_prontuario,
    fcp.co_seq_fat_cidadao_pec,
    fci.co_seq_fat_cad_individual,

    -- =====================================================
    -- TERRITÓRIO OFICIAL (ACS)
    -- =====================================================

    territorio.nu_micro_area           AS nu_micro_area,
    territorio.co_dim_unidade_saude,

    -- =====================================================
    -- DADOS CADASTRAIS DO CIDADÃO
    -- =====================================================

    c.nu_area,
    c.no_bairro,
    c.no_bairro_filtro,
    c.co_localidade,
    c.co_uf,
    c.ds_logradouro,
    c.nu_numero,
    c.ds_cep,

    -- =====================================================
    -- SEXO
    -- =====================================================

    s.ds_sexo,
    s.sg_sexo,

    -- =====================================================
    -- NASCIMENTO E IDADE
    -- =====================================================

    fci.dt_nascimento,

    EXTRACT(YEAR FROM AGE(CURRENT_DATE, fci.dt_nascimento))::INTEGER
        AS idade,

    -- =====================================================
    -- CONDIÇÕES CLÍNICAS (NORMALIZADAS)
    -- =====================================================

    COALESCE(fci.st_hipertensao_arterial,0)        AS st_hipertensao_arterial,
    COALESCE(fci.st_diabete,0)                     AS st_diabete,
    COALESCE(fci.st_doenca_cardiaca,0)             AS st_doenca_cardiaca,
    COALESCE(fci.st_doenca_card_insuficiencia,0)   AS st_doenca_card_insuficiencia,
    COALESCE(fci.st_problema_rins,0)               AS st_problema_rins,
    COALESCE(fci.st_problema_rins_insuficiencia,0) AS st_problema_rins_insuficiencia,
    COALESCE(fci.st_avc,0)                         AS st_avc,
    COALESCE(fci.st_infarto,0)                     AS st_infarto,
    COALESCE(fci.st_doenca_respiratoria,0)         AS st_doenca_respiratoria,
    COALESCE(fci.st_cancer,0)                      AS st_cancer,
    COALESCE(fci.st_hanseniase,0)                  AS st_hanseniase,
    COALESCE(fci.st_tuberculose,0)                 AS st_tuberculose,

    -- =====================================================
    -- CID10 (ATESTADOS)
    -- =====================================================

    COALESCE(cid.nu_cid10_filtro, '0') AS nu_cid10_filtro,

	COALESCE(cid.no_cid10, 'Sem diagnóstico informado')
    AS no_cid10

FROM public.tb_cidadao c

-- =====================================================
-- PRONTUÁRIO
-- =====================================================

INNER JOIN public.tb_prontuario p
    ON p.co_cidadao = c.co_seq_cidadao

-- =====================================================
-- FAT CIDADAO PEC
-- =====================================================

INNER JOIN public.tb_fat_cidadao_pec fcp
    ON fcp.co_cidadao = c.co_seq_cidadao

-- =====================================================
-- CADASTRO INDIVIDUAL
-- =====================================================

INNER JOIN public.tb_fat_cad_individual fci
    ON fci.co_fat_cidadao_pec = fcp.co_seq_fat_cidadao_pec

-- =====================================================
-- SEXO
-- =====================================================

LEFT JOIN public.tb_dim_sexo s
    ON s.co_seq_dim_sexo = fci.co_dim_sexo

-- =====================================================
-- TERRITÓRIO ACS
-- =====================================================

LEFT JOIN LATERAL (
    SELECT
        ft.nu_micro_area,
        ft.co_dim_unidade_saude
    FROM public.tb_fat_cidadao_territorio ft
    WHERE ft.co_fat_cidadao_pec = fcp.co_seq_fat_cidadao_pec
    LIMIT 1
) territorio ON TRUE

-- =====================================================
-- CID10 (PEGANDO APENAS UM POR PRONTUÁRIO)
-- =====================================================

LEFT JOIN LATERAL (
    SELECT
        c10.nu_cid10_filtro,
        c10.no_cid10
    FROM public.tb_atestado at
    JOIN public.tb_cid10 c10
        ON c10.co_cid10 = at.co_cid10
    WHERE at.co_prontuario = p.co_seq_prontuario
    LIMIT 1
) cid ON TRUE
-- =====================================================
-- FILTRO: REMOVER FALECIDOS
-- =====================================================

WHERE
    COALESCE(fcp.st_faleceu,0) = 0

ORDER BY
    c.co_seq_cidadao,
    fci.dt_nascimento DESC;

CREATE UNIQUE INDEX idx_mv_cidadao_pk
ON dashboard.mv_cidadao_info (co_seq_cidadao);

CREATE INDEX idx_mv_cidadao_microarea
ON dashboard.mv_cidadao_info (nu_micro_area);

CREATE INDEX idx_mv_cidadao_unidade
ON dashboard.mv_cidadao_info (co_dim_unidade_saude);

COMMENT ON MATERIALIZED VIEW dashboard.mv_cidadao_info IS
'Cidadãos consolidados com dados demográficos, condições clínicas, território ACS e CID10 .';