# Modelos de Machine Learning

## Visão Geral

A plataforma possui **3 modelos preditivos**, todos usando `RandomForestClassifier` do scikit-learn com validação temporal via `TimeSeriesSplit`.

| Modelo | Target | Arquivo | Meta |
|--------|--------|---------|------|
| **Risco de HAS** | `st_hipertensao_arterial` (0/1) | `models/ha_risk_rf.joblib` | `models/ha_risk_meta.json` |
| **Controle Glicêmico** | `controlado` (derivado de `controle_glicemico`) | `models/dm_controle_rf.joblib` | `models/dm_controle_meta.json` |
| **Classificação de IMC** | 6 classes OMS (Baixo Peso → Obesidade III) | `models/ob_imc_rf.joblib` | `models/ob_imc_meta.json` |

---

## Modelo 1: Risco de Hipertensão Arterial (HAS)

**Código:** `app/modules/pressao_arterial/ml/pipeline.py`

### Features

| Feature | Tipo | Descrição |
|---------|------|-----------|
| `idade` | Contínua | Idade em anos (calculada na view) |
| `co_dim_sexo` | Categórica (1=M, 3=F) | Sexo do cidadão |
| `st_diabetes` | Binária (0/1) | Diabetes mellitus |
| `st_fumante` | Binária (0/1) | Fumante |
| `st_alcool` | Binária (0/1) | Uso de álcool |
| `st_outra_droga` | Binária (0/1) | Uso de outras drogas |
| `st_doenca_cardiaca` | Binária (0/1) | Doença cardíaca |
| `st_problema_rins` | Binária (0/1) | Doença renal |
| `st_avc` | Binária (0/1) | AVC/Derrame |
| `st_infarto` | Binária (0/1) | Infarto |
| `st_doenca_respiratoria` | Binária (0/1) | Doença respiratória crônica |
| `st_cancer` | Binária (0/1) | Câncer |
| `st_hanseniase` | Binária (0/1) | Hanseníase |
| `st_tuberculose` | Binária (0/1) | Tuberculose |

### Target

- `st_hipertensao_arterial`: 1 = hipertenso, 0 = não hipertenso
- Fonte: `dashboard.mv_pa_cadastros`

### Hiperparâmetros

```python
RandomForestClassifier(
    n_estimators=300,     # árvores na floresta
    max_depth=12,         # profundidade máxima
    min_samples_leaf=20,  # mínimo amostras por folha
    class_weight="balanced",  # ajuste para classes desbalanceadas
    random_state=42,
    n_jobs=-1,            # usa todos os cores
)
```

### Validação

- **Método:** `TimeSeriesSplit(n_splits=5)` — treina em dados mais antigos, valida em mais recentes
- **Razão:** Evita vazamento temporal (data leakage). O modelo nunca "vê o futuro" durante o treino
- **Métricas:** ROC-AUC, F1, Precisão, Recall, Acurácia (média ± desvio padrão dos folds)

### Classificação de Risco

| Probabilidade | Nível | Cor |
|---------------|-------|-----|
| < 20% | Baixo | Verde |
| 20% – 35% | Moderado | Âmbar |
| > 35% | Alto | Vermelho |

### Como Treinar/Retreinar

```bash
# Via API (recomendado — roda em background)
curl -X POST http://localhost:8000/api/v1/pressao-arterial/modelo/treinar \
  -H "Authorization: Bearer <token>"

# Verificar status
curl http://localhost:8000/api/v1/pressao-arterial/modelo/status-treino \
  -H "Authorization: Bearer <token>"

# Verificar métricas após treino
curl http://localhost:8000/api/v1/pressao-arterial/modelo/info \
  -H "Authorization: Bearer <token>"
```

O treinamento leva ~2-5 minutos dependendo do volume de dados.

### Predição Individual

```bash
curl -X POST http://localhost:8000/api/v1/pressao-arterial/predizer-risco \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "idade": 55,
    "co_dim_sexo": 3,
    "st_diabetes": 1,
    "st_fumante": 0,
    "st_doenca_cardiaca": 1
  }'
```

Campos binários omitidos são tratados como `0` (não informado).

---

## Modelo 2: Controle Glicêmico em Diabéticos

**Código:** `app/modules/diabetes/ml/pipeline.py`

### Features

| Feature | Tipo | Descrição |
|---------|------|-----------|
| `idade` | Contínua | Idade na data do exame |
| `co_dim_sexo` | Categórica (1=M, 3=F) | Sexo |
| `hba1c` | Contínua | Valor da hemoglobina glicada (%) |
| `st_hipertensao` | Binária | Hipertensão arterial |
| `st_doenca_cardiaca` | Binária | Doença cardíaca |
| `st_insuf_cardiaca` | Binária | Insuficiência cardíaca |
| `st_infarto` | Binária | Infarto |
| `st_problema_rins` | Binária | Doença renal |
| `st_avc` | Binária | AVC |
| `st_fumante` | Binária | Fumante |
| `st_alcool` | Binária | Uso de álcool |
| `st_doenca_respiratoria` | Binária | Doença respiratória |
| `st_cancer` | Binária | Câncer |

### Target

- `controlado`: 1 = controlado, 0 = descontrolado
- Derivado de `controle_glicemico` na view `dashboard.mv_dm_hemoglobina`

### Critérios de Controle (SBD 2024)

| Grupo etário | HbA1c controlada | HbA1c descontrolada |
|-------------|------------------|---------------------|
| Adultos (18-64) | < 7.0% | ≥ 7.0% |
| Idosos (65-79) | < 7.5% | ≥ 7.5% |
| Idosos (80+) | < 8.0% | ≥ 8.0% |

