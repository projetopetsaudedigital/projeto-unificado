-- =====================================================================
-- TABELA DE CONTROLE DE PROCESSAMENTO
-- Schema: dashboard.tb_controle_processamento
--
-- Registra quando cada processamento foi executado, com métricas
-- e status. Permite rastrear histórico de normalizações, treinamentos
-- de modelos e refresh de views.
-- =====================================================================

CREATE TABLE IF NOT EXISTS dashboard.tb_controle_processamento (
    co_seq               SERIAL PRIMARY KEY,
    tp_processamento     VARCHAR(50)  NOT NULL,   -- 'normalizacao_bairros', 'treino_has', 'treino_dm', 'refresh_views'
    dt_inicio            TIMESTAMP    NOT NULL DEFAULT NOW(),
    dt_fim               TIMESTAMP,
    st_status            VARCHAR(20)  NOT NULL DEFAULT 'em_andamento',  -- 'em_andamento', 'concluido', 'erro'
    ds_modelo            VARCHAR(100),             -- nome do modelo (ex: 'ha_risk_rf')
    ds_metricas          JSONB,                    -- métricas de ML ou stats de normalização
    qt_registros         INTEGER,                  -- quantidade de registros processados
    ds_observacao        TEXT,                      -- observações livres
    ds_erro              TEXT                       -- mensagem de erro (se st_status = 'erro')
);

CREATE INDEX IF NOT EXISTS idx_controle_proc_tipo
    ON dashboard.tb_controle_processamento (tp_processamento);

CREATE INDEX IF NOT EXISTS idx_controle_proc_dt
    ON dashboard.tb_controle_processamento (dt_inicio DESC);

COMMENT ON TABLE dashboard.tb_controle_processamento IS
    'Histórico de processamentos: normalizações, treinamentos de ML, refresh de views. '
    'Permite rastrear quando e como cada processamento foi executado.';
