"""
Pipeline de treinamento — Controle Glicêmico em Diabéticos.

Modelo: RandomForestClassifier (target: controlado=1, descontrolado=0)
Validação: TimeSeriesSplit (treina no passado, testa no futuro)
Fonte: dashboard.mv_dm_hemoglobina

Uso:
    from app.modules.diabetes.ml.pipeline import treinar_modelo
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
    roc_auc_score,
    f1_score,
    precision_score,
    recall_score,
    accuracy_score,
)
from sklearn.model_selection import TimeSeriesSplit

from app.core.database import engine
from app.core.logging_config import setup_logging
from app.shared.controle_processamento import (
    criar_tabela_controle,
    registrar_inicio,
    registrar_fim,
)

logger = setup_logging("dm.ml.pipeline")

# ── Configurações ─────────────────────────────────────────────────────────────

MODEL_DIR  = Path(__file__).parent.parent.parent.parent.parent.parent / "models"
MODEL_PATH = MODEL_DIR / "dm_controle_rf.joblib"
META_PATH  = MODEL_DIR / "dm_controle_meta.json"

MODEL_DIR.mkdir(exist_ok=True)

# Features usadas no treino e na predição (ordem importa)
FEATURES = [
    "idade",
    "co_dim_sexo",
    "hba1c",
    "st_hipertensao",
    "st_doenca_cardiaca",
    "st_insuf_cardiaca",
    "st_infarto",
    "st_problema_rins",
    "st_avc",
    "st_fumante",
    "st_alcool",
    "st_doenca_respiratoria",
    "st_cancer",
]

# target binário derivado de controle_glicemico
TARGET = "controlado"

# ── Carga de dados ────────────────────────────────────────────────────────────

_SQL = """
SELECT
    -- chave temporal para TimeSeriesSplit (ex: 202403)
    ano * 100 + mes                                                AS co_dim_tempo,
    idade_no_exame                                                 AS idade,
    CASE sg_sexo WHEN 'M' THEN 1 WHEN 'F' THEN 3 ELSE 1 END      AS co_dim_sexo,
    hba1c,
    COALESCE(st_hipertensao,         0) AS st_hipertensao,
    COALESCE(st_doenca_cardiaca,     0) AS st_doenca_cardiaca,
    COALESCE(st_insuf_cardiaca,      0) AS st_insuf_cardiaca,
    COALESCE(st_infarto,             0) AS st_infarto,
    COALESCE(st_problema_rins,       0) AS st_problema_rins,
    COALESCE(st_avc,                 0) AS st_avc,
    COALESCE(st_fumante,             0) AS st_fumante,
    COALESCE(st_alcool,              0) AS st_alcool,
    COALESCE(st_doenca_respiratoria, 0) AS st_doenca_respiratoria,
    COALESCE(st_cancer,              0) AS st_cancer,
    CASE WHEN controle_glicemico = 'Controlado' THEN 1 ELSE 0 END AS controlado
FROM dashboard.mv_dm_hemoglobina
WHERE controle_glicemico IS NOT NULL
  AND hba1c IS NOT NULL
  AND idade_no_exame IS NOT NULL
  AND sg_sexo IS NOT NULL
  AND ano IS NOT NULL
"""


def _carregar_dados() -> pd.DataFrame:
    logger.info("Carregando dados de mv_dm_hemoglobina...")
    df = pd.read_sql(_SQL, engine)
    logger.info(f"  {len(df):,} registros carregados.")
    return df


# ── Treinamento ───────────────────────────────────────────────────────────────

def treinar_modelo(n_splits: int = 5) -> dict:
    """
    Treina RandomForestClassifier com TimeSeriesSplit por co_dim_tempo.

    Target: controle_glicemico = 'Controlado' (1) vs 'Descontrolado' (0).
    TimeSeriesSplit garante sem vazamento temporal.

    Retorna dict com métricas e importâncias das features.
    """
    # Registra início no controle de processamento
    criar_tabela_controle()
    co_seq = registrar_inicio("treino_dm", ds_modelo="dm_controle_rf")

    try:
        df = _carregar_dados()

        # Ordena por tempo — obrigatório para TimeSeriesSplit
        df = df.sort_values("co_dim_tempo").reset_index(drop=True)

        X = df[FEATURES].values
        y = df[TARGET].values

        logger.info(f"  Target: {y.sum():,} controlados / {len(y):,} total "
                    f"({y.mean()*100:.1f}%)")

        tscv = TimeSeriesSplit(n_splits=n_splits)

        auc_scores, f1_scores, prec_scores, rec_scores, acc_scores = [], [], [], [], []
        importancias_acum = np.zeros(len(FEATURES))

        for fold, (train_idx, test_idx) in enumerate(tscv.split(X), 1):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            clf = RandomForestClassifier(
                n_estimators=200,
                max_depth=12,
                min_samples_leaf=20,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            )
            clf.fit(X_train, y_train)

            y_prob = clf.predict_proba(X_test)[:, 1]
            y_pred = (y_prob >= 0.5).astype(int)

            auc  = roc_auc_score(y_test, y_prob)
            f1   = f1_score(y_test, y_pred, zero_division=0)
            prec = precision_score(y_test, y_pred, zero_division=0)
            rec  = recall_score(y_test, y_pred, zero_division=0)
            acc  = accuracy_score(y_test, y_pred)

            auc_scores.append(auc)
            f1_scores.append(f1)
            prec_scores.append(prec)
            rec_scores.append(rec)
            acc_scores.append(acc)
            importancias_acum += clf.feature_importances_

            logger.info(f"  Fold {fold}: AUC={auc:.3f} F1={f1:.3f} "
                        f"Prec={prec:.3f} Rec={rec:.3f}")

        # Treino final com todos os dados
        logger.info("Treinando modelo final com todos os dados...")
        clf_final = RandomForestClassifier(
            n_estimators=300,
            max_depth=12,
            min_samples_leaf=20,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        clf_final.fit(X, y)

        importancias_medias = (importancias_acum / n_splits).tolist()

        metricas = {
            "roc_auc":  {"media": float(np.mean(auc_scores)),  "std": float(np.std(auc_scores))},
            "f1":       {"media": float(np.mean(f1_scores)),   "std": float(np.std(f1_scores))},
            "precisao": {"media": float(np.mean(prec_scores)), "std": float(np.std(prec_scores))},
            "recall":   {"media": float(np.mean(rec_scores)),  "std": float(np.std(rec_scores))},
            "acuracia": {"media": float(np.mean(acc_scores)),  "std": float(np.std(acc_scores))},
        }

        feature_importances = dict(zip(FEATURES, importancias_medias))

        meta = {
            "treinado_em":        datetime.now().isoformat(),
            "total_registros":    int(len(df)),
            "total_controlados":  int(y.sum()),
            "prevalencia_treino": round(float(y.mean()) * 100, 1),
            "features":           FEATURES,
            "n_splits_cv":        n_splits,
            "metricas":           metricas,
            "feature_importances": feature_importances,
        }

        joblib.dump(clf_final, MODEL_PATH)
        META_PATH.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

        logger.info(f"Modelo salvo em: {MODEL_PATH}")
        logger.info(f"AUC médio: {metricas['roc_auc']['media']:.3f} "
                    f"(±{metricas['roc_auc']['std']:.3f})")

        # Registra sucesso no controle
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
