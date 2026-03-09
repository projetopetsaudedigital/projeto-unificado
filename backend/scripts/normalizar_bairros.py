"""
Script de normalização de nomes de bairros.

Uso:
    # Teste rápido com apenas 50 CEPs
    python scripts/normalizar_bairros.py --limite-ceps 50

    # Execução completa (pode levar 20-40 min para ~3600 CEPs com delay 0.3s)
    python scripts/normalizar_bairros.py

    # Ver estatísticas dos mapeamentos já criados
    python scripts/normalizar_bairros.py --status

    # Ajustar threshold de similaridade (padrão: 80%)
    python scripts/normalizar_bairros.py --threshold 85
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import execute_query
from app.core.logging_config import setup_logging
from app.modules.pressao_arterial.processors.normalizador_bairros import (
    criar_tabela_mapeamento,
    executar_normalizacao,
)

logger = setup_logging("scripts.normalizar_bairros")


def mostrar_status() -> None:
    """Exibe estatísticas dos mapeamentos já criados."""
    try:
        stats = execute_query("""
            SELECT
                tp_origem,
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE no_bairro_canonico IS NOT NULL) AS com_canonico,
                COUNT(*) FILTER (WHERE no_bairro_canonico IS NULL) AS sem_canonico,
                ROUND(AVG(vl_similaridade), 1) AS media_similaridade
            FROM dashboard.tb_bairros_mapeamento
            GROUP BY tp_origem
            ORDER BY tp_origem
        """, {})

        if not stats:
            print("  Nenhum mapeamento encontrado. Execute o script sem --status primeiro.")
            return

        print(f"\n{'Origem':<12} {'Total':>8} {'Com canônico':>14} {'Sem canônico':>14} {'Sim. média':>12}")
        print("-" * 65)
        total_geral = 0
        for r in stats:
            sim = f"{r['media_similaridade']:.1f}%" if r['media_similaridade'] else "  —"
            print(f"{r['tp_origem']:<12} {r['total']:>8,} {r['com_canonico']:>14,} {r['sem_canonico']:>14,} {sim:>12}")
            total_geral += r['total']
        print("-" * 65)
        print(f"{'TOTAL':<12} {total_geral:>8,}")

        # Top 20 bairros canônicos
        top = execute_query("""
            SELECT no_bairro_canonico, COUNT(*) AS variantes
            FROM dashboard.tb_bairros_mapeamento
            WHERE no_bairro_canonico IS NOT NULL
            GROUP BY no_bairro_canonico
            ORDER BY variantes DESC
            LIMIT 20
        """, {})

        print(f"\nTop 20 bairros canônicos (por número de variantes mapeadas):")
        for r in top:
            print(f"  {r['variantes']:>3} variantes → {r['no_bairro_canonico']}")

        # Sem match (precisam revisão manual)
        sem_match = execute_query("""
            SELECT no_bairro_raw, tp_origem
            FROM dashboard.tb_bairros_mapeamento
            WHERE no_bairro_canonico IS NULL
            ORDER BY no_bairro_raw
            LIMIT 20
        """, {})
        if sem_match:
            print(f"\nSem correspondência (primeiros 20 — precisam revisão manual):")
            for r in sem_match:
                print(f"  [{r['tp_origem']}] {r['no_bairro_raw']}")

    except Exception as e:
        print(f"  Erro ao consultar status: {e}")
        print("  Execute o script sem --status para criar a tabela primeiro.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalização de bairros do e-SUS PEC")
    parser.add_argument("--status", action="store_true", help="Exibe estatísticas dos mapeamentos existentes")
    parser.add_argument("--limite-ceps", type=int, default=None, metavar="N",
                        help="Limitar a N CEPs (útil para testes)")
    parser.add_argument("--threshold", type=float, default=80.0,
                        help="Threshold mínimo de similaridade para fuzzy (padrão: 80.0)")
    parser.add_argument("--delay", type=float, default=0.3,
                        help="Segundos entre chamadas à API ViaCEP (padrão: 0.3)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  Normalização de Bairros — e-SUS PEC")
    print("=" * 60)

    if args.status:
        mostrar_status()
        return

    criar_tabela_mapeamento()

    if args.limite_ceps:
        print(f"\n  Modo TESTE — processando apenas {args.limite_ceps} CEPs")
    else:
        # Estima o tempo
        n_ceps = execute_query("""
            SELECT COUNT(DISTINCT ds_cep) AS n
            FROM dashboard.mv_pa_cadastros
            WHERE ds_cep IS NOT NULL AND LENGTH(TRIM(ds_cep)) >= 8
        """, {})[0]["n"]
        tempo_min = round(n_ceps * args.delay / 60, 1)
        print(f"\n  {n_ceps:,} CEPs distintos × {args.delay}s delay ≈ {tempo_min} minutos")
        print(f"  Threshold fuzzy: {args.threshold}%")
        print("\n  Pressione Ctrl+C para cancelar. O progresso é salvo incrementalmente.")

    print()
    stats = executar_normalizacao(
        delay_viacep=args.delay,
        threshold_fuzzy=args.threshold,
        limite_ceps=args.limite_ceps,
    )

    print(f"\n  Resultado:")
    print(f"    ViaCEP com bairro:    {stats['viacep_ok']:,}")
    print(f"    ViaCEP sem bairro:    {stats['viacep_sem_bairro']:,}")
    print(f"    Fuzzy com match:      {stats['fuzzy_ok']:,}")
    print(f"    Fuzzy sem match:      {stats['fuzzy_sem_match']:,}")
    print(f"    Já existiam:          {stats['ja_existia']:,}")
    print(f"\n  Execute com --status para ver o resumo completo.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
