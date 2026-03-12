"""
Script de setup inicial do banco de dados.

Uso:
    cd plataforma-saude/backend
    python scripts/setup.py --all              # Setup completo (novo servidor)
    python scripts/setup.py --check            # Verificar status do banco
    python scripts/setup.py --auth             # Apenas criar tabela de admin
    python scripts/setup.py --normalizacao     # Normalizar bairros (após --all)
    python scripts/setup.py --normalizacao --limite-ceps 50
    python scripts/setup.py --refresh          # Atualizar views materializadas
"""

import argparse
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

# Garante que o módulo 'app' seja encontrado ao rodar o script diretamente
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import test_connection, execute_query
from app.core.logging_config import setup_logging
from app.modules.pressao_arterial.quality.audit_table import criar_tabela_auditoria
from app.modules.pressao_arterial.views.manager import (
    criar_schema,
    criar_views,
    status_views,
)
from app.shared.controle_processamento import criar_tabela_controle

logger = setup_logging("scripts.setup")

# ── Carregamento dos arquivos SQL ────────────────────────────────────────────

_SQL_DIR = Path(__file__).parent.parent / "sql"

_SQL_SETUP_SINGLE      = (_SQL_DIR / "setup_single_db.sql").read_text(encoding="utf-8")
_SQL_SETUP_AUTH        = (_SQL_DIR / "auth" / "setup_auth.sql").read_text(encoding="utf-8")
_SQL_SETUP_GEO         = (_SQL_DIR / "geo" / "setup_geocodificacao.sql").read_text(encoding="utf-8")
_SQL_VW_BAIRRO         = (_SQL_DIR / "pressao_arterial" / "vw_bairro_canonico.sql").read_text(encoding="utf-8")
_SQL_VW_LOTEAMENTO     = (_SQL_DIR / "pressao_arterial" / "vw_loteamento_canonico.sql").read_text(encoding="utf-8")
_SQL_MV_DM_HEMOGLOBINA = (_SQL_DIR / "diabetes" / "mv_dm_hemoglobina.sql").read_text(encoding="utf-8")

_SQL_BAIRROS_MAPEAMENTO = """
CREATE TABLE IF NOT EXISTS dashboard.tb_bairros_mapeamento (
    no_bairro_raw       VARCHAR(255) PRIMARY KEY,
    no_bairro_canonico  VARCHAR(255),
    no_loteamento       VARCHAR(255),
    tp_origem           VARCHAR(50),
    vl_similaridade     NUMERIC(5,2),
    dt_criacao          TIMESTAMP DEFAULT NOW()
);
ALTER TABLE dashboard.tb_bairros_mapeamento ADD COLUMN IF NOT EXISTS no_loteamento VARCHAR(255);
ALTER TABLE dashboard.tb_bairros_mapeamento ADD COLUMN IF NOT EXISTS tp_origem VARCHAR(50);
ALTER TABLE dashboard.tb_bairros_mapeamento ADD COLUMN IF NOT EXISTS vl_similaridade NUMERIC(5,2);
"""


# ── Utilitário DDL com AUTOCOMMIT ────────────────────────────────────────────

def _split_statements(sql_text: str) -> list[str]:
    """
    Divide SQL em statements por ';', ignorando ';' dentro de blocos $$.

    Necessário para PL/pgSQL: funções com $$ BEGIN ... END $$ contêm ';'
    internos que não devem ser tratados como separadores de statement.
    """
    statements, current, in_dollar = [], [], False
    i = 0
    while i < len(sql_text):
        if sql_text[i:i+2] == "$$":
            in_dollar = not in_dollar
            current.append("$$")
            i += 2
            continue
        if sql_text[i] == ";" and not in_dollar:
            lines = [ln for ln in "".join(current).splitlines()
                     if ln.strip() and not ln.strip().startswith("--")]
            cleaned = "\n".join(lines).strip()
            if cleaned:
                statements.append(cleaned)
            current = []
        else:
            current.append(sql_text[i])
        i += 1
    # último statement sem ';' final
    lines = [ln for ln in "".join(current).splitlines()
             if ln.strip() and not ln.strip().startswith("--")]
    cleaned = "\n".join(lines).strip()
    if cleaned:
        statements.append(cleaned)
    return statements


