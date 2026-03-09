"""
Gravação e consulta da tabela de auditoria de outliers.

A tabela dashboard.tb_auditoria_outliers armazena todos os registros
suspeitos detectados pelo pipeline de qualidade, permitindo revisão humana.

Status de revisão:
  0 = pendente
  1 = confirmado_erro     (erro de digitação, dado inválido)
  2 = confirmado_real     (dado real, manter nas análises)
"""

from __future__ import annotations
import pandas as pd
from datetime import datetime
from typing import Optional

from sqlalchemy import text

from app.core.database import engine, SessionLocal
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.modules.pressao_arterial.quality.outlier_detector import OutlierInfo

logger = setup_logging("pa.quality.audit_table")

_SCHEMA = settings.DB_SCHEMA
_TABELA = f"{_SCHEMA}.tb_auditoria_outliers"


def criar_tabela_auditoria() -> bool:
    """
    Cria a tabela de auditoria se ainda não existir.
    Chamado automaticamente no startup da API.

    Returns:
        True se criada ou já existia, False em caso de erro.
    """
    sql = f"""
    CREATE TABLE IF NOT EXISTS {_TABELA} (
        co_seq_auditoria    SERIAL PRIMARY KEY,
        co_seq_medicao      INTEGER,
        co_seq_cidadao      INTEGER,
        nu_pa_original      VARCHAR(20),
        pas_valor           NUMERIC(6,1),
        pad_valor           NUMERIC(6,1),
        tp_outlier          VARCHAR(30) NOT NULL,
        ds_motivo           TEXT,
        vl_zscore           NUMERIC(8,4),
        dt_deteccao         TIMESTAMP DEFAULT NOW(),
        st_revisado         SMALLINT DEFAULT 0
            CHECK (st_revisado IN (0, 1, 2)),
        ds_observacao       TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_audit_medicao
        ON {_TABELA} (co_seq_medicao);

    CREATE INDEX IF NOT EXISTS idx_audit_cidadao
        ON {_TABELA} (co_seq_cidadao);

    CREATE INDEX IF NOT EXISTS idx_audit_revisado
        ON {_TABELA} (st_revisado);

    COMMENT ON TABLE {_TABELA} IS
        'Outliers detectados pelo pipeline de qualidade — pendentes de revisão humana';

    COMMENT ON COLUMN {_TABELA}.st_revisado IS
        '0=pendente | 1=confirmado_erro | 2=confirmado_real';
    """
    try:
        with engine.connect() as conn:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_SCHEMA}"))
            conn.execute(text(sql))
            conn.commit()
        logger.info(f"Tabela de auditoria '{_TABELA}' pronta.")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar tabela de auditoria: {e}")
        return False


def gravar_outliers(outliers: list[OutlierInfo]) -> int:
    """
    Insere uma lista de OutlierInfo na tabela de auditoria.
    Usa INSERT ... ON CONFLICT DO NOTHING para evitar duplicatas
    baseadas em (co_seq_medicao, tp_outlier).

    Returns:
        Número de registros inseridos.
    """
    if not outliers:
        logger.info("Nenhum outlier para gravar.")
        return 0

    sql = f"""
    INSERT INTO {_TABELA}
        (co_seq_medicao, co_seq_cidadao, nu_pa_original, pas_valor, pad_valor,
         tp_outlier, ds_motivo, vl_zscore, dt_deteccao)
    VALUES
        (:co_seq_medicao, :co_seq_cidadao, :nu_pa_original, :pas_valor, :pad_valor,
         :tp_outlier, :ds_motivo, :vl_zscore, :dt_deteccao)
    """

    agora = datetime.now()
    registros = [
        {
            "co_seq_medicao": o.co_seq_medicao,
            "co_seq_cidadao": o.co_seq_cidadao,
            "nu_pa_original": o.nu_pa_original[:20] if o.nu_pa_original else None,
            "pas_valor": o.pas_valor,
            "pad_valor": o.pad_valor,
            "tp_outlier": o.tp_outlier,
            "ds_motivo": o.ds_motivo,
            "vl_zscore": o.vl_zscore,
            "dt_deteccao": agora,
        }
        for o in outliers
    ]

    try:
        with engine.connect() as conn:
            conn.execute(text(sql), registros)
            conn.commit()
        logger.info(f"{len(registros):,} outliers gravados na tabela de auditoria.")
        return len(registros)
    except Exception as e:
        logger.error(f"Erro ao gravar outliers: {e}")
        raise


def buscar_pendentes(limite: int = 100, offset: int = 0) -> pd.DataFrame:
    """
    Retorna outliers pendentes de revisão (st_revisado = 0).

    Args:
        limite: máximo de registros retornados
        offset: paginação

    Returns:
        DataFrame com os outliers pendentes.
    """
    sql = f"""
    SELECT
        co_seq_auditoria,
        co_seq_medicao,
        co_seq_cidadao,
        nu_pa_original,
        pas_valor,
        pad_valor,
        tp_outlier,
        ds_motivo,
        vl_zscore,
        dt_deteccao,
        st_revisado
    FROM {_TABELA}
    WHERE st_revisado = 0
    ORDER BY dt_deteccao DESC
    LIMIT :limite OFFSET :offset
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql), {"limite": limite, "offset": offset})
            colunas = result.keys()
            return pd.DataFrame(result.fetchall(), columns=list(colunas))
    except Exception as e:
        logger.error(f"Erro ao buscar pendentes: {e}")
        return pd.DataFrame()


def contar_por_status() -> dict:
    """
    Retorna contagem de outliers agrupados por status de revisão.
    Usado no endpoint de qualidade de dados.
    """
    sql = f"""
    SELECT
        st_revisado,
        COUNT(*) AS total
    FROM {_TABELA}
    GROUP BY st_revisado
    ORDER BY st_revisado
    """
    mapa = {0: "pendente", 1: "confirmado_erro", 2: "confirmado_real"}
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            return {
                mapa.get(row[0], str(row[0])): row[1]
                for row in result.fetchall()
            }
    except Exception as e:
        logger.error(f"Erro ao contar outliers: {e}")
        return {}
