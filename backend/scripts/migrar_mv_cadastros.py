"""
Migração: recria dashboard.mv_pa_cadastros com deduplicação por cidadão.

O que mudou na view:
  1. DISTINCT ON (co_fat_cidadao_pec) — 1 linha por cidadão (ficha mais recente)
  2. grupo_idade: corte alinhado com faixa_etaria (65 anos, não 64)
     'Adultos (18-64)' / 'Idosos (65+)'
  3. Novo UNIQUE INDEX em co_fat_cidadao_pec

Por que DROP + CREATE (não só REFRESH):
  A estrutura da query mudou (DISTINCT ON, ORDER BY alterado).
  REFRESH apenas recarrega os dados com a mesma definição — não aplica
  mudanças no DDL.

Dependências que serão recriadas automaticamente:
  - dashboard.vw_bairro_canonico (VIEW regular — recriada após a MV)

Uso:
    cd plataforma-saude/backend
    python scripts/migrar_mv_cadastros.py

    # Para apenas verificar sem executar (dry-run):
    python scripts/migrar_mv_cadastros.py --dry-run
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import engine, test_connection
from app.core.logging_config import setup_logging

logger = setup_logging("scripts.migrar_mv_cadastros")

SQL_DIR = Path(__file__).parent.parent / "sql" / "pressao_arterial"

PASSOS = [
    {
        "descricao": "Remover view dependente (vw_bairro_canonico)",
        "sql": "DROP VIEW IF EXISTS dashboard.vw_bairro_canonico CASCADE",
    },
    {
        "descricao": "Remover view materializada antiga (mv_pa_cadastros)",
        "sql": "DROP MATERIALIZED VIEW IF EXISTS dashboard.mv_pa_cadastros CASCADE",
    },
    {
        "descricao": "Recriar mv_pa_cadastros com deduplicação",
        "sql_file": "mv_pa_cadastros.sql",
    },
    {
        "descricao": "Recriar vw_bairro_canonico",
        "sql_file": "vw_bairro_canonico.sql",
    },
]


def executar_sql(conn, sql: str, descricao: str, dry_run: bool) -> bool:
    if dry_run:
        print(f"    [DRY-RUN] {descricao}")
        return True
    try:
        conn.execute(text(sql))
        conn.commit()
        print(f"    OK — {descricao}")
        return True
    except Exception as e:
        print(f"    ERRO — {descricao}")
        print(f"           {e}")
        logger.error(f"{descricao}: {e}")
        return False


def contar_linhas(conn, view: str) -> int:
    try:
        result = conn.execute(text(f"SELECT COUNT(*) AS total FROM {view}"))
        row = result.fetchone()
        return row[0] if row else 0
    except Exception:
        return -1


def main() -> None:
    parser = argparse.ArgumentParser(description="Recria mv_pa_cadastros com deduplicação")
    parser.add_argument("--dry-run", action="store_true", help="Mostra o plano sem executar")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  MIGRAÇÃO — mv_pa_cadastros (deduplicação + faixa etária)")
    print("=" * 65)

    if args.dry_run:
        print("\n  MODO DRY-RUN: nenhuma alteração será feita no banco.\n")

    # Verifica conexão
    info = test_connection()
    if info.get("status") != "connected":
        print(f"\n  ERRO de conexão: {info}")
        sys.exit(1)
    print(f"\n  Banco: {info.get('version', 'PostgreSQL')}")

    # Aviso sobre impacto
    if not args.dry_run:
        print("\n  ATENÇÃO: esta operação irá:")
        print("    • DROP dashboard.vw_bairro_canonico")
        print("    • DROP dashboard.mv_pa_cadastros")
        print("    • Recriar ambas com a nova definição")
        print("    • A view ficará offline durante ~1-2 min (tempo de rebuild)")
        resposta = input("\n  Confirmar? [s/N] ").strip().lower()
        if resposta != "s":
            print("  Cancelado.")
            sys.exit(0)

    print()
    erros = 0

    with engine.connect() as conn:
        for passo in PASSOS:
            descricao = passo["descricao"]

            if "sql_file" in passo:
                sql_file = SQL_DIR / passo["sql_file"]
                if not sql_file.exists():
                    print(f"    ERRO — arquivo não encontrado: {sql_file}")
                    erros += 1
                    continue
                sql = sql_file.read_text(encoding="utf-8")
            else:
                sql = passo["sql"]

            ok = executar_sql(conn, sql, descricao, dry_run=args.dry_run)
            if not ok:
                erros += 1

        # Contagem final
        if not args.dry_run and erros == 0:
            print()
            n_cadastros = contar_linhas(conn, "dashboard.mv_pa_cadastros")
            print(f"  Linhas em mv_pa_cadastros (cidadãos únicos): {n_cadastros:,}")
            if n_cadastros > 0:
                n_has = conn.execute(text(
                    "SELECT COUNT(*) FROM dashboard.mv_pa_cadastros WHERE st_hipertensao_arterial = 1"
                )).fetchone()[0]
                prevalencia = round(n_has / n_cadastros * 100, 1)
                print(f"  Hipertensos: {n_has:,} ({prevalencia}%)")

    print()
    if erros == 0:
        print("  Migração concluída com sucesso.")
    else:
        print(f"  Migração concluída com {erros} erro(s). Verifique os logs.")
        sys.exit(1)

    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
