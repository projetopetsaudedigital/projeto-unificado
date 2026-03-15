-- =====================================================================
-- VIEW: ATENDIMENTOS DO ÚLTIMO ANO
-- Schema: dashboard.vw_atendimento_ultimo_ano
--
-- View regular (não materializada) sobre mv_atendimento_completo.
-- Filtro temporal para as análises que pedem "último ano".
-- Não duplica dados — apenas filtra a materialized view.
-- =====================================================================

CREATE OR REPLACE VIEW dashboard.vw_atendimento_ultimo_ano AS
SELECT *
FROM dashboard.mv_atendimento_completo
WHERE dt_inicio >= CURRENT_DATE - INTERVAL '1 year';

COMMENT ON VIEW dashboard.vw_atendimento_ultimo_ano IS
    'Filtro de último ano sobre mv_atendimento_completo. '
    'Usar para todas as análises que pedem dados do último ano. '
    'Não requer REFRESH — acompanha automaticamente a materialized view fonte.';
