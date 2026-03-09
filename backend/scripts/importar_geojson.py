"""
Importação de GeoJSON para a tabela de geocodificação.

Lê os arquivos Bairros.geojson e Loteamentos.geojson,
calcula o centroide de cada polígono e insere na tabela
dashboard.tb_geocodificacao.

Uso:
    python scripts/importar_geojson.py
    python scripts/importar_geojson.py --arquivo path/to/Bairros.geojson
"""

import sys
import json
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import execute_query
from app.core.logging_config import setup_logging

logger = setup_logging("scripts.importar_geojson")

# Caminhos padrão dos GeoJSON
_BASE_GEOJSON = Path(__file__).parent.parent.parent / "projeto" / "pressao-arterial" / "data" / "geojson"
_BAIRROS_GEOJSON = _BASE_GEOJSON / "Bairros.geojson"


def calcular_centroide(coords_polygon):
    """
    Calcula o centroide de um polígono simples (média das coordenadas).
    coords_polygon: lista de [lng, lat] pontos (anel externo).
    """
    ring = coords_polygon[0]  # Anel externo
    n = len(ring)
    if n == 0:
        return None, None

    avg_lng = sum(p[0] for p in ring) / n
    avg_lat = sum(p[1] for p in ring) / n
    return round(avg_lat, 7), round(avg_lng, 7)


def normalizar_nome_bairro(nome):
    """Normaliza o nome do bairro para comparação."""
    if not nome:
        return nome
    import unicodedata
    # Remove acentos
    nome = unicodedata.normalize("NFD", nome)
    nome = "".join(c for c in nome if unicodedata.category(c) != "Mn")
    # Lowercase, strip
    nome = nome.strip().lower()
    # Remove \n que aparece em alguns nomes do GeoJSON
    nome = nome.replace("\n", "").strip()
    return nome


def importar_bairros_geojson(caminho_geojson=None):
    """
    Importa bairros do GeoJSON, calcula centroides e insere no banco.
    Retorna dict com estatísticas.
    """
    caminho = Path(caminho_geojson) if caminho_geojson else _BAIRROS_GEOJSON

    if not caminho.exists():
        logger.error(f"Arquivo não encontrado: {caminho}")
        return {"erro": f"Arquivo não encontrado: {caminho}"}

    with open(caminho, "r", encoding="utf-8", errors="replace") as f:
        geojson = json.load(f)

    features = geojson.get("features", [])
    logger.info(f"Lendo {len(features)} features de {caminho.name}")

    # Criar tabela se não existe
    execute_query("""
        CREATE TABLE IF NOT EXISTS dashboard.tb_geocodificacao (
            no_bairro       VARCHAR(255) PRIMARY KEY,
            nu_latitude     NUMERIC(10,7) NOT NULL,
            nu_longitude    NUMERIC(10,7) NOT NULL,
            ds_fonte        VARCHAR(50) NOT NULL DEFAULT 'manual',
            ds_tipo_geo     VARCHAR(20) DEFAULT NULL,
            geojson_polygon JSONB,
            dt_criacao      TIMESTAMP DEFAULT NOW(),
            dt_atualizacao  TIMESTAMP DEFAULT NOW()
        )
    """)

    inseridos = 0
    atualizados = 0
    erros = 0

    for feat in features:
        props = feat.get("properties", {})
        geometry = feat.get("geometry", {})
        nome = props.get("name") or props.get("Name") or ""
        nome = nome.strip().replace("\n", "")

        if not nome or geometry.get("type") != "Polygon":
            erros += 1
            continue

        lat, lng = calcular_centroide(geometry.get("coordinates", []))
        if lat is None:
            erros += 1
            continue

        polygon_json = json.dumps(geometry)

        try:
            execute_query("""
                INSERT INTO dashboard.tb_geocodificacao
                    (no_bairro, nu_latitude, nu_longitude, ds_fonte, geojson_polygon)
                VALUES
                    (:nome, :lat, :lng, 'geojson_import', CAST(:polygon AS JSONB))
                ON CONFLICT (no_bairro) DO UPDATE SET
                    nu_latitude = EXCLUDED.nu_latitude,
                    nu_longitude = EXCLUDED.nu_longitude,
                    ds_fonte = 'geojson_import',
                    geojson_polygon = EXCLUDED.geojson_polygon,
                    dt_atualizacao = NOW()
            """, {"nome": nome, "lat": lat, "lng": lng, "polygon": polygon_json})

            inseridos += 1
            logger.info(f"  {nome}: ({lat}, {lng})")
        except Exception as e:
            logger.error(f"  Erro ao inserir {nome}: {e}")
            erros += 1

    stats = {
        "arquivo": caminho.name,
        "total_features": len(features),
        "inseridos": inseridos,
        "erros": erros,
    }
    logger.info(f"Importação concluída: {stats}")
    return stats


