"""
Endpoints de Machine Learning — Risco de Hipertensão Arterial.

GET  /modelo/info       → status e métricas do modelo treinado
POST /modelo/treinar    → dispara o treinamento (leva 2-5 min)
POST /predizer-risco    → prediz probabilidade de HAS para um perfil
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional

from app.modules.pressao_arterial.ml.predictor import (
    info_modelo,
    predizer_risco,
    modelo_disponivel,
)
from app.core.logging_config import setup_logging

logger = setup_logging("pa.routes.ml")

router = APIRouter()

# ── Estado de treinamento ────────────────────────────────────────────────────

_treinamento_em_andamento = False


# ── Schemas ──────────────────────────────────────────────────────────────────

class PerfilPaciente(BaseModel):
    """Perfil do paciente para predição de risco de HAS."""

    idade: int = Field(..., ge=18, le=110, description="Idade em anos (≥18).", examples=[55])
    co_dim_sexo: int = Field(
        default=1,
        description="Código do sexo: 1=Masculino, 3=Feminino (padrão e-SUS).",
        examples=[3],
    )

    # Condições de saúde (0=não/não informado, 1=sim)
    st_diabetes:           int = Field(default=0, ge=0, le=1, description="Diabetes mellitus.")
    st_fumante:            int = Field(default=0, ge=0, le=1, description="Fumante.")
    st_alcool:             int = Field(default=0, ge=0, le=1, description="Uso de álcool.")
    st_outra_droga:        int = Field(default=0, ge=0, le=1, description="Uso de outras drogas.")
    st_doenca_cardiaca:    int = Field(default=0, ge=0, le=1, description="Doença cardíaca.")
    st_problema_rins:      int = Field(default=0, ge=0, le=1, description="Problema nos rins.")
    st_avc:                int = Field(default=0, ge=0, le=1, description="AVC ou derrame.")
    st_infarto:            int = Field(default=0, ge=0, le=1, description="Infarto.")
    st_doenca_respiratoria:int = Field(default=0, ge=0, le=1, description="Doença respiratória crônica.")
    st_cancer:             int = Field(default=0, ge=0, le=1, description="Câncer.")
    st_hanseniase:         int = Field(default=0, ge=0, le=1, description="Hanseníase.")
    st_tuberculose:        int = Field(default=0, ge=0, le=1, description="Tuberculose.")


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/modelo/info", summary="Status e métricas do modelo de risco")
def modelo_info():
    """
    Retorna informações sobre o modelo treinado:
      - Se está disponível
      - Quando foi treinado
      - Métricas de validação (ROC-AUC, F1, precisão, recall)
      - Importância de cada feature
    """
    return info_modelo()


@router.post("/modelo/treinar", summary="Treina (ou re-treina) o modelo de risco de HAS")
def treinar(background_tasks: BackgroundTasks):
    """
    Dispara o treinamento do RandomForestClassifier com TimeSeriesSplit.

    O treinamento roda em background e leva aproximadamente 2-5 minutos.
    Use GET /modelo/info para verificar quando ficou disponível.

    **Atenção:** modelos anteriores são substituídos ao final do treinamento.
    """
    global _treinamento_em_andamento
    if _treinamento_em_andamento:
        raise HTTPException(
            status_code=409,
            detail="Treinamento já em andamento. Aguarde e consulte GET /modelo/info.",
        )

    def _treinar_bg():
        global _treinamento_em_andamento
        _treinamento_em_andamento = True
        try:
            from app.modules.pressao_arterial.ml.pipeline import treinar_modelo
            treinar_modelo()
            logger.info("Treinamento concluído com sucesso.")
        except Exception as e:
            logger.error(f"Erro no treinamento: {e}")
        finally:
            _treinamento_em_andamento = False

    background_tasks.add_task(_treinar_bg)

    return {
        "status": "iniciado",
        "mensagem": "Treinamento iniciado em background. Consulte GET /modelo/info para acompanhar.",
        "em_andamento": True,
    }


@router.get("/modelo/status-treino", summary="Verifica se o treinamento está em andamento")
def status_treino():
    return {
        "em_andamento": _treinamento_em_andamento,
        "modelo_disponivel": modelo_disponivel(),
    }


@router.post("/predizer-risco", summary="Prediz probabilidade de hipertensão para um perfil")
def predizer(perfil: PerfilPaciente):
    """
    Recebe o perfil de um paciente e retorna a probabilidade estimada de
    hipertensão arterial sistêmica (HAS).

    **Importante:** Este é um modelo preditivo baseado em dados populacionais.
    O resultado não substitui avaliação clínica.

    Retorna:
      - probabilidade (0–1) e percentual
      - nível de risco: Baixo (<20%), Moderado (20–35%), Alto (>35%)
      - top fatores que mais influenciaram a predição
    """
    if not modelo_disponivel():
        raise HTTPException(
            status_code=503,
            detail="Modelo não disponível. Treine primeiro via POST /modelo/treinar.",
        )
    if _treinamento_em_andamento:
        raise HTTPException(
            status_code=503,
            detail="Modelo em re-treinamento. Tente novamente em alguns minutos.",
        )

    try:
        resultado = predizer_risco(perfil.model_dump())
        return resultado
    except Exception as e:
        logger.error(f"Erro na predição: {e}")
        raise HTTPException(status_code=500, detail=str(e))
