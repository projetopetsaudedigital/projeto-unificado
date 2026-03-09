"""
Gerenciador das views materializadas de Pressão Arterial.

Responsável por:
  - Criar o schema 'dashboard' se não existir
  - Criar as 3 views materializadas (apenas se não existirem)
  - Atualizar (REFRESH) as views de forma concorrente

Views gerenciadas:
  - dashboard.mv_pa_medicoes          — medições com UBS/equipe
  - dashboard.mv_pa_cadastros         — cadastros com fatores de risco
  - dashboard.mv_pa_medicoes_cidadaos — longitudinal (medições + cidadão)
"""

from pathlib import Path
from typing import NamedTuple

from app.core.database import execute_query, engine
from app.core.logging_config import setup_logging

logger = setup_logging("pa.views.manager")

# Diretório com os scripts SQL
_SQL_DIR = Path(__file__).parent.parent.parent.parent.parent / "sql" / "pressao_arterial"

# Ordem importa: mv_pa_medicoes não depende de nada;
# mv_pa_medicoes_cidadaos depende da estrutura de tb_fat_cidadao_pec.
_VIEWS = [
    "mv_pa_medicoes",
    "mv_pa_cadastros",
    "mv_pa_medicoes_cidadaos",
]


class ViewStatus(NamedTuple):
    name: str
    exists: bool
    row_count: int | None
    last_refresh: str | None


def criar_schema() -> None:
    """Garante que o schema 'dashboard' existe."""
    execute_query("CREATE SCHEMA IF NOT EXISTS dashboard", {})
    logger.info("Schema 'dashboard' verificado.")


def criar_views() -> dict[str, bool]:
    """
    Executa os scripts DDL de cada view (CREATE MATERIALIZED VIEW IF NOT EXISTS).
    Retorna {nome_view: criada_com_sucesso}.
    """
    resultados: dict[str, bool] = {}

    for view_name in _VIEWS:
        sql_file = _SQL_DIR / f"{view_name}.sql"
        if not sql_file.exists():
            logger.warning(f"Script SQL não encontrado: {sql_file}")
            resultados[view_name] = False
            continue

        ddl = sql_file.read_text(encoding="utf-8")
        try:
            # Executa bloco completo (DDL + índices + COMMENT)
            # Cada statement é separado por ';'
            with engine.connect() as conn:
                # psycopg2 via SQLAlchemy — executa bloco inteiro
                from sqlalchemy import text
                conn.execute(text(ddl))
                conn.commit()
            logger.info(f"View criada/verificada: dashboard.{view_name}")
            resultados[view_name] = True
        except Exception as exc:
            logger.error(f"Erro ao criar dashboard.{view_name}: {exc}")
            resultados[view_name] = False

    return resultados


def atualizar_view(view_name: str, concurrently: bool = True) -> bool:
    """
    Executa REFRESH MATERIALIZED VIEW [CONCURRENTLY] para uma view específica.
    CONCURRENTLY requer UNIQUE index na view (já criado nos scripts DDL).
    Retorna True se sucesso.
    """
    schema_view = f"dashboard.{view_name}"
    modo = "CONCURRENTLY" if concurrently else ""
    sql = f"REFRESH MATERIALIZED VIEW {modo} {schema_view}"

    try:
        with engine.connect() as conn:
            from sqlalchemy import text
            # REFRESH não pode rodar dentro de transação explícita no modo CONCURRENTLY
            conn.execute(text("COMMIT"))
            conn.execute(text(sql))
        logger.info(f"View atualizada: {schema_view} (concurrently={concurrently})")
        return True
    except Exception as exc:
        logger.error(f"Erro ao atualizar {schema_view}: {exc}")
        return False


def atualizar_todas(concurrently: bool = True) -> dict[str, bool]:
    """Atualiza todas as views na ordem correta."""
    return {v: atualizar_view(v, concurrently=concurrently) for v in _VIEWS}


def status_views() -> list[ViewStatus]:
    """
    Retorna informações sobre cada view: se existe e quantas linhas tem.
    Útil para o endpoint GET /qualidade/views.
    """
    resultados: list[ViewStatus] = []

    for view_name in _VIEWS:
        schema_view = f"dashboard.{view_name}"

        # Verifica se a view existe em pg_matviews
        check_sql = """
            SELECT schemaname, matviewname
            FROM pg_matviews
            WHERE schemaname = 'dashboard'
              AND matviewname = :view_name
        """
        try:
            rows = execute_query(check_sql, {"view_name": view_name})
            exists = bool(rows)

            if exists:
                count_rows = execute_query(
                    f"SELECT COUNT(*) AS total FROM {schema_view}", {}
                )
                row_count = count_rows[0]["total"] if count_rows else 0
            else:
                row_count = None

            resultados.append(ViewStatus(
                name=schema_view,
                exists=exists,
                row_count=row_count,
                last_refresh=None,  # PostgreSQL não armazena nativo — extensão pg_stat seria necessária
            ))
        except Exception as exc:
            logger.error(f"Erro ao verificar status de {schema_view}: {exc}")
            resultados.append(ViewStatus(name=schema_view, exists=False, row_count=None, last_refresh=None))

    return resultados