def mapear_bairros_esus_para_geojson():
    """
    Usa fuzzy matching para mapear nomes de bairros do e-SUS
    aos nomes dos bairros do GeoJSON (já importados).
    Atualiza tb_geocodificacao com coordenadas para bairros do e-SUS.
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz não instalado — pulando mapeamento fuzzy")
        return {"mapeados": 0, "sem_match": 0}

    # Bairros do GeoJSON já no banco
    geo_rows = execute_query(
        "SELECT no_bairro, nu_latitude, nu_longitude FROM dashboard.tb_geocodificacao WHERE ds_fonte = 'geojson_import'",
        {},
    )
    if not geo_rows:
        return {"mapeados": 0, "sem_match": 0, "msg": "Nenhum bairro GeoJSON importado"}

    geo_nomes = {r["no_bairro"]: (r["nu_latitude"], r["nu_longitude"]) for r in geo_rows}
    geo_normalizado = {normalizar_nome_bairro(n): n for n in geo_nomes}

    # Bairros distintos do e-SUS (via vw_bairro_canonico)
    esus_rows = execute_query("""
        SELECT DISTINCT bairro_canonico AS bairro
        FROM dashboard.vw_bairro_canonico
        WHERE bairro_canonico IS NOT NULL
    """, {})

    if not esus_rows:
        return {"mapeados": 0, "sem_match": 0, "msg": "Nenhum bairro no e-SUS"}

    mapeados = 0
    sem_match = 0
    threshold = 80

    for row in esus_rows:
        bairro_esus = row["bairro"]
        bairro_norm = normalizar_nome_bairro(bairro_esus)

        # Já tem coordenada?
        existe = execute_query(
            "SELECT 1 FROM dashboard.tb_geocodificacao WHERE no_bairro = :b", {"b": bairro_esus}
        )
        if existe:
            continue

        # Match exato (normalizado)
        if bairro_norm in geo_normalizado:
            geo_nome = geo_normalizado[bairro_norm]
            lat, lng = geo_nomes[geo_nome]
            execute_query("""
                INSERT INTO dashboard.tb_geocodificacao (no_bairro, nu_latitude, nu_longitude, ds_fonte)
                VALUES (:nome, :lat, :lng, 'geojson_fuzzy')
                ON CONFLICT (no_bairro) DO NOTHING
            """, {"nome": bairro_esus, "lat": lat, "lng": lng})
            mapeados += 1
            logger.info(f"  Match exato: '{bairro_esus}' → '{geo_nome}'")
            continue

        # Fuzzy match
        melhor_score = 0
        melhor_nome = None
        for geo_norm, geo_orig in geo_normalizado.items():
            score = fuzz.ratio(bairro_norm, geo_norm)
            if score > melhor_score:
                melhor_score = score
                melhor_nome = geo_orig

        if melhor_score >= threshold and melhor_nome:
            lat, lng = geo_nomes[melhor_nome]
            execute_query("""
                INSERT INTO dashboard.tb_geocodificacao (no_bairro, nu_latitude, nu_longitude, ds_fonte)
                VALUES (:nome, :lat, :lng, 'geojson_fuzzy')
                ON CONFLICT (no_bairro) DO NOTHING
            """, {"nome": bairro_esus, "lat": lat, "lng": lng})
            mapeados += 1
            logger.info(f"  Fuzzy ({melhor_score}%): '{bairro_esus}' → '{melhor_nome}'")
        else:
            sem_match += 1
            logger.debug(f"  Sem match: '{bairro_esus}' (melhor: '{melhor_nome}' {melhor_score}%)")

    return {"mapeados": mapeados, "sem_match": sem_match}


def main():
    parser = argparse.ArgumentParser(description="Importar GeoJSON de bairros")
    parser.add_argument("--arquivo", help="Caminho para o GeoJSON (padrão: Bairros.geojson)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Importacao de GeoJSON -> Geocodificacao")
    print("=" * 60 + "\n")

    # 1. Importar polígonos
    stats = importar_bairros_geojson(args.arquivo)
    print(f"  GeoJSON: {stats.get('inseridos', 0)} bairros importados, {stats.get('erros', 0)} erros")

    # 2. Mapear bairros do e-SUS
    print("\n  Mapeando bairros do e-SUS para GeoJSON...")
    fuzzy = mapear_bairros_esus_para_geojson()
    print(f"  Fuzzy: {fuzzy.get('mapeados', 0)} mapeados, {fuzzy.get('sem_match', 0)} sem match")

    # 3. Resumo
    total = execute_query("SELECT COUNT(*) AS n FROM dashboard.tb_geocodificacao", {})
    print(f"\n  Total de bairros geocodificados: {total[0]['n']}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
