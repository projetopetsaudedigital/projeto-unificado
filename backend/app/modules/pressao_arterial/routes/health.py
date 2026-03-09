"""
Router de health check da API.
Valida conexão com banco e retorna status dos componentes.
"""

from fastapi import APIRouter
from app.core.database import test_connection
from app.modules.pressao_arterial.quality.audit_table import (
    criar_tabela_auditoria,
    contar_por_status,
)

router = APIRouter()


@router.get("/health", summary="Health check da API e banco de dados")
def health_check():
    """
    Verifica se a API está no ar e se a conexão com o banco está funcionando.
    Cria a tabela de auditoria se não existir.
    """
    db_info = test_connection()
    criar_tabela_auditoria()
    outliers_resumo = contar_por_status()

    return {
        "api": "online",
        "database": db_info,
        "auditoria_outliers": outliers_resumo,
    }
