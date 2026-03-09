"""
Script para popular ds_tipo_geo em tb_geocodificacao.

Adiciona a coluna ds_tipo_geo ('bairro' | 'loteamento') e a popula
com base nos nomes importados de cada GeoJSON.
- Bairros.geojson  → 'bairro'
- Loteamentos.geojson → 'loteamento'

Executa como: python scripts/migrar_tipo_geo.py
"""
import sys, json
from pathlib import Path
sys.path.insert(0, r'C:\teste_pet_analise\plataforma-saude\backend')

from app.core.database import engine_admin
from sqlalchemy import text

engine = engine_admin

GEOJSON_DIR = Path(r'C:\teste_pet_analise\plataforma-saude\backend\data\geojson')

def load_names(filename):
    path = GEOJSON_DIR / filename
    geo = json.loads(path.read_text(encoding='utf-8', errors='replace'))
    names = set()
    for f in geo.get('features', []):
        props = f.get('properties', {})
        name = (props.get('name') or props.get('Name') or '').strip().replace('\n', '')
        if name:
            names.add(name)
    return names

print("Carregando GeoJSON...")
bairros_names = load_names('Bairros.geojson')
loteamentos_names = load_names('Loteamentos.geojson')
print(f"  Bairros.geojson: {len(bairros_names)} nomes")
print(f"  Loteamentos.geojson: {len(loteamentos_names)} nomes")

with engine.begin() as conn:
    # 1. Add column if not exists
    conn.execute(text("""
        ALTER TABLE dashboard.tb_geocodificacao
        ADD COLUMN IF NOT EXISTS ds_tipo_geo VARCHAR(20) DEFAULT NULL
    """))
    print("\nColuna ds_tipo_geo adicionada (ou já existia).")

    # 2. Reset all geojson_import rows
    conn.execute(text("""
        UPDATE dashboard.tb_geocodificacao
        SET ds_tipo_geo = NULL
        WHERE ds_fonte = 'geojson_import'
    """))

    # 3. Mark bairros
    bairros_updated = 0
    for name in bairros_names:
        r = conn.execute(text("""
            UPDATE dashboard.tb_geocodificacao
            SET ds_tipo_geo = 'bairro'
            WHERE ds_fonte = 'geojson_import'
              AND dashboard.normaliza_bairro(no_bairro) = dashboard.normaliza_bairro(:name)
        """), {"name": name})
        bairros_updated += r.rowcount
    print(f"Bairros marcados: {bairros_updated}")

    # 4. Mark loteamentos (only if not already marked as bairro)
    lotes_updated = 0
    for name in loteamentos_names:
        r = conn.execute(text("""
            UPDATE dashboard.tb_geocodificacao
            SET ds_tipo_geo = 'loteamento'
            WHERE ds_fonte = 'geojson_import'
              AND ds_tipo_geo IS NULL
              AND dashboard.normaliza_bairro(no_bairro) = dashboard.normaliza_bairro(:name)
        """), {"name": name})
        lotes_updated += r.rowcount
    print(f"Loteamentos marcados: {lotes_updated}")

    # 5. Verify
    check = conn.execute(text("""
        SELECT ds_tipo_geo, COUNT(*) AS n
        FROM dashboard.tb_geocodificacao
        WHERE ds_fonte = 'geojson_import'
        GROUP BY ds_tipo_geo ORDER BY ds_tipo_geo
    """)).fetchall()
    print("\nDistribuição após migração:")
    for row in check:
        print(f"  {row[0]}: {row[1]}")

print("\nMigração concluída.")
