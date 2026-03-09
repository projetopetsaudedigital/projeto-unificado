"""
Endpoints de Machine Learning — Controle Glicêmico (Diabetes).

GET  /modelo/info       → status e métricas do modelo treinado
POST /modelo/treinar    → dispara o treinamento (leva 2-5 min)
POST /predizer-controle → prediz probabilidade de controle glicêmico
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional

from app.modules.diabetes.ml.predictor import (
    info_modelo,
    predizer_controle,
    modelo_disponivel,
)
from app.core.logging_config import setup_logging

logger = setup_logging("dm.routes.ml")

router = APIRouter()

_treinamento_em_andamento = False


# ── Schemas ──────────────────────────────────────────────────────────────────

class PerfilDiabetico(BaseModel):
    """Perfil do paciente diabético para predição de controle glicêmico."""

    idade:       int   = Field(..., ge=18, le=110, description="Idade em anos.", examples=[60])
    co_dim_sexo: int   = Field(default=1, description="1=Masculino, 3=Feminino.", examples=[3])
    hba1c:       float = Field(..., ge=3.0, le=20.0, description="Hemoglobina glicada (%)", examples=[7.5])

    st_hipertensao:        int = Field(default=0, ge=0, le=1)
    st_doenca_cardiaca:    int = Field(default=0, ge=0, le=1)
    st_insuf_cardiaca:     int = Field(default=0, ge=0, le=1)
    st_infarto:            int = Field(default=0, ge=0, le=1)
    st_problema_rins:      int = Field(default=0, ge=0, le=1)
    st_avc:                int = Field(default=0, ge=0, le=1)
    st_fumante:            int = Field(default=0, ge=0, le=1)
    st_alcool:             int = Field(default=0, ge=0, le=1)
    st_doenca_respiratoria:int = Field(default=0, ge=0, le=1)
    st_cancer:             int = Field(default=0, ge=0, le=1)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/modelo/info", summary="Status e métricas do modelo de controle glicêmico")
def modelo_info():
    return info_modelo()


@router.post("/modelo/treinar", summary="Treina (ou re-treina) o modelo de controle glicêmico")
def treinar(background_tasks: BackgroundTasks):
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
            from app.modules.diabetes.ml.pipeline import treinar_modelo
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


@router.post("/predizer-controle", summary="Prediz probabilidade de controle glicêmico")
def predizer(perfil: PerfilDiabetico):
    """
    Recebe o perfil de um paciente diabético e retorna a probabilidade estimada
    de estar com controle glicêmico adequado (HbA1c dentro da meta SBD 2024).

    **Importante:** Resultado estimativo. Não substitui avaliação clínica.
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
        resultado = predizer_controle(perfil.model_dump())
        return resultado
    except Exception as e:
        logger.error(f"Erro na predição: {e}")
        raise HTTPException(status_code=500, detail=str(e))
