"""Schemas Pydantic do endpoint de individuos em diabetes."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class PerfilPacienteItem(BaseModel):
    nome: Optional[str] = Field(default=None, examples=["Maria da Silva"])
    idade: Optional[int] = Field(default=None, examples=[62])
    sexo: Optional[str] = Field(default=None, examples=["F"])


class TerritorioPacienteItem(BaseModel):
    area: Optional[str] = Field(default=None, examples=["2"])
    microarea: Optional[str] = Field(default=None, examples=["03"])


class Hba1cAtualItem(BaseModel):
    valor: float = Field(description="Valor do ultimo HbA1c no periodo.", examples=[8.2])
    data: date = Field(description="Data do ultimo exame HbA1c.", examples=["2026-03-10"])


class UltimoExameItem(BaseModel):
    data_medicao: date = Field(examples=["2026-03-10"])
    hba1c: float = Field(examples=[8.2])
    exame: str = Field(examples=["HbA1c"])


class IndividuoDiabetesItem(BaseModel):
    co_cidadao: int = Field(description="Identificador do cidadao.", examples=[1234567])
    paciente_perfil: PerfilPacienteItem
    territorio: TerritorioPacienteItem
    hba1c_atual: Hba1cAtualItem
    ultimas_medicoes: list[UltimoExameItem]
    outras_condicoes: list[str]
    status_atual: str = Field(description="Controlado ou Descontrolado.", examples=["Descontrolado"])


class IndividuosDiabetesResponse(BaseModel):
    total: int
    limite: int
    offset: int
    filtros_aplicados: dict
    dados: list[IndividuoDiabetesItem]
