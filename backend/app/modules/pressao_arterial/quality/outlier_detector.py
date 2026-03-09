"""
Detecção estatística de outliers em medições de pressão arterial.

Dois métodos complementares:
  1. IQR populacional — detecta outliers em relação à população toda
  2. Z-score individual — detecta medições atípicas no histórico de um paciente

Outliers são MARCADOS, não removidos. São enviados para auditoria humana.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import pandas as pd
import numpy as np
from scipy import stats

from app.core.config import settings
from app.core.logging_config import setup_logging

logger = setup_logging("pa.quality.outlier_detector")


@dataclass
class OutlierInfo:
    co_seq_medicao: Optional[int]
    co_seq_cidadao: Optional[int]
    nu_pa_original: str
    pas_valor: Optional[float]
    pad_valor: Optional[float]
    tp_outlier: str   # 'iqr_populacional' | 'zscore_individual'
    ds_motivo: str
    vl_zscore: Optional[float]


def detectar_outliers_populacao(df: pd.DataFrame) -> tuple[pd.DataFrame, list[OutlierInfo]]:
    """
    Detecta outliers populacionais usando o método IQR (Interquartile Range).

    Lógica:
        Q1 - 1.5 * IQR  <  valor  <  Q3 + 1.5 * IQR  →  normal
        Fora disso                                      →  outlier

    Trabalha apenas com registros com status_validacao != "invalido"
    (ou seja, inclui suspeitos que passaram na validação fisiológica).

    Args:
        df: DataFrame processado pelo validator (com colunas PAS, PAD, status_validacao)

    Returns:
        Tupla (df_com_flag, lista_de_outliers)
        - df_com_flag: DataFrame com coluna 'outlier_populacional' (bool)
        - lista_de_outliers: lista de OutlierInfo para gravação na auditoria
    """
    df = df.copy()
    df["outlier_populacional"] = False
    outliers: list[OutlierInfo] = []

    mascara_validos = df["status_validacao"].isin(["valido", "suspeito"]) & df["PAS"].notna()
    df_validos = df[mascara_validos]

    if df_validos.empty:
        logger.warning("Nenhum registro válido para detecção de outliers populacionais.")
        return df, outliers

    fator = settings.OUTLIER_IQR_FACTOR

    for coluna in ["PAS", "PAD"]:
        q1 = df_validos[coluna].quantile(0.25)
        q3 = df_validos[coluna].quantile(0.75)
        iqr = q3 - q1
        limite_inf = q1 - fator * iqr
        limite_sup = q3 + fator * iqr

        mascara_outlier = (
            mascara_validos &
            ((df[coluna] < limite_inf) | (df[coluna] > limite_sup))
        )

        df.loc[mascara_outlier, "outlier_populacional"] = True

        for _, row in df[mascara_outlier].iterrows():
            outliers.append(OutlierInfo(
                co_seq_medicao=row.get("co_seq_medicao"),
                co_seq_cidadao=row.get("co_seq_cidadao"),
                nu_pa_original=row.get("nu_medicao_pressao_arterial", ""),
                pas_valor=row.get("PAS"),
                pad_valor=row.get("PAD"),
                tp_outlier="iqr_populacional",
                ds_motivo=(
                    f"{coluna}={row[coluna]:.1f} fora do intervalo IQR "
                    f"[{limite_inf:.1f} - {limite_sup:.1f}] "
                    f"(Q1={q1:.1f}, Q3={q3:.1f}, IQR={iqr:.1f})"
                ),
                vl_zscore=None,
            ))

    total_outliers = df["outlier_populacional"].sum()
    logger.info(
        f"IQR populacional: {total_outliers:,} outliers detectados "
        f"em {len(df_validos):,} registros válidos "
        f"({total_outliers/len(df_validos)*100:.2f}%)"
    )
    return df, outliers


def detectar_outliers_por_paciente(
    df: pd.DataFrame,
    col_cidadao: str = "co_seq_cidadao",
    min_medicoes: int = 3,
) -> tuple[pd.DataFrame, list[OutlierInfo]]:
    """
    Detecta outliers individuais por paciente usando Z-score.

    Para cada cidadão com pelo menos `min_medicoes` medições válidas,
    calcula o Z-score de cada medição em relação ao histórico daquele cidadão.
    Medições com |Z| > threshold são marcadas como outlier.

    Args:
        df: DataFrame com colunas PAS, PAD, col_cidadao, status_validacao
        col_cidadao: nome da coluna de ID do cidadão
        min_medicoes: mínimo de medições para calcular z-score (< isso, não analisa)

    Returns:
        Tupla (df_com_flag, lista_de_outliers)
    """
    df = df.copy()
    df["outlier_individual"] = False
    outliers: list[OutlierInfo] = []

    if col_cidadao not in df.columns:
        logger.warning(f"Coluna '{col_cidadao}' não encontrada. Pulando z-score individual.")
        return df, outliers

    threshold = settings.OUTLIER_ZSCORE_THRESHOLD
    mascara_validos = df["status_validacao"].isin(["valido", "suspeito"]) & df["PAS"].notna()

    grupos = df[mascara_validos].groupby(col_cidadao)

    for cidadao_id, grupo in grupos:
        if len(grupo) < min_medicoes:
            continue

        for coluna in ["PAS", "PAD"]:
            valores = grupo[coluna].dropna()
            if valores.std() == 0:
                continue

            zscores = np.abs(stats.zscore(valores))
            indices_outlier = valores.index[zscores > threshold]

            for idx in indices_outlier:
                df.loc[idx, "outlier_individual"] = True
                row = df.loc[idx]
                z = zscores[valores.index.get_loc(idx)]
                outliers.append(OutlierInfo(
                    co_seq_medicao=row.get("co_seq_medicao"),
                    co_seq_cidadao=cidadao_id,
                    nu_pa_original=row.get("nu_medicao_pressao_arterial", ""),
                    pas_valor=row.get("PAS"),
                    pad_valor=row.get("PAD"),
                    tp_outlier="zscore_individual",
                    ds_motivo=(
                        f"{coluna}={row[coluna]:.1f} — Z-score={z:.2f} "
                        f"(threshold={threshold}, média_histórica={valores.mean():.1f}, "
                        f"σ={valores.std():.1f}, n={len(grupo)} medições)"
                    ),
                    vl_zscore=round(float(z), 4),
                ))

    total = df["outlier_individual"].sum()
    cidadaos_analisados = sum(1 for _, g in grupos if len(g) >= min_medicoes)
    logger.info(
        f"Z-score individual: {total:,} outliers em {cidadaos_analisados:,} cidadãos analisados"
    )
    return df, outliers


def executar_pipeline_outliers(df: pd.DataFrame) -> tuple[pd.DataFrame, list[OutlierInfo]]:
    """
    Executa os dois detectores em sequência e consolida os resultados.

    Returns:
        (df_final, todos_os_outliers)
        - df_final tem colunas 'outlier_populacional', 'outlier_individual', 'eh_outlier'
        - todos_os_outliers é a lista consolidada para gravar na auditoria
    """
    logger.info("Iniciando pipeline de detecção de outliers...")

    df, outliers_pop = detectar_outliers_populacao(df)
    df, outliers_ind = detectar_outliers_por_paciente(df)

    df["eh_outlier"] = df["outlier_populacional"] | df["outlier_individual"]
    todos = outliers_pop + outliers_ind

    logger.info(
        f"Pipeline concluído: {len(todos):,} registros de outlier "
        f"({df['eh_outlier'].sum():,} registros únicos afetados)"
    )
    return df, todos