def _executar_sql_ddl(sql_text: str) -> None:
    """
    Executa DDL (CREATE MATERIALIZED VIEW, CREATE INDEX, etc.) com AUTOCOMMIT.

    Por que AUTOCOMMIT:
    - DDL dentro de uma transação SQLAlchemy é revertido se o processo for
      interrompido antes do commit. Para views grandes (20-60 min via FDW)
      isso perde todo o trabalho a cada interrupção.
    - Com AUTOCOMMIT, cada statement commita imediatamente ao concluir.
    """
    from app.core.database import engine as _engine

    statements = _split_statements(sql_text)

    def _heartbeat(stop_event: threading.Event, label: str, start: float) -> None:
        while not stop_event.wait(30):
            elapsed = int(time.time() - start)
            print(f"    ... aguardando '{label}' — {elapsed}s decorridos", flush=True)

    raw_conn = _engine.raw_connection()
    raw_conn.set_isolation_level(0)  # ISOLATION_LEVEL_AUTOCOMMIT
    try:
        with raw_conn.cursor() as cur:
            cur.execute("SET statement_timeout = '3600000'")  # 60 min máximo por statement
            for i, stmt in enumerate(statements, 1):
                first_line = stmt.splitlines()[0][:70]
                ts = datetime.now().strftime("%H:%M:%S")
                print(f"    [{i}/{len(statements)}] {ts} {first_line}...", flush=True)
                stop = threading.Event()
                t = threading.Thread(target=_heartbeat, args=(stop, first_line[:40], time.time()), daemon=True)
                t.start()
                try:
                    cur.execute(stmt)
                finally:
                    stop.set()
                    t.join()
                ts_end = datetime.now().strftime("%H:%M:%S")
                print(f"    [{i}/{len(statements)}] {ts_end} OK", flush=True)
    finally:
        raw_conn.close()


# ── Funções por etapa ────────────────────────────────────────────────────────

def step_check() -> bool:
    """Testa conexão e exibe status atual das views."""
    print("\n[CHECK] Testando conexão com o banco...")
    info = test_connection()
    if info.get("status") != "connected":
        print(f"  ERRO: {info}")
        return False
    print(f"  OK — PEC: {info.get('pec', {}).get('database', '?')} | Admin: {info.get('admin', {}).get('database', '?')}")
    print(f"  Modo: {'FDW (dois bancos)' if settings.DB_MODE == 'fdw' else 'Banco único (pet_saude)'}")

    print("\n  STATUS DAS VIEWS:")
    views = status_views()
    if not views:
        print("  (nenhuma view encontrada)")
    for v in views:
        if v.exists:
            print(f"  {v.name}: {v.row_count:,} linhas")
        else:
            print(f"  {v.name}: NAO EXISTE")
    return True


def step_schema() -> None:
    """Cria schemas (dashboard, auth, pec) e aliases pec.* conforme o modo."""
    mode = settings.DB_MODE
    if mode == "single":
        print("\n[SCHEMA] Configurando banco único (schemas + views pec.*)...")
        _executar_sql_ddl(_SQL_SETUP_SINGLE)
    else:
        print("\n[SCHEMA] Criando schema 'dashboard' (modo FDW)...")
        criar_schema()
    print("  OK")


def step_auth() -> None:
    """Cria auth.tb_usuarios e insere o usuário admin padrão."""
    print("\n[AUTH] Criando tabela de usuários e admin padrão...")
    _executar_sql_ddl(_SQL_SETUP_AUTH)
    print("  OK — auth.tb_usuarios criada | admin@plataforma.saude inserido (se não existia)")


def step_tabelas() -> None:
    """Cria tabelas de suporte: auditoria, controle de processamento, bairros_mapeamento."""
    print("\n[TABELAS] Criando tabelas de suporte...")
    ok = criar_tabela_auditoria()
    print(f"  Auditoria de outliers: {'OK' if ok else 'ERRO'}")
    criar_tabela_controle()
    print("  Controle de processamento: OK")
    execute_query(_SQL_BAIRROS_MAPEAMENTO)
    print("  Mapeamento de bairros: OK")
    _executar_sql_ddl(_SQL_SETUP_GEO)
    print("  Geocodificação de bairros: OK")


def step_views_pa() -> None:
    """Cria as 3 views materializadas de Pressão Arterial."""
    print("\n[VIEWS-PA] Criando views materializadas de Pressão Arterial...")
    if settings.DB_MODE == "fdw":
        print("  (pode levar vários minutos via FDW — aguarde)")
    resultados = criar_views()
    for nome, sucesso in resultados.items():
        print(f"  [{'OK' if sucesso else 'ERRO'}] dashboard.{nome}")


