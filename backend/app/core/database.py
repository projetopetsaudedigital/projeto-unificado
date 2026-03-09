"""
Gerenciamento de conexão com PostgreSQL via SQLAlchemy.

Dois engines:
  - engine_pec   → banco pet_saude (e-SUS PEC, somente leitura)
  - engine_admin → banco admin-esus (views, controle, auth)
  - engine       → alias para engine_admin (retrocompatibilidade)
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings
from app.core.logging_config import setup_logging

logger = setup_logging("core.database")

# ── Engines — configuração condicional por DB_MODE ────────────────────────

if settings.DB_MODE == "single":
    # Modo banco único: tudo em pet_saude (sem FDW)
    _single_engine = create_engine(
        settings.PEC_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"options": "-csearch_path=dashboard,pec,public"},
    )
    engine_pec   = _single_engine
    engine_admin = _single_engine
else:
    # Modo FDW: dois bancos separados
    engine_pec = create_engine(
        settings.PEC_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=5,
    )
    engine_admin = create_engine(
        settings.ADMIN_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"options": "-csearch_path=dashboard,pec,auth,public"},
    )

# ── Retrocompatibilidade ──────────────────────────────────────────────────

engine = engine_admin  # Todos os imports existentes de 'engine' funcionam

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_admin)


def get_db() -> Generator[Session, None, None]:
    """Dependência FastAPI — fornece uma sessão de banco por requisição."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection() -> dict:
    """Testa a conexão com o(s) banco(s) e retorna informações."""
    result = {}

    # Testa PEC
    try:
        with engine_pec.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
            result["pec"] = {
                "status": "connected",
                "database": settings.DB_NAME,
                "host": settings.DB_HOST,
                "postgres_version": version,
            }
    except Exception as e:
        logger.error(f"Falha na conexão com o PEC: {e}")
        result["pec"] = {"status": "error", "message": str(e)}

    if settings.DB_MODE == "single":
        # Mesmo banco — replica a entrada pec para admin
        result["admin"] = result["pec"].copy()
    else:
        # Testa Admin separado
        try:
            with engine_admin.connect() as conn:
                version = conn.execute(text("SELECT version()")).scalar()
                result["admin"] = {
                    "status": "connected",
                    "database": settings.ADMIN_DB_NAME,
                    "host": settings.ADMIN_DB_HOST,
                    "postgres_version": version,
                }
        except Exception as e:
            logger.error(f"Falha na conexão com o Admin: {e}")
            result["admin"] = {"status": "error", "message": str(e)}

    # Status geral
    result["status"] = (
        "connected" if result.get("pec", {}).get("status") == "connected"
        and result.get("admin", {}).get("status") == "connected"
        else "error"
    )
    return result


def execute_query(sql: str, params: dict = None) -> list[dict]:
    """Executa uma query SQL no banco admin-esus e retorna lista de dicionários.
    Para DDL/DML que não retornam linhas, retorna lista vazia."""
    try:
        with engine_admin.connect() as conn:
            result = conn.execute(text(sql), params or {})
            conn.commit()
            if not result.returns_rows:
                return []
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Erro ao executar query: {e}")
        raise


def execute_query_pec(sql: str, params: dict = None) -> list[dict]:
    """Executa uma query SQL no banco PEC (pet_saude, somente leitura).
    Para queries que precisam ler tabelas diretamente do PEC."""
    try:
        with engine_pec.connect() as conn:
            result = conn.execute(text(sql), params or {})
            if not result.returns_rows:
                return []
            columns = result.keys()
            return [dict(zip(columns, row)) for row in result.fetchall()]
    except Exception as e:
        logger.error(f"Erro ao executar query PEC: {e}")
        raise
