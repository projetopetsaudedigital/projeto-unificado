"""
Exporta dados dos bairros para JSON.

Uso:
    python scripts/exportar_bairros.py
    python scripts/exportar_bairros.py --saida data/meu_arquivo.json
    python scripts/exportar_bairros.py --minimo-cadastros 100

Pré-requisito: scripts/normalizar_bairros.py deve ter sido executado.
Se não foi, usa no_bairro_filtro como fallback (sem normalização).

Saída padrão: data/bairros_analise.json
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import execute_query
from app.core.logging_config import setup_logging

logger = setup_logging("scripts.exportar_bairros")


def exportar(saida: Path, minimo_cadastros: int = 1) -> None:
    sql = f"""
    SELECT
        COALESCE(bm.no_bairro_canonico, cad.no_bairro_filtro) AS bairro,

        COUNT(*)                                                 AS total_cadastros,
        COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)     AS hipertensos,
        ROUND(
            COUNT(*) FILTER (WHERE st_hipertensao_arterial = 1)::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                        AS prevalencia_pct,

        COUNT(*) FILTER (WHERE st_diabetes = 1)                  AS n_diabetes,
        COUNT(*) FILTER (WHERE st_avc = 1)                       AS n_avc,
        COUNT(*) FILTER (WHERE st_infarto = 1)                   AS n_infarto,
        COUNT(*) FILTER (WHERE st_doenca_cardiaca = 1)           AS n_doenca_cardiaca,
        COUNT(*) FILTER (WHERE st_problema_rins = 1)             AS n_problema_rins,
        COUNT(*) FILTER (WHERE st_fumante = 1)                   AS n_fumantes,
        COUNT(*) FILTER (WHERE st_alcool = 1)                    AS n_alcool,

        COUNT(*) FILTER (WHERE grupo_idade = 'Idosos (65+)')     AS n_idosos,
        COUNT(*) FILTER (WHERE grupo_idade = 'Adultos (18-64)') AS n_adultos,
        ROUND(
            COUNT(*) FILTER (WHERE grupo_idade = 'Idosos (65+)')::NUMERIC
            / NULLIF(COUNT(*), 0) * 100, 1
        )                                                        AS pct_idosos,

        cad.co_localidade,
        cad.nu_area

    FROM dashboard.mv_pa_cadastros cad
    LEFT JOIN dashboard.tb_bairros_mapeamento bm
        ON bm.no_bairro_raw = cad.no_bairro_filtro
    WHERE cad.no_bairro_filtro IS NOT NULL
    GROUP BY
        COALESCE(bm.no_bairro_canonico, cad.no_bairro_filtro),
        cad.co_localidade,
        cad.nu_area
    HAVING COUNT(*) >= {minimo_cadastros}
    ORDER BY total_cadastros DESC
    """

    logger.info("Consultando dados dos bairros...")
    rows = execute_query(sql, {})
    logger.info(f"{len(rows)} bairros encontrados.")

    # Converte Decimal para float (serialização JSON)
    resultado = []
    for r in rows:
        item = {}
        for k, v in r.items():
            if hasattr(v, "__float__"):
                item[k] = float(v)
            else:
                item[k] = v
        resultado.append(item)

    saida.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "gerado_em": datetime.now().isoformat(),
        "total_bairros": len(resultado),
        "minimo_cadastros_filtro": minimo_cadastros,
        "bairros": resultado,
    }

    saida.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"Exportado: {saida} ({saida.stat().st_size / 1024:.1f} KB)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Exporta bairros para JSON")
    parser.add_argument("--saida", default="data/bairros_analise.json",
                        help="Caminho do arquivo de saída (padrão: data/bairros_analise.json)")
    parser.add_argument("--minimo-cadastros", type=int, default=1,
                        help="Mínimo de cadastros para incluir o bairro (padrão: 1)")
    args = parser.parse_args()

    saida = Path(args.saida)
    exportar(saida, minimo_cadastros=args.minimo_cadastros)

    print(f"\n  Arquivo gerado: {saida.resolve()}")
    print(f"  Abra no VS Code ou use para análise no frontend.\n")


if __name__ == "__main__":
    main()
