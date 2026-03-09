"""
Gerenciamento da tabela de controle de processamento.

Registra início, fim, status e métricas de cada processamento
(normalização, treinamento de ML, refresh de views).
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Any

from sqlalchemy import text

from app.core.database import engine, execute_query
from app.core.logging_config import setup_logging

logger = setup_logging("shared.controle")


_DDL = """
CREATE TABLE IF NOT EXISTS dashboard.tb_controle_processamento (
    co_seq               SERIAL PRIMARY KEY,
    tp_processamento     VARCHAR(50)  NOT NULL,
    dt_inicio            TIMESTAMP    NOT NULL DEFAULT NOW(),
    dt_fim               TIMESTAMP,
    st_status            VARCHAR(20)  NOT NULL DEFAULT 'em_andamento',
    ds_modelo            VARCHAR(100),
    ds_metricas          JSONB,
    qt_registros         INTEGER,
    ds_observacao        TEXT,
    ds_erro              TEXT
);
"""


def criar_tabela_controle() -> None:
    """Cria a tabela tb_controle_processamento se não existir."""
    with engine.connect() as conn:
        conn.execute(text(_DDL))
        conn.commit()
    logger.info("Tabela tb_controle_processamento pronta.")


def registrar_inicio(
    tp_processamento: str,
    ds_modelo: Optional[str] = None,
    ds_observacao: Optional[str] = None,
) -> int:
    """
    Registra o início de um processamento.
    Retorna o co_seq (ID) do registro criado.
    """
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                INSERT INTO dashboard.tb_controle_processamento
                    (tp_processamento, dt_inicio, st_status, ds_modelo, ds_observacao)
                VALUES (:tp, NOW(), 'em_andamento', :modelo, :obs)
                RETURNING co_seq
            """),
            {"tp": tp_processamento, "modelo": ds_modelo, "obs": ds_observacao},
        )
        co_seq = result.scalar()
        conn.commit()
    logger.info(f"Processamento '{tp_processamento}' iniciado (ID={co_seq})")
    return co_seq


def registrar_fim(
    co_seq: int,
    st_status: str = "concluido",
    ds_metricas: Optional[dict] = None,
    qt_registros: Optional[int] = None,
    ds_erro: Optional[str] = None,
) -> None:
    """Registra o fim (sucesso ou erro) de um processamento."""
    metricas_json = json.dumps(ds_metricas, ensure_ascii=False) if ds_metricas else None
    with engine.connect() as conn:
        conn.execute(
            text("""
                UPDATE dashboard.tb_controle_processamento
                SET dt_fim = NOW(),
                    st_status = :status,
                    ds_metricas = CAST(:metricas AS jsonb),
                    qt_registros = :qt,
                    ds_erro = :erro
                WHERE co_seq = :id
            """),
            {
                "id": co_seq,
                "status": st_status,
                "metricas": metricas_json,
                "qt": qt_registros,
                "erro": ds_erro,
            },
        )
        conn.commit()
    logger.info(f"Processamento ID={co_seq} finalizado: {st_status}")


def listar_processamentos(
    tp_processamento: Optional[str] = None,
    limite: int = 20,
) -> list[dict]:
    """Lista os últimos processamentos registrados."""
    sql = """
        SELECT co_seq, tp_processamento, dt_inicio, dt_fim,
               st_status, ds_modelo, ds_metricas, qt_registros, ds_observacao, ds_erro
        FROM dashboard.tb_controle_processamento
    """
    params = {}
    if tp_processamento:
        sql += " WHERE tp_processamento = :tp"
        params["tp"] = tp_processamento
    sql += f" ORDER BY dt_inicio DESC LIMIT {limite}"
    return execute_query(sql, params)


def ultimo_processamento(tp_processamento: str) -> Optional[dict]:
    """Retorna o último processamento concluído de um tipo."""
    rows = execute_query(
        """
        SELECT co_seq, dt_inicio, dt_fim, st_status, ds_modelo,
               ds_metricas, qt_registros, ds_observacao
        FROM dashboard.tb_controle_processamento
        WHERE tp_processamento = :tp AND st_status = 'concluido'
        ORDER BY dt_fim DESC
        LIMIT 1
        """,
        {"tp": tp_processamento},
    )
    return rows[0] if rows else None
