"""
Router de qualidade de dados — Pressão Arterial.

Endpoints:
  GET  /qualidade/resumo         → contagem por status de outlier
  GET  /qualidade/pendentes      → lista outliers aguardando revisão
  POST /qualidade/executar       → roda o pipeline de qualidade nos dados do banco
"""

from fastapi import APIRouter, Query
from typing import Optional
import pandas as pd

from app.core.database import execute_query
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.modules.pressao_arterial.quality.validator import processar_dataframe
from app.modules.pressao_arterial.quality.outlier_detector import executar_pipeline_outliers
from app.modules.pressao_arterial.quality.audit_table import (
    contar_por_status,
    buscar_pendentes,
    gravar_outliers,
)
from app.modules.pressao_arterial.views.manager import status_views, atualizar_todas

logger = setup_logging("pa.routes.qualidade")
router = APIRouter()


@router.get("/qualidade/resumo", summary="Resumo dos outliers por status de revisão")
def resumo_qualidade():
    """
    Retorna quantos outliers existem na tabela de auditoria,
    agrupados por status: pendente, confirmado_erro, confirmado_real.
    """
    contagem = contar_por_status()
    total = sum(contagem.values())
    return {
        "total_outliers": total,
        "por_status": contagem,
    }


@router.get("/qualidade/pendentes", summary="Lista outliers pendentes de revisão")
def listar_pendentes(
    limite: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    """
    Retorna os outliers que ainda não foram revisados (st_revisado = 0).
    Útil para o painel de qualidade de dados do gestor.
    """
    df = buscar_pendentes(limite=limite, offset=offset)
    if df.empty:
        return {"total": 0, "registros": []}

    registros = df.where(pd.notnull(df), None).to_dict(orient="records")
    return {
        "total": len(registros),
        "registros": registros,
    }


@router.get("/qualidade/views", summary="Status das views materializadas")
def status_views_endpoint():
    """
    Retorna quais views materializadas existem no banco e quantas linhas têm.
    Útil para verificar se o setup inicial foi executado corretamente.
    """
    views = status_views()
    return {
        "views": [
            {
                "name": v.name,
                "exists": v.exists,
                "row_count": v.row_count,
            }
            for v in views
        ]
    }


@router.post("/qualidade/views/refresh", summary="Atualiza todas as views materializadas")
def refresh_views():
    """
    Executa REFRESH MATERIALIZED VIEW CONCURRENTLY em todas as views.
    Use após importar novos dados no e-SUS PEC.
    """
    resultados = atualizar_todas(concurrently=True)
    sucesso = all(resultados.values())
    return {
        "status": "ok" if sucesso else "parcial",
        "views": resultados,
    }


@router.post("/qualidade/executar", summary="Executa o pipeline de qualidade nos dados do banco")
def executar_pipeline_qualidade(
    limite: int = Query(
        default=10000,
        ge=100,
        le=500000,
        description="Máximo de medições a processar nesta execução",
    )
):
    """
    Carrega medições do banco, roda validação técnica e detecção de outliers,
    e grava os resultados suspeitos na tabela de auditoria.

    Use este endpoint para rodar manualmente ou agendar via cron.
    """
    logger.info(f"Iniciando pipeline de qualidade (limite={limite:,})...")

    # Carrega medições da view materializada
    sql = f"""
    SELECT
        co_seq_medicao,
        nu_medicao_pressao_arterial,
        dt_medicao
    FROM {settings.DB_SCHEMA}.mv_pa_medicoes
    ORDER BY dt_medicao DESC
    LIMIT :limite
    """
    try:
        registros = execute_query(sql, {"limite": limite})
    except Exception as e:
        return {"status": "erro", "mensagem": f"Falha ao carregar dados: {e}"}

    if not registros:
        return {"status": "ok", "mensagem": "Nenhum dado encontrado na view de medições."}

    df = pd.DataFrame(registros)
    logger.info(f"{len(df):,} medições carregadas.")

    # Validação técnica
    df = processar_dataframe(df)

    # Detecção de outliers (apenas nos que têm PAS/PAD)
    df, lista_outliers = executar_pipeline_outliers(df)

    # Filtra apenas os suspeitos/inválidos para auditoria
    outliers_para_gravar = [
        o for o in lista_outliers
        if o.co_seq_medicao is not None
    ]

    gravados = gravar_outliers(outliers_para_gravar) if outliers_para_gravar else 0

    validos = (df["status_validacao"] == "valido").sum()
    suspeitos = (df["status_validacao"] == "suspeito").sum()
    invalidos = (df["status_validacao"] == "invalido").sum()
    outliers_pop = df.get("outlier_populacional", pd.Series([False]*len(df))).sum()
    outliers_ind = df.get("outlier_individual", pd.Series([False]*len(df))).sum()

    return {
        "status": "ok",
        "total_processado": len(df),
        "validacao": {
            "validos": int(validos),
            "suspeitos": int(suspeitos),
            "invalidos": int(invalidos),
            "percentual_valido": round(validos / len(df) * 100, 2),
        },
        "outliers": {
            "iqr_populacional": int(outliers_pop),
            "zscore_individual": int(outliers_ind),
            "gravados_auditoria": gravados,
        },
    }
