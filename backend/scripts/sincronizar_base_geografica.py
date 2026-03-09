"""
Sincronização 100% Offline da Base Geográfica e Bairros do e-SUS.

Estratégia Híbrida Inteligente:
1. Carrega Loteamentos.geojson e Bairros.geojson na tb_geocodificacao com suas lat/lngs reais (Fonte Principal da Verdade).
2. Tenta fazer o match exato/fuzzy dos bairros crus do e-SUS diretamente contra os loteamentos (filhos) e bairros (pais).
3. Salva os matches na tb_bairros_mapeamento. Como o loteamento sabe quem é o bairro pai, a hierarquia é preservada.
"""

import sys
import json
import argparse
from pathlib import Path
from rapidfuzz import process, fuzz
from sqlalchemy import text
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import engine, execute_query
from app.core.logging_config import setup_logging
from app.modules.pressao_arterial.processors.normalizador_bairros import (
    normalizar_texto, parece_bairro
)

logger = setup_logging("scripts.sincronizar_base_geo")

DDL_MAPEAMENTO = """
CREATE TABLE IF NOT EXISTS dashboard.tb_bairros_mapeamento (
    co_seq_bairro_map   SERIAL PRIMARY KEY,
    no_bairro_raw       TEXT NOT NULL,          -- nome original (normalizado básico)
    no_bairro_canonico  TEXT,                   -- nome do bairro PAI (agrupador final)
    no_loteamento       TEXT,                   -- nome do loteamento correspondente (se houver)
    tp_origem           VARCHAR(20) NOT NULL,   -- 'geojson_exato' | 'geojson_fuzzy' | 'manual'
    vl_similaridade     NUMERIC(5,2),           -- score do fuzzy
    dt_criacao          TIMESTAMP DEFAULT NOW(),
    UNIQUE (no_bairro_raw)
);
CREATE INDEX IF NOT EXISTS idx_bairros_map_raw ON dashboard.tb_bairros_mapeamento (no_bairro_raw);
CREATE INDEX IF NOT EXISTS idx_bairros_map_canonico ON dashboard.tb_bairros_mapeamento (no_bairro_canonico);
"""

def centroid_from_polygon(coordinates: list) -> tuple[float, float]:
    """Calcula um centroid simples a partir de um polígono GeoJSON (primeiro anel)."""
    if not coordinates or not coordinates[0]:
        return 0.0, 0.0
    ring = coordinates[0]
    if isinstance(ring[0], list) and isinstance(ring[0][0], list):
         ring = ring[0]
         
    sum_lon, sum_lat = 0.0, 0.0
    for lon, lat in ring:
        sum_lon += lon
        sum_lat += lat
    return sum_lat / len(ring), sum_lon / len(ring)


def carregar_arquivos_geojson() -> tuple[list[dict], list[dict]]:
    """Lê os dois arquivos GeoJSON da pasta data."""
    # O arquivo estah em scripts/sincronizar... Entao sobe uma vez para 'backend'
    base_dir = Path(__file__).resolve().parent.parent / "data" / "geojson"
    bairros_file = base_dir / "Bairros.geojson"
    loteamentos_file = base_dir / "Loteamentos.geojson"
    
    logger.info(f"Buscando bairros em: {bairros_file}")
    
    bairros, loteamentos = [], []
    
    if bairros_file.exists():
        with open(bairros_file, "r", encoding="utf-8") as f:
            bairros = json.load(f).get("features", [])
            
    if loteamentos_file.exists():
        with open(loteamentos_file, "r", encoding="utf-8") as f:
            loteamentos = json.load(f).get("features", [])
            
    return bairros, loteamentos


def popular_geocodificacao(bairros: list[dict], loteamentos: list[dict]):
    """Popula a tb_geocodificacao com centroids de Loteamentos e Bairros."""
    logger.info("Populando tb_geocodificacao com base em GeoJSON...")
    sql = """
    INSERT INTO dashboard.tb_geocodificacao (no_bairro, nu_latitude, nu_longitude, ds_fonte)
    VALUES (:nome, :lat, :lng, 'geojson_import')
    ON CONFLICT (no_bairro) DO UPDATE 
        SET nu_latitude = EXCLUDED.nu_latitude,
            nu_longitude = EXCLUDED.nu_longitude,
            ds_fonte = 'geojson_import'
    """
    
    count = 0
    with engine.connect() as conn:
        # Bairros Pais
        for feature in bairros:
            prop = feature.get("properties", {})
            geom = feature.get("geometry", {})
            nome_raw = prop.get("nome") or prop.get("name") or prop.get("Name")
            if not nome_raw or not geom.get("coordinates"):
                 continue
                 
            nome_norm = normalizar_texto(nome_raw).title()
            lat, lng = centroid_from_polygon(geom["coordinates"])
            
            conn.execute(text(sql), {"nome": nome_norm, "lat": lat, "lng": lng})
            count += 1
            
        # Loteamentos (Podem ser minúsculos, mas garantem precisão visual máxima)
        for feature in loteamentos:
            prop = feature.get("properties", {})
            geom = feature.get("geometry", {})
            nome_raw = prop.get("nome") or prop.get("name") or prop.get("Name")
            if not nome_raw or not geom.get("coordinates"):
                 continue
                 
            nome_norm = normalizar_texto(nome_raw).title()
            lat, lng = centroid_from_polygon(geom["coordinates"])
            
            conn.execute(text(sql), {"nome": nome_norm, "lat": lat, "lng": lng})
            count += 1
            
        conn.commit()
    logger.info(f" -> {count} regiões (bairros/loteamentos) geocodificadas com sucesso.")