### Como Treinar/Retreinar

```bash
# Via API
curl -X POST http://localhost:8000/api/v1/diabetes/modelo/treinar \
  -H "Authorization: Bearer <token>"

# Verificar info
curl http://localhost:8000/api/v1/diabetes/modelo/info \
  -H "Authorization: Bearer <token>"
```

---

## Modelo 3: Classificação de IMC (Obesidade)

**Código:** `app/modules/obesidade/ml/pipeline.py`

### Features

| Feature | Tipo | Descrição |
|---------|------|-----------|
| `peso_kg` | Contínua | Peso em kilogramas |
| `altura_m` | Contínua | Altura em metros |
| `idade` | Contínua | Idade em anos |
| `co_dim_sexo` | Categórica (1=M, 3=F) | Sexo |
| `st_hipertensao` | Binária | Hipertensão arterial |
| `st_diabete` | Binária | Diabetes mellitus |
| `st_fumante` | Binária | Fumante |
| `st_alcool` | Binária | Uso de álcool |
| `st_doenca_cardiaca` | Binária | Doença cardíaca |
| `st_doenca_respiratoria` | Binária | Doença respiratória |

### Target — 6 Classes OMS

| Classe | IMC | Código |
|--------|-----|--------|
| Baixo Peso | < 18.5 | `baixo_peso` |
| Normal | 18.5 – 24.9 | `normal` |
| Sobrepeso | 25.0 – 29.9 | `sobrepeso` |
| Obesidade Grau I | 30.0 – 34.9 | `obesidade_1` |
| Obesidade Grau II | 35.0 – 39.9 | `obesidade_2` |
| Obesidade Grau III | ≥ 40.0 | `obesidade_3` |

> **Nota:** O IMC é sempre **recalculado** a partir de peso e altura brutos (`peso / altura²`), não usando o valor armazenado no e-SUS (que pode conter erros).

### Fonte de Dados

- View: `dashboard.mv_obesidade`
- Medições com peso e altura válidos (peso entre 20-300 kg, altura entre 0.5-2.5 m)

### Hiperparâmetros

```python
RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    min_samples_leaf=20,
    class_weight="balanced",   # ajuste para classes desbalanceadas
    random_state=42,
    n_jobs=-1,
)
```

### Validação

- **Método:** `TimeSeriesSplit(n_splits=5)` — mesmo padrão dos outros modelos
- **Métricas por classe:** Precisão, Recall e F1 para cada uma das 6 classes
- **Métricas gerais:** Acurácia geral, macro-F1

### Como Treinar/Retreinar

```bash
# Via API (roda em background)
curl -X POST http://localhost:8000/api/v1/obesidade/modelo/treinar \
  -H "Authorization: Bearer <token>"

# Verificar status
curl http://localhost:8000/api/v1/obesidade/modelo/status-treino \
  -H "Authorization: Bearer <token>"

# Verificar métricas
curl http://localhost:8000/api/v1/obesidade/modelo/info \
  -H "Authorization: Bearer <token>"
```

### Predição Individual

```bash
curl -X POST http://localhost:8000/api/v1/obesidade/predizer-imc \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "peso_kg": 95.0,
    "altura_m": 1.72,
    "idade": 45,
    "sexo": "M",
    "st_hipertensao": 1,
    "st_diabete": 0,
    "st_fumante": 0,
    "st_alcool": 0,
    "st_doenca_cardiaca": 0,
    "st_doenca_respiratoria": 0
  }'
```

**Resposta:**

```json
{
  "imc_calculado": 32.1,
  "classificacao_predita": "obesidade_1",
  "probabilidades": {
    "baixo_peso": 0.00,
    "normal": 0.01,
    "sobrepeso": 0.08,
    "obesidade_1": 0.72,
    "obesidade_2": 0.16,
    "obesidade_3": 0.03
  },
  "confianca": 0.72,
  "nivel_confianca": "alta"
}
```

---

## Artefatos dos Modelos

Os modelos treinados ficam em `backend/models/`:

```
models/
├── ha_risk_rf.joblib        # Modelo HAS serializado
├── ha_risk_meta.json        # Metadados: features, métricas, data
├── dm_controle_rf.joblib    # Modelo DM serializado
├── dm_controle_meta.json    # Metadados DM
├── ob_imc_rf.joblib         # Modelo Obesidade serializado
└── ob_imc_meta.json         # Metadados Obesidade
```

### Estrutura do meta.json

```json
{
  "treinado_em": "2026-03-06T19:30:00",
  "total_registros": 15000,
  "prevalencia_treino": 35.2,
  "features": ["idade", "co_dim_sexo", "..."],
  "n_splits_cv": 5,
  "metricas": {
    "roc_auc": {"media": 0.812, "std": 0.023},
    "f1": {"media": 0.745, "std": 0.031},
    "precisao": {"media": 0.780, "std": 0.028},
    "recall": {"media": 0.712, "std": 0.035},
    "acuracia": {"media": 0.790, "std": 0.020}
  },
  "feature_importances": {
    "idade": 0.35,
    "st_diabetes": 0.12
  }
}
```

---

## Boas Práticas

1. **Retreinar periodicamente** — após novos cadastros no e-SUS (recomendado: mensal)
2. **Dar REFRESH nas views antes** — o modelo treina sobre as views materializadas
3. **Verificar métricas** — AUC < 0.7 indica modelo fraco, investigue a qualidade dos dados
4. **Não usar em decisão clínica** — os modelos são preditivos populacionais, não diagnósticos individuais
5. **Ordem correta:** REFRESH views → normalização de bairros → treinamento dos modelos
