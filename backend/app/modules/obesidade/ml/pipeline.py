"""
Pipeline de treinamento — Classificação de IMC (6 classes OMS).

Modelo: RandomForestClassifier (multiclasse)
Validação: TimeSeriesSplit (treina no passado, testa no futuro)
Fonte: dashboard.mv_obesidade

Uso:
    from app.modules.obesidade.ml.pipeline import treinar_modelo
    resultado = treinar_modelo()
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.preprocessing import LabelEncoder

from app.core.database import engine
from app.core.logging_config import setup_logging
from app.shared.controle_processamento import (
    criar_tabela_controle,
    registrar_fim,
    registrar_inicio,
)

logger = setup_logging("ob.ml.pipeline")

# ── Configurações ─────────────────────────────────────────────────────────────

MODEL_DIR  = Path(__file__).parent.parent.parent.parent.parent.parent / "models"
MODEL_PATH = MODEL_DIR / "ob_imc_rf.joblib"
META_PATH  = MODEL_DIR / "ob_imc_meta.json"
ENCODER_PATH = MODEL_DIR / "ob_imc_encoder.joblib"

MODEL_DIR.mkdir(exist_ok=True)

# Features — mesma lógica do projeto obesidade original
FEATURES = [
    "peso_kg",
    "altura_m",
    "imc",
    "idade",
    "co_dim_sexo",
    "st_hipertensao",
    "st_diabete",
    "st_fumante",
    "st_alcool",
    "st_doenca_cardiaca",
    "st_doenca_respiratoria",
]

TARGET = "classificacao_imc"

# Ordem canônica das classes (para probabilidades consistentes)
CLASSES = ["Baixo Peso", "Normal", "Sobrepeso", "Obesidade I", "Obesidade II", "Obesidade III"]

# ── Carga de dados ────────────────────────────────────────────────────────────

_SQL = """
SELECT
    ano * 100 + mes                                                AS co_dim_tempo,
    peso_kg,
    altura_m,
    imc,
    idade_no_exame                                                 AS idade,
    co_dim_sexo,
    COALESCE(st_hipertensao,       0)                             AS st_hipertensao,
    COALESCE(st_diabete,           0)                             AS st_diabete,
    COALESCE(st_fumante,           0)                             AS st_fumante,
    COALESCE(st_alcool,            0)                             AS st_alcool,
    COALESCE(st_doenca_cardiaca,   0)                             AS st_doenca_cardiaca,
    COALESCE(st_doenca_respiratoria, 0)                           AS st_doenca_respiratoria,
    classificacao_imc
FROM dashboard.mv_obesidade
WHERE classificacao_imc IS NOT NULL
  AND peso_kg IS NOT NULL
  AND altura_m IS NOT NULL
  AND imc IS NOT NULL
  AND idade_no_exame IS NOT NULL
  AND co_dim_sexo IS NOT NULL
  AND ano IS NOT NULL
"""


def _carregar_dados() -> pd.DataFrame:
    logger.info("Carregando dados de mv_obesidade...")
    df = pd.read_sql(_SQL, engine)
    logger.info(f"  {len(df):,} registros carregados.")
    return df


# ── Treinamento ───────────────────────────────────────────────────────────────

def treinar_modelo(n_splits: int = 5) -> dict:
    """
    Treina RandomForestClassifier multiclasse com TimeSeriesSplit por co_dim_tempo.

    Target: classificacao_imc (6 classes OMS).
    TimeSeriesSplit garante sem vazamento temporal.

    Retorna dict com métricas e importâncias das features.
    """
    criar_tabela_controle()
    co_seq = registrar_inicio("treino_obesidade", ds_modelo="ob_imc_rf")

    try:
        df = _carregar_dados()

        df = df.sort_values("co_dim_tempo").reset_index(drop=True)

        # Encode das classes para inteiros (preserva ordem canônica)
        le = LabelEncoder()
        le.classes_ = np.array(CLASSES)
        # Registros com classe fora da lista canônica são removidos
        df = df[df[TARGET].isin(CLASSES)].copy()
        y = le.transform(df[TARGET].values)
        X = df[FEATURES].values

        dist = df[TARGET].value_counts().to_dict()
        logger.info(f"  Distribuição: {dist}")
        logger.info(f"  Total válido: {len(df):,}")

        tscv = TimeSeriesSplit(n_splits=n_splits)

        acc_scores, f1_scores, prec_scores, rec_scores = [], [], [], []
        importancias_acum = np.zeros(len(FEATURES))

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            clf = RandomForestClassifier(
                n_estimators=200,
                max_depth=15,
                min_samples_leaf=10,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
            clf.fit(X_train, y_train)
            y_pred = clf.predict(X_test)

            acc  = accuracy_score(y_test, y_pred)
            f1   = f1_score(y_test, y_pred, average="macro", zero_division=0)
            prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
            rec  = recall_score(y_test, y_pred, average="macro", zero_division=0)

            acc_scores.append(acc)
            f1_scores.append(f1)
            prec_scores.append(prec)
            rec_scores.append(rec)
            importancias_acum += clf.feature_importances_

            logger.info(f"  Fold {fold}: Acc={acc:.3f} F1={f1:.3f} Prec={prec:.3f} Rec={rec:.3f}")

        # Treino final com todos os dados
        logger.info("Treinando modelo final com todos os dados...")
        clf_final = RandomForestClassifier(
            n_estimators=300,
            max_depth=15,
            min_samples_leaf=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        clf_final.fit(X, y)

        # Métricas por classe no conjunto completo
        y_pred_all = clf_final.predict(X)
        report = classification_report(
            y, y_pred_all, target_names=CLASSES, output_dict=True, zero_division=0
        )
        metricas_por_classe = [
            {
                "classe": cls,
                "precisao": round(report[cls]["precision"], 4),
                "recall": round(report[cls]["recall"], 4),
                "f1": round(report[cls]["f1-score"], 4),
                "suporte": int(report[cls]["support"]),
            }
            for cls in CLASSES
            if cls in report
        ]

        importancias_medias = (importancias_acum / n_splits).tolist()

        metricas = {
            "acuracia":  {"media": float(np.mean(acc_scores)),  "std": float(np.std(acc_scores))},
            "f1_macro":  {"media": float(np.mean(f1_scores)),   "std": float(np.std(f1_scores))},
            "precisao":  {"media": float(np.mean(prec_scores)), "std": float(np.std(prec_scores))},
            "recall":    {"media": float(np.mean(rec_scores)),  "std": float(np.std(rec_scores))},
        }

        feature_importances = dict(zip(FEATURES, importancias_medias))

        meta = {
            "treinado_em":        datetime.now().isoformat(),
            "total_registros":    int(len(df)),
            "distribuicao_treino": {k: int(v) for k, v in dist.items()},
            "features":           FEATURES,
            "classes":            CLASSES,
            "n_splits_cv":        n_splits,
            "metricas":           metricas,
            "metricas_por_classe": metricas_por_classe,
            "feature_importances": feature_importances,
        }

        joblib.dump(clf_final, MODEL_PATH)
        joblib.dump(le, ENCODER_PATH)
        META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info(f"Modelo salvo em: {MODEL_PATH}")
        logger.info(f"Acurácia média: {metricas['acuracia']['media']:.3f} "
                    f"(±{metricas['acuracia']['std']:.3f})")

        registrar_fim(
            co_seq,
            st_status="concluido",
            ds_metricas=metricas,
            qt_registros=int(len(df)),
        )

        return meta

    except Exception as e:
        registrar_fim(co_seq, st_status="erro", ds_erro=str(e))
        raise
