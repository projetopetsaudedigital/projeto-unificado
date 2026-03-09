"""
Endpoints de Machine Learning para obesidade / classificação de IMC.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.modules.obesidade.ml.pipeline import treinar_modelo
from app.modules.obesidade.ml.predictor import get_modelo_info, predizer
from app.modules.obesidade.schemas import (
    ModeloObesidadeInfoResponse,
    PerfilAntropometrico,
    PredicaoIMCResponse,
    ProbabilidadesIMC,
)
from app.core.logging_config import setup_logging

logger = setup_logging("ob.routes.ml")
router = APIRouter()

# Flag para evitar treinos simultâneos
_treino_em_andamento = False


def _treinar_background():
    global _treino_em_andamento
    try:
        _treino_em_andamento = True
        treinar_modelo()
    except Exception as e:
        logger.error(f"Erro no treino background: {e}")
    finally:
        _treino_em_andamento = False


@router.get(
    "/modelo/info",
    response_model=ModeloObesidadeInfoResponse,
    summary="Status e métricas do modelo de obesidade",
    description="Retorna se o modelo está treinado, métricas de validação cruzada, "
                "acurácia por classe de IMC e importância das features.",
)
def endpoint_modelo_info():
    try:
        info = get_modelo_info()
        info["treino_em_andamento"] = _treino_em_andamento
        return ModeloObesidadeInfoResponse(**info)
    except Exception as e:
        logger.error(f"Erro em /modelo/info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/modelo/treinar",
    summary="Treinar modelo de classificação de IMC",
    description="Dispara o treinamento do RandomForest em background. "
                "Use GET /modelo/status-treino para acompanhar. "
                "Registra métricas em tb_controle_processamento.",
)
def endpoint_treinar(background_tasks: BackgroundTasks):
    global _treino_em_andamento
    if _treino_em_andamento:
        return {"status": "em_andamento", "mensagem": "Treino já está em execução."}
    background_tasks.add_task(_treinar_background)
    return {"status": "iniciado", "mensagem": "Treinamento iniciado em background."}


@router.get(
    "/modelo/status-treino",
    summary="Verificar se treino está em andamento",
)
def endpoint_status_treino():
    return {"treino_em_andamento": _treino_em_andamento}


@router.post(
    "/predizer-imc",
    response_model=PredicaoIMCResponse,
    summary="Predizer classificação de IMC individual",
    description="Recebe perfil antropométrico e retorna a classificação de IMC predita "
                "(6 classes OMS), probabilidades por classe e nível de confiança.",
)
def endpoint_predizer(perfil: PerfilAntropometrico):
    try:
        resultado = predizer(
            peso_kg=perfil.peso_kg,
            altura_m=perfil.altura_m,
            idade=perfil.idade,
            sexo=perfil.sexo,
            st_hipertensao=perfil.st_hipertensao,
            st_diabete=perfil.st_diabete,
            st_fumante=perfil.st_fumante,
            st_alcool=perfil.st_alcool,
            st_doenca_cardiaca=perfil.st_doenca_cardiaca,
            st_doenca_respiratoria=perfil.st_doenca_respiratoria,
        )
        return PredicaoIMCResponse(
            imc_calculado=resultado["imc_calculado"],
            classificacao_predita=resultado["classificacao_predita"],
            probabilidades=ProbabilidadesIMC(**resultado["probabilidades"]),
            confianca=resultado["confianca"],
            nivel_confianca=resultado["nivel_confianca"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Erro em /predizer-imc: {e}")
        raise HTTPException(status_code=500, detail=str(e))
