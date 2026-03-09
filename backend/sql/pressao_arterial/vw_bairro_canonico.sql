-- =====================================================================
-- FUNCTION: dashboard.normaliza_bairro
-- Remove acentos, espaços duplos e converte para minúsculas
-- =====================================================================
CREATE OR REPLACE FUNCTION dashboard.normaliza_bairro(nome TEXT) RETURNS TEXT AS $$
BEGIN
    IF nome IS NULL THEN RETURN NULL; END IF;
    RETURN lower(trim(regexp_replace(
        translate(nome, 'ÁÉÍÓÚÀÈÌÒÙÂÊÎÔÛÄËÏÖÜÃÕÑáéíóúàèìòùâêîôûäëïöüãõñÇç', 'AEIOUAEIOUAEIOUAEIOUAONaeiouaeiouaeiouaeiouaoncC'),
        '\s+', ' ', 'g'
    )));
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- =====================================================================
-- VIEW: RESOLUÇÃO DE BAIRRO CANÔNICO E GEOLOCALIZAÇÃO
-- Schema: dashboard.vw_bairro_canonico
--
-- Problema: mv_pa_cadastros tem 2300+ variações de nomes de bairros
-- (erros de digitação, abreviações, logradouros no lugar de bairros).
--
-- Solução: VIEW regular que junta mv_pa_cadastros com a tabela de
-- mapeamento gerada pelo pipeline de sincronização offline (GeoJSON + rapidfuzz).
--
-- Campo-chave: bairro_canonico
--   → nome padronizado obtido via GeoJSON da prefeitura (Bairros ou Bairro Pai de um Loteamento)
--   → fallback: usa no_bairro_filtro original se for "órfão"
--
-- Todos os endpoints de analytics usam esta view.
-- Pré-requisito: executar scripts/sincronizar_base_geografica.py
-- =====================================================================

CREATE OR REPLACE VIEW dashboard.vw_bairro_canonico AS
SELECT
    cad.*,
    -- Se o mapeamento oficial GeoJSON achou o bairro Pai, usa ele. Se for órfão (ou NULL), mantém o q o ESUS digitou
    COALESCE(bm.no_bairro_canonico, cad.no_bairro_filtro) AS bairro_canonico,
    -- Flag: TRUE se o bairro_canonico bate com um bairro/loteamento oficial de VDC (fonte GeoJSON da prefeitura)
    EXISTS (
        SELECT 1
        FROM dashboard.tb_geocodificacao geo
        WHERE geo.ds_fonte = 'geojson_import'
          AND dashboard.normaliza_bairro(geo.no_bairro)
              = dashboard.normaliza_bairro(COALESCE(bm.no_bairro_canonico, cad.no_bairro_filtro))
    ) AS st_bairro_vdc
FROM dashboard.mv_pa_cadastros cad
LEFT JOIN dashboard.tb_bairros_mapeamento bm
    ON dashboard.normaliza_bairro(cad.no_bairro_filtro) = bm.no_bairro_raw;

COMMENT ON VIEW dashboard.vw_bairro_canonico IS
    'mv_pa_cadastros enriquecida com bairro_canonico normalizado e flag st_bairro_vdc. '
    'st_bairro_vdc=TRUE indica bairro reconhecido pelo GeoJSON da prefeitura de VDC. '
    'Usa tb_bairros_mapeamento (gerada por scripts/normalizar_bairros.py). '
    'Se o mapeamento não existir, usa no_bairro_filtro como fallback.';