def step_views_diabetes() -> None:
    """Cria mv_dm_hemoglobina."""
    print("\n[VIEWS-DIABETES] Criando view materializada de Diabetes...")
    if settings.DB_MODE == "fdw":
        print("  (pode levar vários minutos via FDW — aguarde)")
    try:
        _executar_sql_ddl(_SQL_MV_DM_HEMOGLOBINA)
        print("  [OK] dashboard.mv_dm_hemoglobina")
    except Exception as e:
        print(f"  [ERRO] mv_dm_hemoglobina: {e}")


def step_views_regulares() -> None:
    """Cria vw_bairro_canonico e vw_loteamento_canonico."""
    print("\n[VIEWS-REGULARES] Criando views regulares de endereço...")
    try:
        _executar_sql_ddl(_SQL_VW_BAIRRO)
        print("  [OK] dashboard.vw_bairro_canonico")
    except Exception as e:
        print(f"  [ERRO] vw_bairro_canonico: {e}")
    try:
        _executar_sql_ddl(_SQL_VW_LOTEAMENTO)
        print("  [OK] dashboard.vw_loteamento_canonico")
    except Exception as e:
        print(f"  [ERRO] vw_loteamento_canonico: {e}")


def step_normalizacao(limite_ceps: int | None, threshold: float, delay: float) -> None:
    """Executa normalização de bairros via ViaCEP + fuzzy matching."""
    print("\n[NORMALIZACAO] Iniciando normalização de endereços...")
    print(f"  threshold={threshold}% | delay={delay}s", end="")
    if limite_ceps:
        print(f" | limite-ceps={limite_ceps}")
    else:
        print()

    from app.modules.pressao_arterial.processors.normalizador_bairros import (
        criar_tabela_mapeamento,
        executar_normalizacao,
    )
    criar_tabela_mapeamento()
    executar_normalizacao(
        limite_ceps=limite_ceps,
        threshold_fuzzy=threshold,
        delay_viacep=delay,
    )
    print("  [OK] Normalização concluída")


def step_sincronizacao_geo() -> None:
    """Carrega dados oficiais de bairros via GeoJSON local e realiza mapeamento Fuzzy offline."""
    print("\n[MAPAS] Sincronizando Base Geográfica Oficial...")
    try:
        from scripts.sincronizar_base_geografica import (
            carregar_arquivos_geojson,
            popular_geocodificacao,
            mapear_esus_para_geojson
        )
        bairros, loteamentos = carregar_arquivos_geojson()
        popular_geocodificacao(bairros, loteamentos)
        stats = mapear_esus_para_geojson(threshold=80.0)
        print(f"  [OK] Bairros carregados: {len(bairros) + len(loteamentos)}")
        print(f"  [OK] Match e-SUS: {stats['exato']} Exatos, {stats['fuzzy']} Fuzzy, {stats['orfao']} Órfãos.")
    except Exception as e:
        print(f"  [ERRO] Sincronização falhou: {e}")


def step_refresh() -> None:
    """Faz REFRESH CONCURRENTLY em todas as views materializadas existentes."""
    from app.modules.pressao_arterial.views.manager import atualizar_view

    views_materializadas = [
        "mv_pa_medicoes",
        "mv_pa_cadastros",
        "mv_pa_medicoes_cidadaos",
        "mv_dm_hemoglobina",
    ]

    print("\n[REFRESH] Atualizando views materializadas...")
    for view in views_materializadas:
        try:
            rows = execute_query(
                "SELECT matviewname FROM pg_matviews WHERE schemaname='dashboard' AND matviewname=:v",
                {"v": view},
            )
            if not rows:
                print(f"  [SKIP] dashboard.{view} (não existe)")
                continue
            print(f"  Atualizando dashboard.{view}...")
            ok = atualizar_view(view, concurrently=True)
            print(f"  [{'OK' if ok else 'ERRO'}] dashboard.{view}")
        except Exception as e:
            print(f"  [ERRO] {view}: {e}")


