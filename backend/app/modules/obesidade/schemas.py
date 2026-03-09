"""
Schemas Pydantic para o módulo de Obesidade.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ── KPIs ──────────────────────────────────────────────────────────────────────

class KPIsObesidade(BaseModel):
    total_medicoes: int = Field(description="Total de medições no período")
    total_adultos: int = Field(description="Adultos únicos com medição")
    imc_medio: float = Field(description="IMC médio da população")
    prevalencia_sobrepeso_pct: float = Field(description="% com sobrepeso (IMC >= 25)")
    prevalencia_obesidade_pct: float = Field(description="% com obesidade (IMC >= 30)")
    prevalencia_obesidade_g2g3_pct: float = Field(description="% com obesidade grau 2 ou 3 (IMC >= 35)")
    tendencia_mensal: float = Field(description="Variação mensal do IMC médio (ponto/mês)")

class KPIsObesidadeResponse(BaseModel):
    kpis: KPIsObesidade
    filtros: dict


# ── Tendência ─────────────────────────────────────────────────────────────────

class PontoTendenciaObesidade(BaseModel):
    mes_ano: str
    imc_medio: float
    total_medicoes: int
    pct_normal: float
    pct_sobrepeso: float
    pct_obesidade_i: float
    pct_obesidade_ii: float
    pct_obesidade_iii: float
    pct_baixo_peso: float

class TendenciaObesidadeResponse(BaseModel):
    serie: list[PontoTendenciaObesidade]


# ── Distribuição ──────────────────────────────────────────────────────────────

class DistribuicaoClasse(BaseModel):
    classificacao: str
    total: int
    percentual: float

class DistribuicaoPorSexo(BaseModel):
    sexo: str
    total: int
    imc_medio: float
    pct_obesidade: float

class DistribuicaoPorFaixaEtaria(BaseModel):
    faixa_etaria: str
    total: int
    imc_medio: float
    pct_obesidade: float

class DistribuicaoObesidadeResponse(BaseModel):
    por_classificacao: list[DistribuicaoClasse]
    por_sexo: list[DistribuicaoPorSexo]
    por_faixa_etaria: list[DistribuicaoPorFaixaEtaria]


# ── Fatores de Risco ──────────────────────────────────────────────────────────

class ComorbidadeObesidade(BaseModel):
    comorbidade: str
    pct_baixo_peso: float
    pct_normal: float
    pct_sobrepeso: float
    pct_obesidade_i: float
    pct_obesidade_ii: float
    pct_obesidade_iii: float

class FatoresRiscoObesidadeResponse(BaseModel):
    comorbidades: list[ComorbidadeObesidade]


# ── Por Bairro ────────────────────────────────────────────────────────────────

class BairroObesidade(BaseModel):
    bairro: str
    total_medicoes: int
    total_adultos: int
    imc_medio: float
    pct_obesidade: float
    pct_obesidade_g2g3: float

class BairrosObesidadeResponse(BaseModel):
    bairros: list[BairroObesidade]


# ── ML ────────────────────────────────────────────────────────────────────────

class PerfilAntropometrico(BaseModel):
    peso_kg: float = Field(ge=10, le=350, description="Peso em quilogramas")
    altura_m: float = Field(ge=1.0, le=2.5, description="Altura em metros")
    idade: int = Field(ge=18, le=120, description="Idade em anos")
    sexo: str = Field(description="Sexo: 'M' ou 'F'")
    st_hipertensao: int = Field(default=0, ge=0, le=1)
    st_diabete: int = Field(default=0, ge=0, le=1)
    st_fumante: int = Field(default=0, ge=0, le=1)
    st_alcool: int = Field(default=0, ge=0, le=1)
    st_doenca_cardiaca: int = Field(default=0, ge=0, le=1)
    st_doenca_respiratoria: int = Field(default=0, ge=0, le=1)

class ProbabilidadesIMC(BaseModel):
    baixo_peso: float
    normal: float
    sobrepeso: float
    obesidade_i: float
    obesidade_ii: float
    obesidade_iii: float

class PredicaoIMCResponse(BaseModel):
    imc_calculado: float
    classificacao_predita: str
    probabilidades: ProbabilidadesIMC
    confianca: float
    nivel_confianca: str = Field(description="Baixa (<50%) / Media (50-70%) / Alta (70-90%) / Muito Alta (>90%)")

class MetricasPorClasse(BaseModel):
    classe: str
    precisao: float
    recall: float
    f1: float
    suporte: int

class ModeloObesidadeInfoResponse(BaseModel):
    modelo_treinado: bool
    treinado_em: Optional[str] = None
    total_registros_treino: Optional[int] = None
    distribuicao_treino: Optional[dict] = None
    metricas: Optional[dict] = None
    metricas_por_classe: Optional[list[MetricasPorClasse]] = None
    feature_importances: Optional[dict] = None
    treino_em_andamento: bool = False
