-- ============================================================
-- Tabela de geocodificação de bairros
-- Banco: admin-esus | Schema: dashboard
-- ============================================================

CREATE TABLE IF NOT EXISTS dashboard.tb_geocodificacao (
    no_bairro           VARCHAR(255) PRIMARY KEY,
    nu_latitude         NUMERIC(10,7) NOT NULL,
    nu_longitude        NUMERIC(10,7) NOT NULL,
    ds_fonte            VARCHAR(50) NOT NULL DEFAULT 'manual',
    ds_tipo_geo         VARCHAR(20) DEFAULT NULL,
    -- Fontes: 'geojson_import', 'nominatim', 'manual'
    geojson_polygon     JSONB,
    dt_criacao          TIMESTAMP DEFAULT NOW(),
    dt_atualizacao      TIMESTAMP DEFAULT NOW()
);

ALTER TABLE dashboard.tb_geocodificacao ADD COLUMN IF NOT EXISTS ds_tipo_geo VARCHAR(20) DEFAULT NULL;

CREATE INDEX IF NOT EXISTS idx_geo_fonte ON dashboard.tb_geocodificacao(ds_fonte);

COMMENT ON TABLE dashboard.tb_geocodificacao IS
    'Coordenadas geográficas (lat/lng) dos bairros, importadas de GeoJSON ou geocodificadas via Nominatim.';