# ── Ponto de entrada ─────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scripts/setup.py",
        description="Setup da Plataforma de Saúde Pública",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python scripts/setup.py --all                          Setup completo (novo servidor)
  python scripts/setup.py --check                        Verificar status do banco
  python scripts/setup.py --auth                         Apenas criar tabela de admin
  python scripts/setup.py --schema --tabelas             Schema + tabelas de suporte
  python scripts/setup.py --views-pa --views-diabetes    Apenas views de PA e Diabetes
  python scripts/setup.py --normalizacao                 Normalizar bairros (após --all)
  python scripts/setup.py --normalizacao --limite-ceps 50 --threshold 85
  python scripts/setup.py --refresh                      Atualizar views materializadas
        """,
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help="Executa tudo na ordem correta: schema → auth → tabelas → views (PA, diabetes, regulares)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Testa conexão com o banco e exibe o status atual das views",
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Cria schemas (dashboard, auth, pec) e aliases pec.* (modo single) ou configura FDW",
    )
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Cria auth.tb_usuarios e insere o usuário admin padrão (admin@plataforma.saude / admin123)",
    )
    parser.add_argument(
        "--tabelas",
        action="store_true",
        help="Cria tabelas de suporte: auditoria de outliers, controle de processamento, bairros_mapeamento",
    )
    parser.add_argument(
        "--views-pa",
        action="store_true",
        dest="views_pa",
        help="Cria as 3 views materializadas de Pressão Arterial",
    )
    parser.add_argument(
        "--views-diabetes",
        action="store_true",
        dest="views_diabetes",
        help="Cria mv_dm_hemoglobina (Diabetes)",
    )
    parser.add_argument(
        "--views-regulares",
        action="store_true",
        dest="views_regulares",
        help="Cria vw_bairro_canonico e vw_loteamento_canonico",
    )
    parser.add_argument(
        "--normalizacao",
        action="store_true",
        help="Executa normalização de bairros via ViaCEP + fuzzy matching (executar após --all)",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Executa REFRESH CONCURRENTLY em todas as views materializadas existentes",
    )

    # Flags auxiliares para --normalizacao
    parser.add_argument(
        "--limite-ceps",
        type=int,
        default=None,
        metavar="N",
        dest="limite_ceps",
        help="Limita a N CEPs na normalização (útil para testes rápidos)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=80.0,
        metavar="FLOAT",
        help="Threshold de similaridade fuzzy para normalização (padrão: 80.0)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        metavar="FLOAT",
        help="Delay em segundos entre chamadas à API ViaCEP (padrão: 0.3)",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # Sem nenhuma flag → exibir help
    nenhuma_flag = not any([
        args.all, args.check, args.schema, args.auth, args.tabelas,
        args.views_pa, args.views_diabetes, args.views_regulares, 
        args.normalizacao, args.refresh,
    ])
    if nenhuma_flag:
        parser.print_help()
        sys.exit(0)

    mode_label = "FDW (dois bancos)" if settings.DB_MODE == "fdw" else "Banco único (pet_saude)"
    print("\n" + "=" * 60)
    print("  SETUP — Plataforma de Saúde Pública")
    print(f"  Modo: {mode_label}")
    print("=" * 60)

    # Teste de conexão sempre que qualquer flag for usada
    info = test_connection()
    if info.get("status") != "connected":
        print(f"\n  ERRO de conexão: {info}")
        sys.exit(1)
    print(f"\n  Conexão OK — PEC: {info.get('pec', {}).get('database', '?')} | Admin: {info.get('admin', {}).get('database', '?')}")

    # Execução das etapas
    if args.all:
        step_schema()
        step_auth()
        step_tabelas()
        step_views_pa()
        step_views_diabetes()
        step_views_regulares()
        step_sincronizacao_geo()
    else:
        if args.schema:
            step_schema()
        if args.auth:
            step_auth()
        if args.tabelas:
            step_tabelas()
        if args.views_pa:
            step_views_pa()
        if args.views_diabetes:
            step_views_diabetes()
        if args.views_regulares:
            step_views_regulares()
        if args.normalizacao:
            step_normalizacao(
                limite_ceps=args.limite_ceps,
                threshold=args.threshold,
                delay=args.delay,
            )
        if args.refresh:
            step_refresh()

    # --check pode ser combinado com outras flags ou usado sozinho
    if args.check or args.all:
        print("\n" + "-" * 60)
        print("  STATUS FINAL DAS VIEWS:")
        for v in status_views():
            if v.exists:
                print(f"  {v.name}: {v.row_count:,} linhas")
            else:
                print(f"  {v.name}: NAO EXISTE")

    if args.all:
        print("\n  Setup completo concluído.")
        print("  Próximo passo (opcional): python scripts/setup.py --normalizacao")
        print("  Para iniciar a API: uvicorn main:app --reload")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
