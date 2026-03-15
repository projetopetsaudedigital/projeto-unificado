"""
Modelos Pydantic para os endpoints de analytics de Pressão Arterial.

Cada campo tem descrição, exemplo e origem (qual view/tabela alimenta o dado),
exibidos automaticamente no Swagger UI (/docs).
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ─── KPIs gerais ────────────────────────────────────────────────────────────

class KPIsGerais(BaseModel):
    total_cadastros: int = Field(
        description="Total de cidadãos adultos (≥18 anos), vivos e com bairro preenchido "
                    "no Cadastro Individual do e-SUS PEC.",
        examples=[347371],
    )
    total_hipertensos: int = Field(
        description="Cidadãos com st_hipertensao_arterial = 1 no cadastro individual. "
                    "Campo autodeclarado ou registrado pelo profissional de saúde.",
        examples=[89100],
    )
    prevalencia_geral_pct: float = Field(
        description="Percentual de hipertensos em relação ao total de cadastros. "
                    "Fórmula: (total_hipertensos / total_cadastros) × 100.",
        examples=[25.6],
    )
    total_vdc_identificados: int = Field(
        description="Cidadãos cujo endereço foi reconhecido em um bairro do GeoJSON VDC "
                    "(st_bairro_vdc = TRUE). Usado nas análises geoespaciais por bairro.",
        examples=[68932],
    )
    total_nao_identificados: int = Field(
        description="Cidadãos com endereço não reconhecido no GeoJSON VDC "
                    "(st_bairro_vdc = FALSE ou NULL). Incluídos no total_cadastros.",
        examples=[3432],
    )
    total_bairros: int = Field(
        description="Número de bairros distintos reconhecidos no GeoJSON VDC "
                    "com ao menos um cadastro.",
        examples=[98],
    )


class KPIsResponse(BaseModel):
    dados: KPIsGerais


# ─── Tendência temporal ──────────────────────────────────────────────────────

class PontoTendencia(BaseModel):
    mes_ano: date = Field(
        description="Primeiro dia do mês de referência (ex: 2024-03-01).",
        examples=["2024-03-01"],
    )
    ano: int = Field(description="Ano da medição.", examples=[2024])
    mes: int = Field(description="Mês da medição (1-12).", examples=[3])
    total_medicoes: int = Field(
        description="Total de medições de PA registradas no mês, "
                    "provenientes de tb_medicao via mv_pa_medicoes_cidadaos.",
        examples=[1832],
    )
    total_cidadaos: int = Field(
        description="Cidadãos distintos com ao menos uma medição no mês.",
        examples=[1540],
    )
    normal: int = Field(
        description="Medições com PAS < 120 mmHg E PAD < 80 mmHg (PA ótima/normal). "
                    "Classificação JNC 8 / Diretrizes SBC 2020.",
        examples=[612],
    )
    elevada: int = Field(
        description="Medições com PAS entre 120-129 mmHg e PAD < 80 mmHg (PA elevada).",
        examples=[210],
    )
    has_estagio_1: int = Field(
        description="Medições com PAS 130-139 mmHg OU PAD 80-89 mmHg (HAS Estágio 1).",
        examples=[480],
    )
    has_estagio_2: int = Field(
        description="Medições com PAS 140-179 mmHg OU PAD 90-119 mmHg (HAS Estágio 2).",
        examples=[398],
    )
    has_estagio_3: int = Field(
        description="Medições com PAS ≥ 180 mmHg OU PAD ≥ 120 mmHg (HAS Estágio 3 / crise).",
        examples=[132],
    )
    media_pas: Optional[float] = Field(
        description="Média da Pressão Arterial Sistólica (mmHg) no mês.",
        examples=[138.5],
    )
    media_pad: Optional[float] = Field(
        description="Média da Pressão Arterial Diastólica (mmHg) no mês.",
        examples=[86.2],
    )


class TendenciaResponse(BaseModel):
    total: int = Field(description="Número de meses retornados.")
    filtros_aplicados: dict = Field(description="Filtros usados na consulta.")
    dados: list[PontoTendencia]


# ─── Prevalência ─────────────────────────────────────────────────────────────

class PrevalenciaBairro(BaseModel):
    bairro: str = Field(
        description="Nome do bairro normalizado (campo no_bairro_filtro da tb_cidadao). "
                    "Após normalização: nome canônico via ViaCEP ou fuzzy matching.",
        examples=["patagonia"],
    )
    total_cadastros: int = Field(
        description="Total de cidadãos adultos cadastrados no bairro.",
        examples=[56072],
    )
    hipertensos: int = Field(
        description="Cidadãos com st_hipertensao_arterial = 1 no bairro.",
        examples=[14500],
    )
    prevalencia_pct: Optional[float] = Field(
        description="Prevalência de HAS no bairro (%). "
                    "Fórmula: (hipertensos / total_cadastros) × 100.",
        examples=[25.9],
    )


class PrevalenciaSexo(BaseModel):
    sexo: Optional[str] = Field(description="Descrição do sexo (ex: 'Feminino', 'Masculino').")
    sg_sexo: Optional[str] = Field(description="Sigla do sexo (ex: 'F', 'M').")
    total: int = Field(description="Total de cadastros com este sexo.")
    hipertensos: int = Field(description="Hipertensos com este sexo.")
    prevalencia_pct: Optional[float] = Field(description="Prevalência (%).")


class PrevalenciaFaixaEtaria(BaseModel):
    faixa_etaria: str = Field(
        description="Faixa etária calculada com base em dt_nascimento. "
                    "Grupos: '18-29', '30-39', '40-49', '50-59', '60-64', '65+'.",
        examples=["50-59"],
    )
    total: int = Field(description="Total de cadastros nesta faixa.")
    hipertensos: int = Field(description="Hipertensos nesta faixa.")
    prevalencia_pct: Optional[float] = Field(description="Prevalência (%).")


class PrevalenciaResponse(BaseModel):
    total: int = Field(description="Número de grupos retornados.")
    agrupamento: str = Field(description="Agrupamento usado: 'bairro', 'sexo' ou 'faixa_etaria'.")
    filtros_aplicados: dict
    dados: list
    nao_identificados: Optional[dict] = Field(
        default=None,
        description="Resumo dos cadastros sem bairro VDC identificado (disponivel apenas no agrupamento por bairro)."
    )


# ─── Fatores de risco ────────────────────────────────────────────────────────

class ComorbidadeComparativo(BaseModel):
    fator: str = Field(
        description="Nome legível do fator de risco ou comorbidade.",
        examples=["Diabetes"],
    )
    coluna: str = Field(
        description="Nome da coluna correspondente na view mv_pa_cadastros.",
        examples=["st_diabetes"],
    )
    pct_hipertensos: Optional[float] = Field(
        description="Percentual de hipertensos (st_hipertensao_arterial = 1) "
                    "que também têm esta comorbidade.",
        examples=[28.4],
    )
    pct_nao_hipertensos: Optional[float] = Field(
        description="Percentual de não-hipertensos que têm esta comorbidade.",
        examples=[12.1],
    )
    n_hipertensos: int = Field(
        description="Contagem absoluta de hipertensos com a comorbidade.",
        examples=[25320],
    )
    n_nao_hipertensos: int = Field(
        description="Contagem absoluta de não-hipertensos com a comorbidade.",
        examples=[9840],
    )


class FatoresRiscoResponse(BaseModel):
    total: int
    tipo: str = Field(
        description="Tipo de análise: 'comparativo_comorbidades' ou 'multiplos_fatores'."
    )
    filtros_aplicados: Optional[dict] = None
    dados: list


# ─── Mapa ────────────────────────────────────────────────────────────────────

class DadosBairrMapa(BaseModel):
    bairro: str = Field(description="Nome do bairro (GeoJSON oficial VDC).")
    lat: Optional[float] = Field(description="Latitude do centróide do bairro.")
    lng: Optional[float] = Field(description="Longitude do centróide do bairro.")
    geo_fonte: Optional[str] = Field(description="Fonte da geocodificação.")
    geo_tipo: Optional[str] = Field(None, description="'bairro' ou 'loteamento'")
    total_cadastros: int = Field(description="Total de cidadãos cadastrados no bairro.")
    hipertensos: int = Field(description="Hipertensos no bairro.")
    prevalencia_pct: Optional[float] = Field(description="Prevalência de HAS (%).")
    n_diabetes: int = Field(description="Diabéticos cadastrados.")
    n_avc: int = Field(description="Cidadãos com AVC registrado.")
    n_infarto: int = Field(description="Cidadãos com infarto registrado.")
    n_fumantes: int = Field(description="Fumantes cadastrados.")
    n_idosos: int = Field(description="Cidadãos com 65+ anos.")
    pct_idosos: Optional[float] = Field(description="Percentual de idosos (%).")


class MapaResponse(BaseModel):
    total_bairros: int
    filtros_aplicados: dict
    dados: list[DadosBairrMapa]


# ─── Bairros ─────────────────────────────────────────────────────────────────

class BairrosResponse(BaseModel):
    total: int = Field(description="Número de bairros distintos com cadastros.")
    bairros: list[str] = Field(description="Lista ordenada de nomes de bairros (campo no_bairro_filtro).")


# ─── UBS ─────────────────────────────────────────────────────────────────────

class UbsItem(BaseModel):
    co_seq_unidade_saude: int = Field(description="ID interno da UBS.")
    nu_cnes: Optional[str] = Field(description="Código CNES da unidade de saúde.")
    no_unidade_saude: str = Field(
        description="Nome da unidade de saúde.",
        examples=["UBS PATAGONIA"],
    )
    bairro_ubs: Optional[str] = Field(
        description="Bairro onde a UBS está localizada (tb_unidade_saude.no_bairro).",
        examples=["PATAGONIA"],
    )
    no_bairro_filtro: Optional[str] = Field(
        description="Versão normalizada do bairro da UBS para buscas.",
    )
    total_pacientes: int = Field(
        description="Pacientes únicos com ao menos uma medição de PA nesta UBS.",
        examples=[4820],
    )
    hipertensos: int = Field(
        description="Pacientes únicos com st_hipertensao_arterial = 1 no cadastro.",
        examples=[1240],
    )
    prevalencia_pct: Optional[float] = Field(
        description="Prevalência de HAS entre os pacientes com medição nesta UBS (%).",
        examples=[25.7],
    )
    total_medicoes: int = Field(
        description="Total de medições de PA registradas na UBS.",
        examples=[12300],
    )


class UbsResponse(BaseModel):
    total: int = Field(description="Número de UBS retornadas.")
    filtros_aplicados: dict
    dados: list[UbsItem]


# ─── Individuos com hipertensao ────────────────────────────────────────────

class PerfilPacienteItem(BaseModel):
    nome: Optional[str] = Field(
        default=None,
        description="Nome do paciente quando disponível no cadastro do PEC.",
        examples=["Ana Carolina Souza"],
    )
    idade: Optional[int] = Field(
        default=None,
        description="Idade atual do cidadao em anos completos.",
        examples=[54],
    )
    sexo: Optional[str] = Field(
        default=None,
        description="Sigla de sexo no cadastro (M/F).",
        examples=["F"],
    )


class TerritorioPacienteItem(BaseModel):
    area: Optional[str] = Field(
        default=None,
        description="Area de adscricao do cidadao (nu_area).",
        examples=["2"],
    )
    microarea: Optional[str] = Field(
        default=None,
        description="Microarea de adscricao do cidadao (nu_micro_area).",
        examples=["03"],
    )


class MedianaAnualItem(BaseModel):
    pas: Optional[float] = Field(
        default=None,
        description="Mediana da PAS nos ultimos 365 dias.",
        examples=[150.0],
    )
    pad: Optional[float] = Field(
        default=None,
        description="Mediana da PAD nos ultimos 365 dias.",
        examples=[90.0],
    )


class UltimaMedicaoItem(BaseModel):
    data_medicao: date = Field(
        description="Data da medicao considerada na lista de ultimas afericoes.",
        examples=["2026-03-10"],
    )
    pas: float = Field(description="PAS da medicao (ou mediana diaria).", examples=[160.0])
    pad: float = Field(description="PAD da medicao (ou mediana diaria).", examples=[100.0])
    pressao: str = Field(
        description="Representacao textual da afericao no formato PAS/PAD.",
        examples=["160/100"],
    )

class IndividuoHipertensaoItem(BaseModel):
    co_cidadao: int = Field(
        description="Identificador unico do cidadao no e-SUS PEC.",
        examples=[1234567],
    )
    n_medicoes_usadas: int = Field(
        description="Quantidade de dias usados no calculo da mediana (1 a 3).",
        examples=[3],
    )
    dt_ultima_medicao: date = Field(
        description="Data da medicao mais recente considerada no calculo.",
        examples=["2026-03-10"],
    )
    paciente_perfil: PerfilPacienteItem = Field(
        description="Perfil clinico-demografico resumido do paciente.",
    )
    territorio: TerritorioPacienteItem = Field(
        description="Informacoes territoriais operacionais (area e microarea).",
    )
    ultimas_medicoes: list[UltimaMedicaoItem] = Field(
        description="Ate 3 ultimas afericoes de PA no periodo analisado.",
    )
    mediana_anual: MedianaAnualItem = Field(
        description="Mediana anual de PA considerando os ultimos 365 dias.",
    )
    outras_condicoes: list[str] = Field(
        description="Lista de comorbidades e fatores de risco ativos no cadastro.",
        examples=[["Diabetes", "Problema Renal"]],
    )
    status_atual: str = Field(
        description="Status atual de controle pressorico pela regra da mediana final.",
        examples=["Descontrolado"],
    )


class IndividuosHipertensaoResponse(BaseModel):
    total: int = Field(description="Total de individuos para os filtros aplicados.")
    total_controlados: int = Field(description="Total com mediana recente < 140/90 mmHg.")
    total_descontrolados: int = Field(description="Total com mediana recente >= 140 ou >= 90 mmHg.")
    limite: int = Field(description="Tamanho da pagina retornada.")
    offset: int = Field(description="Deslocamento da pagina atual.")
    filtros_aplicados: dict = Field(description="Resumo dos filtros usados na consulta.")
    dados: list[IndividuoHipertensaoItem]