def mapear_esus_para_geojson(threshold: float = 80.0):
    """Mapeia o bairro cru do e-SUS para Loteamentos ou Bairros da Base Geográfica."""
    logger.info("Realizando Fuzzy Match do e-SUS contra a Base Geográfica Oficial...")
    bairros, loteamentos = carregar_arquivos_geojson()
    
    # Montar dicionário estruturado para buscas
    # Chave: Nome Normalizado -> Valor: (Nome Canônico Formato Title, Bairro Pai Title)
    universo_geo = {}
    
    for feature in bairros:
        prop = feature.get("properties", {})
        n = prop.get("nome") or prop.get("name") or prop.get("Name")
        if n:
            n_norm = normalizar_texto(n)
            n_title = n_norm.title()
            universo_geo[n_norm] = (n_title, n_title) # Bairro Pai de um Bairro é ele mesmo
            
    for feature in loteamentos:
        prop = feature.get("properties", {})
        n = prop.get("nome") or prop.get("name") or prop.get("Name")
        pai = prop.get("bairro")
        if n and pai:
            n_norm = normalizar_texto(n)
            n_title = n_norm.title()
            pai_title = normalizar_texto(pai).title()
            
            # Se colidir chave, preserva o bairro (n_norm already in dict because of bairros loop)
            if n_norm not in universo_geo:
                universo_geo[n_norm] = (n_title, pai_title)
                
    chaves_validas = list(universo_geo.keys())
    
    # 2. Buscar Bairros Crus do e-SUS
    crus = execute_query("SELECT DISTINCT no_bairro_filtro FROM dashboard.mv_pa_cadastros WHERE no_bairro_filtro IS NOT NULL", {})
    
    sql_upsert = """
    INSERT INTO dashboard.tb_bairros_mapeamento 
        (no_bairro_raw, no_bairro_canonico, no_loteamento, tp_origem, vl_similaridade)
    VALUES (:raw, :canonico, :loteamento, :origem, :sim)
    ON CONFLICT (no_bairro_raw) DO UPDATE
        SET no_bairro_canonico = EXCLUDED.no_bairro_canonico,
            no_loteamento = EXCLUDED.no_loteamento,
            tp_origem = EXCLUDED.tp_origem,
            vl_similaridade = EXCLUDED.vl_similaridade
    """
    
    stats = {"exato": 0, "fuzzy": 0, "orfao": 0}
    
    with engine.connect() as conn:
        for r in crus:
            raw = r["no_bairro_filtro"]
            raw_norm = normalizar_texto(raw)
            if not raw_norm or not parece_bairro(raw_norm):
                continue
                
            match = None
            sim = None
            origem = None
            
            # 1. Match Exato
            if raw_norm in chaves_validas:
                match = raw_norm
                sim = 100.0
                origem = "geojson_exato"
            else:
                # 2. Match Fuzzy
                resultado = process.extractOne(raw_norm, chaves_validas, scorer=fuzz.WRatio, score_cutoff=threshold)
                if resultado:
                    match = resultado[0]
                    sim = resultado[1]
                    origem = "geojson_fuzzy"
                    
            if match:
                loteamento_nome, pai_nome = universo_geo[match]
                conn.execute(text(sql_upsert), {
                    "raw": raw_norm,
                    "canonico": pai_nome,
                    "loteamento": loteamento_nome if loteamento_nome != pai_nome else None,
                    "origem": origem,
                    "sim": sim
                })
                stats["exato" if origem == "geojson_exato" else "fuzzy"] += 1
            else:
                # Orfão (Não achou em nenhum Loteamento/Bairro oficial, provável Invasão ou Distrito)
                conn.execute(text(sql_upsert), {
                    "raw": raw_norm,
                    "canonico": None,
                    "loteamento": None,
                    "origem": "orfao",
                    "sim": None
                })
                stats["orfao"] += 1
                
        conn.commit()
        
    logger.info(f"Mapeamento concluído: {stats['exato']} Exatos, {stats['fuzzy']} Fuzzy, {stats['orfao']} Órfãos.")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Sincronizador 100% Offline da Base Geográfica e Bairros")
    parser.add_argument("--threshold", type=float, default=80.0, help="Limiar de Similaridade (Fuzzy)")
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("  Sincronização Geográfica Offline — e-SUS PEC")
    print("=" * 60)
    
    with engine.connect() as conn:
        conn.execute(text(DDL_MAPEAMENTO))
        conn.commit()
        
    bairros, loteamentos = carregar_arquivos_geojson()
    popular_geocodificacao(bairros, loteamentos)
    stats = mapear_esus_para_geojson(threshold=args.threshold)
    
    print(f"\nResumo da Operação:")
    print(f" -> Loteamentos e Bairros carregados no Mapa: {len(bairros) + len(loteamentos)}")
    print(f" -> Mapeamentos e-SUS Exatos: {stats['exato']}")
    print(f" -> Mapeamentos e-SUS Fuzzy:  {stats['fuzzy']}")
    print(f" -> Mapeamentos Órfãos:       {stats['orfao']} (Necessitam revisão manual/Nominatim)\n")

if __name__ == '__main__':
    main()
