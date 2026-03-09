"""
Validação técnica de medições de pressão arterial.

Retorna status por registro:
  - "valido"   → dentro dos limites fisiológicos, PAS > PAD
  - "invalido" → não parseável ou fora dos limites absolutos
  - "suspeito" → válido fisiologicamente mas extremo (outlier candidato)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import pandas as pd

from app.core.config import settings
from app.core.logging_config import setup_logging

logger = setup_logging("pa.quality.validator")

# Limites para "suspeito" — biologicamente possível mas improvável
_PAS_SUSPEITO_MIN = 70   # abaixo disso, choque grave
_PAS_SUSPEITO_MAX = 250  # acima disso, crise hipertensiva grave
_PAD_SUSPEITO_MIN = 40
_PAD_SUSPEITO_MAX = 150


@dataclass
class ResultadoValidacao:
    pas: Optional[float]
    pad: Optional[float]
    status: str           # "valido" | "invalido" | "suspeito"
    motivo: Optional[str] # descrição do problema, se houver


def validar_pa(valor: str, idade: float = None) -> ResultadoValidacao:
    """
    Valida uma string de pressão arterial no formato "PAS/PAD".

    Args:
        valor: string como "160/90" ou "160/90 mmHg"
        idade: idade do paciente (ajusta threshold para >=65 anos)

    Returns:
        ResultadoValidacao com pas, pad, status e motivo
    """
    if pd.isna(valor) or str(valor).strip() in ("", "None", "nan", "NaN", "NULL"):
        return ResultadoValidacao(None, None, "invalido", "valor ausente ou nulo")

    valor_str = str(valor).strip().replace("mmHg", "").strip()

    partes = valor_str.split("/")
    if len(partes) != 2:
        return ResultadoValidacao(None, None, "invalido", f"formato inesperado: '{valor}'")

    try:
        pas = float(partes[0].strip())
        pad = float(partes[1].strip())
    except ValueError:
        return ResultadoValidacao(None, None, "invalido", f"não numérico: '{valor}'")

    # Validação de range absoluto (limites fisiológicos impossíveis)
    if not (settings.PA_PAS_MIN <= pas <= settings.PA_PAS_MAX):
        return ResultadoValidacao(
            pas, pad, "invalido",
            f"PAS={pas} fora do range válido [{settings.PA_PAS_MIN}-{settings.PA_PAS_MAX}]"
        )
    if not (settings.PA_PAD_MIN <= pad <= settings.PA_PAD_MAX):
        return ResultadoValidacao(
            pas, pad, "invalido",
            f"PAD={pad} fora do range válido [{settings.PA_PAD_MIN}-{settings.PA_PAD_MAX}]"
        )
    if pas <= pad:
        return ResultadoValidacao(
            pas, pad, "invalido",
            f"PAS={pas} deve ser maior que PAD={pad}"
        )

    # Faixa "suspeita" — válida fisiologicamente mas extrema
    suspeito = False
    motivo_suspeito = []
    if pas < _PAS_SUSPEITO_MIN or pas > _PAS_SUSPEITO_MAX:
        suspeito = True
        motivo_suspeito.append(f"PAS={pas} extrema")
    if pad < _PAD_SUSPEITO_MIN or pad > _PAD_SUSPEITO_MAX:
        suspeito = True
        motivo_suspeito.append(f"PAD={pad} extrema")

    if suspeito:
        return ResultadoValidacao(
            pas, pad, "suspeito",
            "; ".join(motivo_suspeito)
        )

    return ResultadoValidacao(pas, pad, "valido", None)


def classificar_pa(pas: float, pad: float, idade: float = None) -> str:
    """
    Classifica a pressão arterial segundo as diretrizes brasileiras.
    Ajusta o threshold de descontrole para idosos (>=65 anos): PAS >150 ou PAD >90.

    Returns:
        "Ótima/Normal" | "Pré-Hipertensão" | "Hipertensão" | "Desconhecido"
    """
    if pd.isna(pas) or pd.isna(pad):
        return "Desconhecido"

    is_idoso = idade is not None and not pd.isna(idade) and float(idade) >= 65

    if is_idoso:
        if pas <= 150 and pad <= 90:
            return "Ótima/Normal (Idoso)"
        return "Hipertensão"

    if pas < 120 and pad < 80:
        return "Ótima/Normal"
    if pas < 140 and pad < 90:
        return "Pré-Hipertensão"
    return "Hipertensão"


def processar_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica validação e classificação a um DataFrame com coluna
    'nu_medicao_pressao_arterial'. Adiciona colunas:
      - PAS, PAD (float)
      - status_validacao ("valido" | "invalido" | "suspeito")
      - motivo_validacao (texto explicativo ou None)
      - classificacao_pa
      - descontrole_pressorico (0 ou 1)

    Args:
        df: DataFrame com pelo menos 'nu_medicao_pressao_arterial'
            e opcionalmente 'idade' ou 'faixa_etaria'

    Returns:
        DataFrame com as colunas adicionadas
    """
    logger.info(f"Processando {len(df):,} registros de PA...")

    df = df.copy()
    df["nu_medicao_pressao_arterial"] = df["nu_medicao_pressao_arterial"].astype(str)

    idade_col = df.get("idade")

    resultados = df["nu_medicao_pressao_arterial"].apply(
        lambda v: validar_pa(v)
    )

    df["PAS"] = [r.pas for r in resultados]
    df["PAD"] = [r.pad for r in resultados]
    df["status_validacao"] = [r.status for r in resultados]
    df["motivo_validacao"] = [r.motivo for r in resultados]

    # Classificação apenas nos registros válidos ou suspeitos (têm PAS/PAD)
    mask_com_valores = df["PAS"].notna()
    df["classificacao_pa"] = "Desconhecido"
    df["descontrole_pressorico"] = 0

    if mask_com_valores.any():
        idades = idade_col if idade_col is not None else pd.Series([None] * len(df))
        df.loc[mask_com_valores, "classificacao_pa"] = df[mask_com_valores].apply(
            lambda row: classificar_pa(row["PAS"], row["PAD"], idades.iloc[row.name] if idades is not None else None),
            axis=1,
        )
        df.loc[mask_com_valores, "descontrole_pressorico"] = (
            df.loc[mask_com_valores, "classificacao_pa"] == "Hipertensão"
        ).astype(int)

    validos = (df["status_validacao"] == "valido").sum()
    suspeitos = (df["status_validacao"] == "suspeito").sum()
    invalidos = (df["status_validacao"] == "invalido").sum()
    total = len(df)

    logger.info(
        f"Validação concluída: {validos:,} válidos ({validos/total*100:.1f}%) | "
        f"{suspeitos:,} suspeitos | {invalidos:,} inválidos"
    )

    return df
