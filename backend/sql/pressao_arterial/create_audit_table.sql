-- ============================================================
-- TABELA DE AUDITORIA DE OUTLIERS — PRESSÃO ARTERIAL
-- Schema: dashboard
-- Criada automaticamente pela API no startup, mas pode ser
-- executada manualmente para inspeção ou recriação.
-- ============================================================

CREATE SCHEMA IF NOT EXISTS dashboard;

-- Remover se quiser recriar do zero:
-- DROP TABLE IF EXISTS dashboard.tb_auditoria_outliers;

CREATE TABLE IF NOT EXISTS dashboard.tb_auditoria_outliers (
    co_seq_auditoria    SERIAL PRIMARY KEY,

    -- Referência ao registro original (pode ser NULL se não mapeável)
    co_seq_medicao      INTEGER,
    co_seq_cidadao      INTEGER,

    -- Dado original e valores extraídos
    nu_pa_original      VARCHAR(20),
    pas_valor           NUMERIC(6,1),
    pad_valor           NUMERIC(6,1),

    -- Tipo do outlier detectado
    -- 'range_fisiologico' → fora dos limites absolutos
    -- 'iqr_populacional'  → IQR na população geral
    -- 'zscore_individual' → z-score no histórico do paciente
    tp_outlier          VARCHAR(30) NOT NULL,

    -- Descrição detalhada do motivo (ex: "PAS=290 extrema; Z=4.2")
    ds_motivo           TEXT,

    -- Z-score calculado (somente para tp_outlier = 'zscore_individual')
    vl_zscore           NUMERIC(8,4),

    -- Auditoria
    dt_deteccao         TIMESTAMP NOT NULL DEFAULT NOW(),

    -- 0 = pendente de revisão
    -- 1 = confirmado como erro (dado inválido, não usar nas análises)
    -- 2 = confirmado como dado real (manter nas análises)
    st_revisado         SMALLINT NOT NULL DEFAULT 0
        CHECK (st_revisado IN (0, 1, 2)),

    ds_observacao       TEXT  -- anotação livre do revisor
);

-- Índices para consultas rápidas
CREATE INDEX IF NOT EXISTS idx_audit_outlier_medicao
    ON dashboard.tb_auditoria_outliers (co_seq_medicao);

CREATE INDEX IF NOT EXISTS idx_audit_outlier_cidadao
    ON dashboard.tb_auditoria_outliers (co_seq_cidadao);

CREATE INDEX IF NOT EXISTS idx_audit_outlier_revisado
    ON dashboard.tb_auditoria_outliers (st_revisado);

CREATE INDEX IF NOT EXISTS idx_audit_outlier_tipo
    ON dashboard.tb_auditoria_outliers (tp_outlier);

-- Comentários
COMMENT ON TABLE dashboard.tb_auditoria_outliers IS
    'Registros de pressão arterial com valores suspeitos detectados '
    'pelo pipeline de qualidade. Pendentes de revisão humana.';

COMMENT ON COLUMN dashboard.tb_auditoria_outliers.st_revisado IS
    '0=pendente | 1=confirmado_erro | 2=confirmado_real';

COMMENT ON COLUMN dashboard.tb_auditoria_outliers.tp_outlier IS
    'range_fisiologico | iqr_populacional | zscore_individual';

-- ============================================================
-- Consultas úteis para gestão da tabela de auditoria:
-- ============================================================

-- Total por status:
-- SELECT st_revisado, COUNT(*) FROM dashboard.tb_auditoria_outliers GROUP BY 1;

-- Pendentes mais antigos:
-- SELECT * FROM dashboard.tb_auditoria_outliers
-- WHERE st_revisado = 0 ORDER BY dt_deteccao ASC LIMIT 20;

-- Marcar como erro de digitação:
-- UPDATE dashboard.tb_auditoria_outliers
-- SET st_revisado = 1, ds_observacao = 'Erro de digitação confirmado'
-- WHERE co_seq_auditoria = 123;

-- Marcar como dado real:
-- UPDATE dashboard.tb_auditoria_outliers
-- SET st_revisado = 2, ds_observacao = 'Crise hipertensiva confirmada em prontuário'
-- WHERE co_seq_auditoria = 456;
