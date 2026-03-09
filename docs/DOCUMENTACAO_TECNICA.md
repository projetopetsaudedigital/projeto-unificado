# Documentação Técnica — Plataforma de Saúde Pública
## Guia completo de arquivos, funções e como modificar o sistema

> **Para quem é este documento:** Desenvolvedores que vão manter, estender ou entender o código da plataforma. Cobre backend (FastAPI/Python), frontend (React) e banco de dados (PostgreSQL).

---

## ÍNDICE

1. [Visão Geral da Arquitetura](#1-visão-geral-da-arquitetura)
2. [Backend — Núcleo do Sistema](#2-backend--núcleo-do-sistema)
3. [Backend — Módulo Hipertensão (HAS)](#3-backend--módulo-hipertensão-has)
4. [Backend — Módulo Diabetes (DM)](#4-backend--módulo-diabetes-dm)
5. [Backend — Módulo Obesidade (OB)](#5-backend--módulo-obesidade-ob)
6. [Banco de Dados — Views Materializadas](#6-banco-de-dados--views-materializadas)
7. [Scripts de Setup e Manutenção](#7-scripts-de-setup-e-manutenção)
8. [Frontend — Estrutura e Roteamento](#8-frontend--estrutura-e-roteamento)
9. [Frontend — Módulo Hipertensão](#9-frontend--módulo-hipertensão)
10. [Frontend — Módulo Diabetes](#10-frontend--módulo-diabetes)
11. [Frontend — Módulo Obesidade](#11-frontend--módulo-obesidade)
12. [Frontend — Componentes e Utilitários](#12-frontend--componentes-e-utilitários)
13. [Como Adicionar um Novo Módulo](#13-como-adicionar-um-novo-módulo)
14. [Como Modificar um Modelo de ML](#14-como-modificar-um-modelo-de-ml)
15. [Variáveis de Ambiente e Configuração](#15-variáveis-de-ambiente-e-configuração)

---

## 1. Visão Geral da Arquitetura

```
plataforma-saude/
├── backend/                  ← API REST (FastAPI + Python)
│   ├── main.py               ← Entry point da aplicação
│   ├── app/
│   │   ├── core/             ← Configuração, banco de dados
│   │   ├── auth/             ← JWT, login, usuários
│   │   ├── modules/          ← 3 módulos clínicos
│   │   │   ├── pressao_arterial/
│   │   │   ├── diabetes/
│   │   │   └── obesidade/
│   │   └── shared/           ← Utilitários compartilhados
│   ├── sql/                  ← DDL das views PostgreSQL
│   ├── scripts/              ← Setup, normalização, migração
│   └── models/               ← Modelos ML treinados (.joblib)
│
└── frontend/                 ← SPA (React 19 + Vite)
    └── src/
        ├── App.jsx            ← Roteamento e layout
        ├── contexts/          ← AuthContext (JWT)
        ├── api/               ← Clientes HTTP
        ├── components/        ← Componentes reutilizáveis
        └── pages/             ← 15 páginas da aplicação
```

### Fluxo de uma requisição típica

```
Usuário clica em "Painel"
    → React Router → pages/Painel.jsx
    → useQuery(['kpis']) → api/pressaoArterial.js → GET /api/v1/pressao-arterial/kpis
    → FastAPI → routes/analytics.py → analytics/kpis.py
    → execute_query(SQL) → PostgreSQL (dashboard.mv_pa_cadastros)
    → JSON retorna → Recharts renderiza gráfico
```

### Modo de banco de dados

A plataforma suporta dois modos, configurável via `.env`:

| Modo | `DB_MODE` | Descrição |
|------|-----------|-----------|
| FDW | `fdw` | Dois bancos separados: PEC (somente leitura) e Admin (leitura/escrita) |
| Single | `single` | Um único banco com schemas diferentes (`pec.*` e `dashboard.*`) |

---

## 2. Backend — Núcleo do Sistema

### `backend/main.py`

**O que faz:** Ponto de entrada da aplicação. Inicializa o FastAPI, configura CORS e registra todos os routers.

```python
# Estrutura principal
app = FastAPI(title="Plataforma de Saúde Pública", ...)

# CORS — permite o frontend (localhost:5173) chamar a API
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)

# Cada módulo tem seu próprio prefixo de rota
app.include_router(auth_router,    prefix="/api/v1/auth")
app.include_router(pa_router,      prefix="/api/v1/pressao-arterial")
app.include_router(diabetes_router,prefix="/api/v1/diabetes")
app.include_router(ob_router,      prefix="/api/v1/obesidade")
```

**Como adicionar um novo módulo:** Crie o router no módulo e adicione `app.include_router(novo_router, prefix="/api/v1/novo-modulo")` aqui.

---

### `backend/app/core/config.py`

**O que faz:** Centraliza toda a configuração via variáveis de ambiente usando Pydantic `BaseSettings`. Valida os valores ao iniciar.

```python
class Settings(BaseSettings):
    # Modo do banco de dados
    DB_MODE: str = "fdw"           # "fdw" ou "single"

    # Banco PEC (e-SUS, somente leitura)
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str                   # ex: "pet_saude"

    # Banco Admin (escrita — apenas no modo FDW)
    ADMIN_DB_HOST: str = ""
    ADMIN_DB_NAME: str = ""

    # JWT
    JWT_SECRET_KEY: str            # Gere com: openssl rand -hex 32
    JWT_EXPIRE_HOURS: int = 8

    # Detecção de outliers
    OUTLIER_ZSCORE_THRESHOLD: float = 3.0
    OUTLIER_IQR_FACTOR: float = 1.5
```

**Para adicionar uma nova configuração:** Adicione o campo com tipo e valor padrão. Ele será lido automaticamente do arquivo `.env`.

---

### `backend/app/core/database.py`

**O que faz:** Gerencia as conexões com o PostgreSQL. Expõe a função `execute_query()` usada por todos os módulos de analytics.

```python
# Função principal — usada em TODO o backend
def execute_query(sql: str, params: dict) -> list[dict]:
    """
    Executa uma query SQL e retorna lista de dicionários.
    Faz commit automático (adequado para SELECT e INSERT/UPDATE simples).
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        conn.commit()
        return [dict(row) for row in result]

# Exemplo de uso em analytics:
rows = execute_query(
    "SELECT COUNT(*) as total FROM dashboard.mv_pa_cadastros WHERE st_hipertensao_arterial = 1",
    {}
)
total = rows[0]["total"]
```

**Importante:** `execute_query()` usa o banco **admin** (leitura/escrita). Para queries no banco PEC use `execute_query_pec()`.

---

### `backend/app/auth/jwt.py`

**O que faz:** Implementa toda a lógica de autenticação: hash de senha (bcrypt), geração e validação de tokens JWT, e dependências do FastAPI para proteger endpoints.

```python
# Como proteger um endpoint (somente usuários autenticados):
from app.auth.jwt import get_usuario_obrigatorio

@router.get("/dados-sensiveis")
def dados(usuario = Depends(get_usuario_obrigatorio)):
    return {"usuario": usuario["ds_nome"]}


# Como exigir um perfil específico:
from app.auth.jwt import exigir_perfil

@router.post("/acao-admin")
def acao(usuario = Depends(exigir_perfil("admin"))):
    return {"ok": True}
```

**Funções importantes:**

| Função | O que faz |
|--------|-----------|
| `criar_hash(senha)` | Gera hash bcrypt da senha |
| `verificar_senha(senha, hash)` | Compara senha com hash bcrypt |
| `criar_token(dados)` | Gera JWT com expiração configurável |
| `decodificar_token(token)` | Valida e decodifica JWT — lança HTTPException se inválido |
| `get_usuario_obrigatorio()` | Dependência FastAPI: exige token válido (401 se não autenticado) |
| `exigir_perfil(*perfis)` | Factory de dependência: exige perfil específico (admin/operador/leitor) |

---

### `backend/app/auth/routes.py`

**O que faz:** Endpoints de autenticação e gestão de usuários.

```python
# Endpoints disponíveis:
POST /api/v1/auth/login          # { email, senha } → { access_token, usuario }
GET  /api/v1/auth/me             # Dados do usuário autenticado
GET  /api/v1/auth/usuarios       # Lista usuários (admin only)
POST /api/v1/auth/usuarios       # Cria usuário (admin only)
```

**Como criar um novo usuário via API:**
```bash
curl -X POST /api/v1/auth/usuarios \
  -H "Authorization: Bearer {token_admin}" \
  -H "Content-Type: application/json" \
  -d '{"ds_nome": "João", "ds_email": "joao@saude.gov.br", "ds_senha": "senha123", "tp_perfil": "operador"}'
```

**Tabela de usuários:** `auth.tb_usuarios` — campos: `co_seq_usuario`, `ds_nome`, `ds_email`, `ds_senha_hash`, `tp_perfil`, `st_ativo`, `dt_criacao`, `dt_ultimo_login`.

---

### `backend/app/shared/controle_processamento.py`

**O que faz:** Sistema de auditoria para operações longas (normalização de bairros, treinamento de ML, refresh de views). Registra início, fim, status e métricas em `dashboard.tb_controle_processamento`.

```python
# Como usar em qualquer pipeline:
from app.shared.controle_processamento import registrar_inicio, registrar_fim

# 1. Registra início (retorna ID do registro)
co_seq = registrar_inicio(
    tp_processamento="treino_has",
    ds_modelo="RandomForestClassifier",
    ds_observacao="n_splits=5"
)

try:
    # ... executa o processamento ...
    metricas = {"auc": 0.87, "f1": 0.83}

    # 2. Registra sucesso com métricas
    registrar_fim(co_seq, st_status="concluido", ds_metricas=metricas, qt_registros=5000)

except Exception as e:
    # 3. Registra falha
    registrar_fim(co_seq, st_status="erro", ds_erro=str(e))
```

**Tipos de processamento usados:**
- `treino_has` — treinamento modelo HAS
- `treino_dm` — treinamento modelo DM
- `treino_ob` — treinamento modelo OB
- `normalizacao_bairros` — normalização via ViaCEP
- `refresh_views` — atualização das views materializadas

---

## 3. Backend — Módulo Hipertensão (HAS)

**Localização:** `backend/app/modules/pressao_arterial/`

**Estrutura do módulo:**
```
pressao_arterial/
├── routes/
│   ├── analytics.py   ← Endpoints de dados e gráficos
│   ├── ml.py          ← Endpoints de Machine Learning
│   ├── admin.py       ← Endpoints administrativos
│   └── qualidade.py   ← Endpoints de qualidade de dados
├── analytics/
│   ├── kpis.py        ← Indicadores gerais
│   ├── tendencia.py   ← Evolução temporal
│   ├── prevalencia.py ← Prevalência por perfil demográfico
│   ├── fatores_risco.py ← Comorbidades
│   ├── mapa.py        ← Dados geoespaciais
│   └── ubs.py         ← Por Unidade de Saúde
├── ml/
│   ├── pipeline.py    ← Treinamento RandomForest
│   └── predictor.py   ← Predição individual
├── quality/
│   ├── outlier_detector.py ← Detecção estatística de outliers
│   └── validator.py        ← Validação de valores de PA
├── processors/
│   └── normalizador_bairros.py ← Normalização via ViaCEP + fuzzy
└── views/
    └── manager.py     ← Gerenciamento das views materializadas
```

### `analytics/fatores_risco.py`

**O que faz:** Compara prevalência de comorbidades entre hipertensos e não-hipertensos.

```python
def buscar_comparativo_comorbidades(bairro=None, ano_inicio=None, ano_fim=None):
    """
    Retorna lista de comorbidades com:
    - pct_hipertensos: % dos hipertensos que têm aquela condição
    - pct_nao_hipertensos: % dos não-hipertensos que têm aquela condição
    - diferenca: hipertensos - nao_hipertensos (mostra quanto mais frequente é)
    """

def buscar_multiplos_fatores(bairro=None):
    """
    Retorna distribuição de hipertensos por número de fatores simultâneos.
    Ex: 30% têm 1 fator, 25% têm 2 fatores, 15% têm 3+ fatores.
    """
```

### `analytics/prevalencia.py`

**O que faz:** Calcula prevalência de HAS por diferentes agrupamentos demográficos.

```python
def buscar_prevalencia_por_bairro(ano_inicio=None, ano_fim=None, apenas_vdc=True):
    """
    Retorna prevalência por bairro. Fonte: vw_bairro_canonico
    Filtro apenas_vdc=True exclui endereços fora de Vitória da Conquista.
    """

def buscar_prevalencia_por_sexo(bairro=None, ano_inicio=None, ano_fim=None):
    """Retorna prevalência separada por sexo (Masculino/Feminino)."""

def buscar_prevalencia_por_faixa_etaria(bairro=None, ano_inicio=None, ano_fim=None):
    """Retorna prevalência por faixa etária (18-29, 30-39, ..., 65+)."""
```

### `analytics/mapa.py`

**O que faz:** Fornece dados geoespaciais para o mapa coroplético.

```python
def buscar_dados_mapa(ano_inicio=None, ano_fim=None):
    """
    Retorna por bairro VDC:
    - latitude, longitude (da tb_geocodificacao)
    - total_cadastros, hipertensos, prevalencia_pct
    - n_diabetes, n_avc, n_infarto, n_fumantes
    - pct_idosos (% de pacientes com 65+)
    """

def buscar_dados_mapa_loteamentos(bairros=None, ano_inicio=None, ano_fim=None):
    """Mesmos dados mas com granularidade de loteamento (bairro > loteamento)."""
```

### `ml/pipeline.py`

**O que faz:** Treina o modelo RandomForest para predição de risco de HAS.

```python
def treinar_modelo(n_splits: int = 5) -> dict:
    """
    Pipeline completo de treinamento:
    1. Carrega dados de dashboard.mv_pa_cadastros
    2. Ordena por co_dim_tempo (garante ordem temporal)
    3. Aplica TimeSeriesSplit(n_splits=5) — SEM leakage temporal
    4. Treina RandomForestClassifier em cada fold
    5. Calcula métricas médias (ROC-AUC, F1, Precision, Recall)
    6. Treina modelo final com todos os dados
    7. Salva ha_risk_rf.joblib + ha_risk_meta.json
    8. Registra em tb_controle_processamento
    """
```

**Parâmetros do modelo:**
```python
RandomForestClassifier(
    n_estimators=300,    # Número de árvores (final) / 200 por fold
    max_depth=12,        # Profundidade máxima
    min_samples_leaf=20, # Mínimo de amostras por folha (evita overfitting)
    class_weight="balanced",  # Compensa desbalanceamento (mais não-hipertensos)
    random_state=42,
    n_jobs=-1
)
```

**Features usadas:**

| Feature | Tipo | Descrição |
|---------|------|-----------|
| `idade` | Numérico | Idade em anos |
| `co_dim_sexo` | Categórico | 1=Masculino, 3=Feminino |
| `st_diabetes` | Binário | Tem diabetes |
| `st_fumante` | Binário | É fumante |
| `st_alcool` | Binário | Usa álcool |
| `st_outra_droga` | Binário | Usa outras drogas |
| `st_doenca_cardiaca` | Binário | Doença cardíaca |
| `st_problema_rins` | Binário | Problemas renais |
| `st_avc` | Binário | Histórico de AVC |
| `st_infarto` | Binário | Histórico de infarto |
| `st_doenca_respiratoria` | Binário | Doença respiratória |
| `st_cancer` | Binário | Histórico de câncer |
| `st_hanseniase` | Binário | Hanseníase |
| `st_tuberculose` | Binário | Tuberculose |

### `ml/predictor.py`

**O que faz:** Carrega o modelo treinado e realiza predições individuais.

```python
def predizer_risco(perfil: dict) -> dict:
    """
    Recebe perfil do paciente e retorna:
    - probabilidade: float (0.0 a 1.0)
    - probabilidade_pct: float (0 a 100)
    - nivel_risco: "Baixo" | "Moderado" | "Alto"
    - cor_risco: "green" | "amber" | "red"
    - fatores: lista dos top 8 fatores com importância
    - aviso: string com disclaimer médico
    """
    # Thresholds de risco:
    # < 20%  → Baixo (verde)
    # 20-35% → Moderado (amarelo)
    # >= 35% → Alto (vermelho)
```

### `quality/outlier_detector.py`

**O que faz:** Detecta medições de PA suspeitas usando dois métodos estatísticos.

```python
def detectar_outliers_populacao(df: pd.DataFrame):
    """
    Método IQR: Q1 - 1.5×IQR < valor < Q3 + 1.5×IQR
    Compara cada medição contra a distribuição POPULACIONAL.
    Bom para detectar erros de digitação extremos (ex: PAS=290).
    """

def detectar_outliers_por_paciente(df: pd.DataFrame, min_medicoes=3):
    """
    Método Z-score INDIVIDUAL por paciente.
    Compara medição atual contra o HISTÓRICO do próprio paciente.
    Bom para detectar mudanças abruptas em pacientes estáveis.
    Requer >= 3 medições para calcular Z-score.
    """

def executar_pipeline_outliers(df: pd.DataFrame):
    """
    Executa ambos os métodos e retorna DataFrame com flags:
    - outlier_populacional: bool
    - outlier_individual: bool
    - eh_outlier: bool (qualquer um dos dois)
    """
```

**Importante:** Os outliers são **marcados**, não removidos. São enviados para revisão manual na interface administrativa.

---

## 4. Backend — Módulo Diabetes (DM)

**Localização:** `backend/app/modules/diabetes/`

```
diabetes/
├── routes/
│   ├── analytics.py   ← Endpoints de dados
│   └── ml.py          ← Endpoints de ML
├── analytics/
│   ├── kpis.py        ← KPIs gerais
│   ├── tendencia.py   ← Evolução HbA1c
│   └── controle.py    ← Análise de controle glicêmico
└── ml/
    ├── pipeline.py    ← Treinamento RandomForest
    └── predictor.py   ← Predição individual
```

### `analytics/controle.py`

**O que faz:** Análise de controle glicêmico usando os critérios da SBD 2024.

```python
def buscar_controle_por_grupo(ano_inicio=None, ano_fim=None, bairro=None):
    """
    Retorna por grupo etário (adulto | idoso_65_79 | idoso_80+):
    - total, controlados, descontrolados
    - pct_controlados, hba1c_media

    Critérios SBD 2024 (já aplicados na view mv_dm_hemoglobina):
    - Adultos 18-64: HbA1c < 7.0% = Controlado
    - Idosos 65-79: HbA1c < 7.5% = Controlado
    - Idosos 80+:   HbA1c < 8.0% = Controlado
    """

def buscar_comorbidades_vs_controle():
    """
    Retorna prevalência de cada comorbidade em:
    - controlados: % dos controlados que têm aquela condição
    - descontrolados: % dos descontrolados que têm aquela condição
    Útil para identificar quais comorbidades dificultam o controle.
    """
```

### `ml/pipeline.py`

**O que faz:** Treina RandomForest para predizer controle glicêmico.

```python
# Target: 1 = Controlado, 0 = Descontrolado
# Definido na view mv_dm_hemoglobina usando critérios SBD 2024

# Features (13):
# idade, co_dim_sexo, hba1c (valor atual!), 10 comorbidades
```

**Atenção:** A feature `hba1c` é incluída intencionalmente — o médico já sabe o valor e quer saber se o paciente está ou estará controlado considerando todo o contexto clínico.

---

## 5. Backend — Módulo Obesidade (OB)

**Localização:** `backend/app/modules/obesidade/`

```
obesidade/
├── routes/
│   ├── analytics.py   ← Endpoints de dados
│   └── ml.py          ← Endpoints de ML
├── analytics/
│   ├── kpis.py        ← KPIs + tendência mensal via REGR_SLOPE
│   ├── distribuicao.py← Distribuição das 6 classes OMS
│   └── fatores_risco.py← Comorbidades por classe IMC
├── ml/
│   ├── pipeline.py    ← Treinamento RandomForest multiclasse
│   └── predictor.py   ← Predição individual com probabilidades
└── schemas.py         ← Modelos Pydantic de request/response
```

### `analytics/kpis.py`

**O que faz:** KPIs de obesidade incluindo tendência mensal calculada via regressão linear no PostgreSQL.

```python
def get_kpis(ano_inicio=None, ano_fim=None, bairro=None, co_unidade_saude=None, sexo=None):
    """
    Retorna:
    - total_medicoes, total_adultos_unicos, imc_medio
    - prevalencia_sobrepeso_pct (IMC >= 25)
    - prevalencia_obesidade_pct (IMC >= 30)
    - prevalencia_obesidade_severa_pct (IMC >= 35)
    - tendencia_mensal: inclinação da reta de IMC ao longo do tempo
      Calculado com REGR_SLOPE(imc, EXTRACT(EPOCH FROM dt_medicao))
      Valor positivo = IMC crescendo; negativo = diminuindo
    """
```

### `analytics/fatores_risco.py`

**O que faz:** Calcula prevalência de comorbidades para cada classe de IMC.

```python
def get_fatores_risco(ano_inicio=None, ano_fim=None, bairro=None, co_unidade_saude=None):
    """
    Retorna lista de comorbidades, cada uma com % em cada classe IMC:
    [
      {
        "comorbidade": "Hipertensão Arterial",
        "pct_baixo_peso": 5.2,
        "pct_normal": 18.3,
        "pct_sobrepeso": 35.7,
        "pct_obesidade_i": 52.1,
        "pct_obesidade_ii": 68.4,
        "pct_obesidade_iii": 81.2
      },
      ...
    ]
    """
```

### `ml/pipeline.py`

**O que faz:** Treina RandomForest multiclasse (6 classes OMS) para classificação de IMC.

```python
# Target: classificacao_imc (string: "Baixo Peso", "Normal", "Sobrepeso", ...)
# Precisa de LabelEncoder para converter strings em inteiros

# Parâmetros do modelo:
RandomForestClassifier(
    n_estimators=300,
    max_depth=15,        # Maior que HAS/DM — classificação multiclasse é mais complexa
    min_samples_leaf=10,
    class_weight="balanced",
)
```

### `ml/predictor.py`

**O que faz:** Predição individual com probabilidades para cada classe.

```python
def predizer(peso_kg, altura_m, idade, sexo, st_hipertensao=0, ...):
    """
    Retorna:
    - imc_calculado: float (peso / altura²)
    - classificacao_predita: "Normal" | "Sobrepeso" | ... (classe prevista)
    - probabilidades: {
        "baixo_peso": 0.02,
        "normal": 0.75,
        "sobrepeso": 0.18,
        ...
      }
    - confianca: float (max probabilidade)
    - nivel_confianca: "Baixa" | "Média" | "Alta" | "Muito Alta"
    """
```

### `schemas.py`

**O que faz:** Define os modelos Pydantic para validação de request e response dos endpoints de ML.

```python
class PerfilAntropometrico(BaseModel):
    peso_kg: float          # 10 a 350
    altura_m: float         # 1.0 a 2.5
    idade: int              # 18 a 120
    sexo: str               # "M" ou "F"
    st_hipertensao: int = 0 # 0 ou 1 (comorbidades opcionais)
    ...

class ModeloObesidadeInfoResponse(BaseModel):
    modelo_treinado: bool
    treinado_em: Optional[str]
    total_registros_treino: Optional[int]
    metricas: Optional[dict]         # {"acuracia": {...}, "f1_macro": {...}}
    metricas_por_classe: Optional[list]  # Por classe IMC
    treino_em_andamento: bool = False
```

---

## 6. Banco de Dados — Views Materializadas

### Por que Views Materializadas?

As queries SQL que alimentam os dashboards envolvem JOINs entre 5-8 tabelas do e-SUS PEC, podendo retornar milhares de linhas. Executar essas queries em tempo real causaria latência de 30-60 segundos por requisição.

As **views materializadas** (MVs) pré-calculam e armazenam o resultado em disco. Com índices otimizados, as mesmas queries respondem em milissegundos. O trade-off é que precisam ser atualizadas periodicamente (`REFRESH MATERIALIZED VIEW CONCURRENTLY`).

---

### `dashboard.mv_pa_cadastros`

**Arquivo:** `backend/sql/pressao_arterial/mv_pa_cadastros.sql`

**O que contém:** Um registro por cidadão (mais recente cadastro) com dados demográficos e fatores de risco.

**Por que DISTINCT ON:**
```sql
-- O e-SUS permite múltiplos cadastros por cidadão.
-- Pegamos sempre o mais recente para evitar dupla contagem.
SELECT DISTINCT ON (cad.co_fat_cidadao_pec)
    ...
FROM tb_fat_cad_individual cad
ORDER BY cad.co_fat_cidadao_pec, cad.co_dim_tempo DESC
```

**Filtros aplicados:**
- Adultos (≥ 18 anos), vivos (`st_faleceu = 0`), com bairro registrado
- Sem recusa de cadastro (`st_recusa_cadastro = 0`)

**Colunas críticas para analytics:**
```
st_hipertensao_arterial   → target dos modelos ML
faixa_etaria              → grupos: 18-29, 30-39, ..., 65+
no_bairro_filtro          → bairro normalizado (chave para joins geográficos)
st_diabetes, st_fumante, st_doenca_cardiaca, ...  → features do modelo
```

---

### `dashboard.mv_pa_medicoes`

**Arquivo:** `backend/sql/pressao_arterial/mv_pa_medicoes.sql`

**O que contém:** Todas as medições de PA dos últimos 10 anos com vínculo à UBS.

**Diferencial:** Inclui `co_unidade_saude` e `co_equipe` via JOIN com `tb_atend_prof → tb_lotacao`, possibilitando análise por unidade de saúde.

**Importante:** Não tem deduplicação — cada medição é uma linha. Um cidadão pode ter 50 linhas aqui.

---

### `dashboard.mv_pa_medicoes_cidadaos`

**Arquivo:** `backend/sql/pressao_arterial/mv_pa_medicoes_cidadaos.sql`

**O que contém:** Medições de PA ligadas ao `co_cidadao` — visão longitudinal.

**O JOIN LATERAL:**
```sql
-- LATERAL permite referenciar aliases da query principal no subquery
-- Aqui pega 1 exame requisitado por atendimento (evita produto cartesiano)
INNER JOIN LATERAL (
    SELECT er.co_seq_exame_requisitado
    FROM pec.tb_exame_requisitado er
    WHERE er.co_seq_atend_prof = ap.co_seq_atend_prof
    LIMIT 1   -- ← garante no máximo 1 linha por atendimento
) er ON TRUE
```

**Usado por:** Análise longitudinal, detecção de outliers por histórico do paciente.

---

### `dashboard.mv_dm_hemoglobina`

**Arquivo:** `backend/sql/diabetes/mv_dm_hemoglobina.sql`

**O que contém:** Exames de HbA1c de pacientes diabéticos com classificação de controle (SBD 2024).

**Classificação embarcada na view:**
```sql
CASE
    WHEN cad.grupo_etario = 'adulto'        AND hba1c < 7.0 THEN 'Controlado'
    WHEN cad.grupo_etario = 'idoso_65_79'   AND hba1c < 7.5 THEN 'Controlado'
    WHEN cad.grupo_etario = 'idoso_80+'     AND hba1c < 8.0 THEN 'Controlado'
    ELSE 'Descontrolado'
END AS controle_glicemico
```

**Filtro de diabéticos:** Usa `LATERAL` para buscar o cadastro mais recente onde `st_diabete = 1`. Apenas pacientes com diabetes confirmado no cadastro aparecem aqui.

---

### `dashboard.mv_obesidade`

**Arquivo:** `backend/sql/obesidade/mv_obesidade.sql`

**O que contém:** Medições antropométricas com IMC recalculado e classificação OMS.

**Recálculo do IMC:**
```sql
-- O e-SUS armazena IMC calculado pela balança, que pode ter erros.
-- A view sempre recalcula a partir dos valores brutos de peso e altura.
(mv.peso_kg / (mv.altura_m * mv.altura_m)) AS imc

-- CTE inicial filtra valores fisiologicamente impossíveis:
-- Peso: 10-350 kg | Altura: 100-250 cm | IMC resultante: 10-80
```

**Classificação IMC (OMS):**
```sql
CASE
    WHEN imc < 18.5  THEN 'Baixo Peso'
    WHEN imc < 25.0  THEN 'Normal'
    WHEN imc < 30.0  THEN 'Sobrepeso'
    WHEN imc < 35.0  THEN 'Obesidade I'
    WHEN imc < 40.0  THEN 'Obesidade II'
    ELSE                  'Obesidade III'
END AS classificacao_imc
```

---

### `dashboard.vw_bairro_canonico` e `dashboard.vw_loteamento_canonico`

**Arquivo:** `backend/sql/pressao_arterial/vw_bairro_canonico.sql`

**O que fazem:** Views **regulares** (não materializadas) que enriquecem `mv_pa_cadastros` com normalização geográfica.

**O problema que resolvem:** O e-SUS tem 2300+ variações de nomes de bairros para ~100 bairros reais. Ex: "Boa Vista", "BOAVISTA", "B. Vista", "Bairro Boa Vista" → todos o mesmo lugar.

```sql
-- vw_bairro_canonico usa tb_bairros_mapeamento para normalizar:
LEFT JOIN dashboard.tb_bairros_mapeamento bm
    ON normaliza_bairro(cad.no_bairro_filtro) = normaliza_bairro(bm.no_bairro_raw)

-- Resultado: cada cadastro ganha bairro_canonico + flag st_bairro_vdc
-- st_bairro_vdc = TRUE: bairro reconhecido no GeoJSON oficial da prefeitura
-- st_bairro_vdc = FALSE: endereço rural, distrito ou sem mapeamento
```

**`vw_loteamento_canonico`** adiciona hierarquia bairro > loteamento para o mapa com granularidade máxima.

---

## 7. Scripts de Setup e Manutenção

### `backend/scripts/setup.py`

**O que faz:** Script master de inicialização. Configura todo o banco de dados do zero.

```bash
# Comando mais importante — faz tudo:
python scripts/setup.py --all

# Flags individuais:
python scripts/setup.py --check            # Verifica conexão e status
python scripts/setup.py --schema           # Cria schemas (dashboard, auth, pec)
python scripts/setup.py --auth             # Cria tabela de usuários e admin padrão
python scripts/setup.py --tabelas          # Cria tabelas de suporte
python scripts/setup.py --views-pa         # Cria 3 views de PA (demorado!)
python scripts/setup.py --views-diabetes   # Cria view de DM
python scripts/setup.py --views-obesidade  # Cria view de OB
python scripts/setup.py --views-regulares  # Cria vw_bairro_canonico e loteamento
python scripts/setup.py --refresh          # Atualiza todas as views materializadas
```

**Função crítica — `_split_statements()`:**
```python
def _split_statements(sql_text: str) -> list[str]:
    """
    Divide SQL em statements por ';', MAS ignora ';' dentro de blocos $$ ... $$.
    Necessário porque PL/pgSQL usa ';' dentro de funções:
        CREATE FUNCTION ... AS $$
        BEGIN
          IF x THEN RETURN NULL; END IF;  ← ';' aqui não é fim de statement
        END;
        $$ LANGUAGE plpgsql;              ← ';' aqui SIM é fim de statement
    """
```

**Credencial padrão criada pelo `--auth`:**
- Email: `admin@plataforma.saude`
- Senha: `admin123`
- **TROCAR EM PRODUÇÃO** via `POST /api/v1/auth/usuarios` ou direto no banco.

---

### `backend/scripts/normalizar_bairros.py`

**O que faz:** Normaliza nomes de bairros do e-SUS usando ViaCEP e fuzzy matching.

```bash
python scripts/normalizar_bairros.py                     # Execução completa (~30 min)
python scripts/normalizar_bairros.py --status            # Ver estatísticas atuais
python scripts/normalizar_bairros.py --limite-ceps 50    # Teste rápido (50 CEPs)
python scripts/normalizar_bairros.py --threshold 85      # Threshold mais rigoroso
```

**Como funciona:**
1. **Fase 1 (CEP → ViaCEP):** Para cada CEP distinto em `mv_pa_cadastros`, consulta a API ViaCEP e salva o bairro oficial.
2. **Fase 2 (Fuzzy):** Para bairros sem CEP, usa fuzzy matching (RapidFuzz) contra a lista de bairros coletada na Fase 1.

**Resultado:** Tabela `dashboard.tb_bairros_mapeamento` com `no_bairro_raw → no_bairro_canonico`.

---

### `backend/scripts/sincronizar_base_geografica.py`

**O que faz:** Sincronização offline dos GeoJSONs da prefeitura com os bairros do e-SUS.

```bash
python scripts/sincronizar_base_geografica.py --threshold 80.0
```

**Arquivos necessários:**
```
backend/data/geojson/
├── Bairros.geojson      ← Bairros oficiais com polígonos
└── Loteamentos.geojson  ← Loteamentos (subdivisões)
```

**O que faz:**
1. Lê GeoJSONs e calcula centroid de cada polígono
2. Popula `dashboard.tb_geocodificacao` com coordenadas oficiais
3. Mapeia bairros do e-SUS para bairros/loteamentos do GeoJSON via fuzzy matching offline

---

## 8. Frontend — Estrutura e Roteamento

### `frontend/src/App.jsx`

**O que faz:** Componente raiz. Configura React Query, contexto de autenticação e todo o sistema de roteamento.

**A estrutura MODULES:**
```javascript
// Adicionar um novo módulo aqui para aparecer no sidebar
const MODULES = [
  {
    key: 'hipertensao',
    label: 'Hipertensão',
    Icon: Heart,
    color: 'text-blue-600',
    bgActive: 'bg-blue-50',
    pages: [
      { to: '/',                  label: 'Painel',          Icon: BarChart2 },
      { to: '/prevalencia',       label: 'Prevalência',     Icon: Users },
      { to: '/fatores-risco',     label: 'Fatores de Risco',Icon: Shield },
      { to: '/mapa',              label: 'Mapa',            Icon: MapPin },
      { to: '/ubs',               label: 'Por UBS',         Icon: Building2 },
      { to: '/risco',             label: 'Risco Individual', Icon: Stethoscope },
      { to: '/qualidade',         label: 'Qualidade',       Icon: CheckSquare },
    ],
  },
  // Diabetes e Obesidade seguem o mesmo padrão...
]
```

**O componente AuthGate:**
```javascript
function AuthGate() {
  const { carregando, usuario } = useAuth()
  if (carregando) return <LoadingScreen />
  if (!usuario)   return <Login />        // Não autenticado
  return <Layout />                       // Autenticado → mostra aplicação
}
```

---

### `frontend/src/contexts/AuthContext.jsx`

**O que faz:** Gerencia o estado de autenticação globalmente. Persiste o token no `localStorage`.

```javascript
// Como usar em qualquer componente:
import { useAuth } from '../contexts/AuthContext'

function MeuComponente() {
  const { usuario, token, login, logout, carregando } = useAuth()

  // usuario = { ds_nome, ds_email, tp_perfil } ou null
  // token = string JWT ou null
  // carregando = true enquanto valida token ao iniciar
}
```

**Validação de token ao iniciar:**
```javascript
useEffect(() => {
  // Ao montar, verifica se o token salvo ainda é válido
  const tokenSalvo = localStorage.getItem('token')
  if (tokenSalvo) {
    fetch('/api/v1/auth/me', { headers: { Authorization: `Bearer ${tokenSalvo}` } })
      .then(r => r.ok ? r.json() : null)
      .then(user => setUsuario(user))  // Se válido, seta usuário; senão, null
  }
}, [])
```

---

### `frontend/src/api/pressaoArterial.js`, `diabetes.js`, `obesidade.js`

**O que fazem:** Clientes HTTP para cada módulo. Seguem o mesmo padrão.

```javascript
// Padrão de implementação do client:
const BASE = '/api/v1/modulo'

async function get(path, params = {}) {
  const url = new URL(BASE + path, window.location.origin)
  // Adiciona parâmetros não-nulos na URL: ?filtro=valor&...
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v)
  })
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const api = {
  kpis:      (params = {}) => get('/kpis', params),
  tendencia: (params = {}) => get('/tendencia', params),
  // ...
}
```

**Por que omitir parâmetros nulos:** Se `bairro=null`, a URL não inclui `?bairro=null`, e o backend retorna dados de todos os bairros (sem filtro). Isso simplifica os filtros no frontend.

---

## 9. Frontend — Módulo Hipertensão

### `frontend/src/pages/Painel.jsx`

**O que faz:** Dashboard principal com KPIs e gráfico de tendência mensal de medições de PA.

```javascript
// Padrão de query com filtros reativos:
const [anoInicio, setAnoInicio] = useState(null)
const [anoFim, setAnoFim]       = useState(null)

const { data: tendencia } = useQuery({
  queryKey: ['tendencia', anoInicio, anoFim],  // Muda os filtros → refaz a query
  queryFn: () => api.tendencia({ ano_inicio: anoInicio, ano_fim: anoFim }),
})
```

**Estrutura dos dados de KPIs:**
```javascript
{
  total_cadastros: 45000,
  total_hipertensos: 12500,
  prevalencia_geral_pct: 27.8,
  total_bairros: 87
}
```

---

### `frontend/src/pages/Mapa.jsx`

**O que faz:** Mapa interativo usando Leaflet com círculos coloridos por prevalência.

```javascript
// Função de cor baseada em prevalência:
function corPrevalencia(pct) {
  // Gradiente: verde (0%) → amarelo (20%) → vermelho (40%+)
  if (pct < 10) return '#22c55e'   // verde
  if (pct < 20) return '#eab308'   // amarelo
  if (pct < 30) return '#f97316'   // laranja
  return '#ef4444'                  // vermelho
}

// Tamanho do círculo proporcional ao volume:
function raioCirculo(total) {
  return Math.max(6, Math.min(40, Math.sqrt(total) * 0.8))
}
```

---

### `frontend/src/pages/RiscoIndividual.jsx`

**O que faz:** Calculadora de risco individual. Formulário com os dados do paciente → gráfico "gauge" com percentual de risco.

```javascript
// O gauge é um SVG desenhado manualmente:
function RiskGauge({ pct, nivel }) {
  // Semi-círculo de 180° com cor que varia conforme o risco
  // Verde < 20%, Âmbar 20-35%, Vermelho >= 35%
  const angulo = (pct / 100) * 180  // 0% = 0°, 100% = 180°
  // Usa Math.cos/sin para calcular a ponta da agulha
}
```

**Aviso de modelo não treinado:**
```javascript
// Se não houver modelo treinado, desabilita o formulário e mostra aviso:
const modeloDisponivel = modeloInfo?.disponivel === true
// <button disabled={!modeloDisponivel || loading}>Calcular Risco</button>
```

---

### `frontend/src/pages/FatoresRisco.jsx`

**O que faz:** Duas análises em abas: comparativo de comorbidades e distribuição de múltiplos fatores.

**Aba 1 — Comparativo:**
```javascript
// Gráfico horizontal de barras:
// Hipertensão:  ██████████████ 67%  (hipertensos)
//               ██████ 31%          (não-hipertensos)
```

**Aba 2 — Múltiplos Fatores:**
```javascript
// Pie chart mostrando quantos fatores de risco os hipertensos acumulam:
// 1 fator: 30%
// 2 fatores: 25%
// 3+ fatores: 15%
```

---

## 10. Frontend — Módulo Diabetes

### `frontend/src/pages/diabetes/DmPainel.jsx`

**O que faz:** Dashboard DM com KPIs, tendência de HbA1c e distribuição por grupos etários.

**Componente de grupos etários:**
```javascript
function DmGruposEtarios({ data }) {
  // Exibe média HbA1c de cada grupo com a META SBD 2024 como referência visual
  // Adultos 18-64: Meta < 7.0%  | Idosos 65-79: Meta < 7.5% | 80+: Meta < 8.0%
  return data.map(grupo => (
    <div>
      <p>{grupo.nome}: {grupo.media.toFixed(1)}%</p>
      <p>Meta: {grupo.meta}%</p>
      <BarraProgresso atual={grupo.media} meta={grupo.meta} />
    </div>
  ))
}
```

---

### `frontend/src/pages/diabetes/DmControle.jsx`

**O que faz:** Análise de controle glicêmico em 3 abas: grupos etários, bairros e comorbidades.

```javascript
// Queries com lazy loading — só carrega quando a aba está ativa:
const { data: dataBairros } = useQuery({
  queryKey: ['dm-controle-bairro'],
  queryFn: dmApi.controleBairro,
  enabled: aba === 'bairros'  // ← só executa quando necessário
})
```

---

### `frontend/src/pages/diabetes/DmRisco.jsx`

**O que faz:** Predição individual de controle glicêmico — similar ao `RiscoIndividual.jsx` do HAS.

```javascript
// O formulário inclui o campo HbA1c atual (diferencial vs HAS):
<input type="range" min={3} max={20} step={0.1}
  value={perfil.hba1c}
  onChange={e => setPerfil(p => ({ ...p, hba1c: parseFloat(e.target.value) }))} />

// Resultado mostra "Provável controle" / "Controle incerto" / "Risco de descontrole"
// Thresholds: >= 65% = Verde, 40-65% = Âmbar, < 40% = Vermelho
```

---

## 11. Frontend — Módulo Obesidade

### `frontend/src/pages/obesidade/ObPainel.jsx`

**O que faz:** Dashboard OB com KPIs e gráfico de tendência de IMC.

**Cor do módulo:** Laranja (`orange-500`, `text-orange-600`) — diferencia de Azul (HAS) e Verde (DM).

---

### `frontend/src/pages/obesidade/ObDistribuicao.jsx`

**O que faz:** Distribuição das 6 classes OMS em 3 visualizações.

```javascript
// Cores para cada classe (padrão usado em todos os gráficos de OB):
const COR_CLASSE = {
  'Baixo Peso':    '#60a5fa',  // azul claro
  'Normal':        '#4ade80',  // verde
  'Sobrepeso':     '#facc15',  // amarelo
  'Obesidade I':   '#fb923c',  // laranja
  'Obesidade II':  '#f87171',  // vermelho claro
  'Obesidade III': '#dc2626',  // vermelho escuro
}

// Gráfico horizontal (melhor para comparar distribuição):
<BarChart data={sorted} layout="vertical">
  <YAxis type="category" dataKey="classificacao" />
  <XAxis type="number" unit="%" domain={[0, 100]} />
</BarChart>
```

---

### `frontend/src/pages/obesidade/ObFatoresRisco.jsx`

**O que faz:** Gráfico e tabela de comorbidades por classe de IMC.

```javascript
// Dados do backend: { comorbidades: [{comorbidade, pct_baixo_peso, pct_normal, ...}] }
// Frontend precisa "pivotar" para o formato do Recharts:
const chartData = comorbidades.map(item => ({
  name: LABEL_CURTO[item.comorbidade],   // nome curto para eixo X
  'Baixo Peso': item.pct_baixo_peso,
  'Normal':     item.pct_normal,
  // ...
}))
```

---

### `frontend/src/pages/obesidade/ObRisco.jsx`

**O que faz:** Predição de classificação IMC com probabilidades por classe.

```javascript
// Diferencial: mostra probabilidades para TODAS as 6 classes simultaneamente
// (diferente de HAS/DM que é binário)
const chartData = ORDEM_CLASSES.map(cls => ({
  name: cls,
  prob: Math.round((resultado.probabilidades[PROB_KEYS[cls]] ?? 0) * 100)
}))

// Badge de confiança:
// < 50% = Baixa | 50-70% = Média | 70-90% = Alta | > 90% = Muito Alta
```

---

## 12. Frontend — Componentes e Utilitários

### `frontend/src/components/ui.jsx`

**O que faz:** Biblioteca de componentes reutilizáveis. Importar daqui para consistência visual.

```javascript
import {
  Card, CardBody,          // Container base
  PageHeader,              // Título de página com slot para actions
  MetricCard,              // KPI card com ícone + valor
  StatusBadge, StatusIcon, // Indicadores de status (verde/amarelo/vermelho)
  LoadingState,            // Spinner + mensagem
  ErrorState,              // Alert de erro com retry
  EmptyState,              // Placeholder "sem dados"
  CommandBlock,            // Bloco de código com botão de cópia
  StepHeader,              // Cabeçalho de seção numerada (usado em Admin)
} from '../components/ui'
```

**Como usar MetricCard:**
```javascript
<MetricCard
  label="Total de Hipertensos"
  value="12.543"
  sub="de 45.000 cadastros"
  icon={Heart}
  color="red"    // "blue" | "green" | "amber" | "red" | "purple" | "slate"
/>
```

**Padrão de loading/error/empty:**
```javascript
{isLoading ? (
  <LoadingState message="Carregando dados..." />
) : isError ? (
  <ErrorState message={error.message} onRetry={refetch} />
) : !data?.length ? (
  <EmptyState message="Nenhum dado encontrado." />
) : (
  <MeuConteudo data={data} />
)}
```

---

### `frontend/vite.config.js`

**O que faz:** Configura o bundler Vite. A parte mais importante é o **proxy da API**.

```javascript
export default defineConfig({
  server: {
    proxy: {
      // Todas as requisições /api/* são redirecionadas para o backend
      '/api': 'http://localhost:8000'
    }
  }
})
```

**Por que o proxy:** Em desenvolvimento, o frontend roda na porta 5173 e o backend na 8000. Sem proxy, o browser bloquearia as requisições por CORS. Com proxy, o Vite intercepta `/api/*` e repassa para o backend.

---

## 13. Como Adicionar um Novo Módulo

Exemplo: adicionar módulo "Saúde Mental" (`/saude-mental`).

### Passo 1 — Backend: criar a view materializada

```sql
-- backend/sql/saude_mental/mv_saude_mental.sql
CREATE MATERIALIZED VIEW IF NOT EXISTS dashboard.mv_saude_mental AS
SELECT
    co_seq_medicao,
    ...
FROM pec.tb_medicao
WHERE ...
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_sm_pk ON dashboard.mv_saude_mental(co_seq_medicao);
```

### Passo 2 — Backend: criar o módulo

```
backend/app/modules/saude_mental/
├── __init__.py
├── routes/
│   └── analytics.py    ← endpoints
└── analytics/
    └── kpis.py         ← queries
```

```python
# routes/analytics.py
from fastapi import APIRouter
from .analytics import kpis

router = APIRouter()

@router.get("/kpis")
def get_kpis():
    return kpis.buscar_kpis()
```

### Passo 3 — Backend: registrar o router em `main.py`

```python
from app.modules.saude_mental.routes.analytics import router as sm_router
app.include_router(sm_router, prefix="/api/v1/saude-mental", tags=["Saúde Mental"])
```

### Passo 4 — Frontend: criar o API client

```javascript
// frontend/src/api/saudeMental.js
const BASE = '/api/v1/saude-mental'
async function get(path, params = {}) { /* mesmo padrão dos outros */ }
export const smApi = {
  kpis: () => get('/kpis'),
}
```

### Passo 5 — Frontend: criar as páginas

```
frontend/src/pages/saude_mental/
└── SmPainel.jsx
```

### Passo 6 — Frontend: adicionar ao MODULES em `App.jsx`

```javascript
import SmPainel from './pages/saude_mental/SmPainel.jsx'
import { Brain } from 'lucide-react'

const MODULES = [
  // ... módulos existentes ...
  {
    key: 'saude-mental',
    label: 'Saúde Mental',
    Icon: Brain,
    color: 'text-purple-600',
    bgActive: 'bg-purple-50',
    pages: [
      { to: '/saude-mental', label: 'Painel', Icon: BarChart2 },
    ],
  },
]

// E adicionar na seção <Routes>:
<Route path="/saude-mental" element={<SmPainel />} />
```

---

## 14. Como Modificar um Modelo de ML

### Adicionar uma nova feature

1. **Verifique se a coluna existe na view materializada:**
   ```sql
   SELECT column_name FROM information_schema.columns
   WHERE table_name = 'mv_pa_cadastros';
   ```

2. **Se não existir, adicione à view SQL e re-execute:**
   ```bash
   python scripts/setup.py --views-pa
   ```

3. **Adicione ao `FEATURES` no pipeline:**
   ```python
   # backend/app/modules/pressao_arterial/ml/pipeline.py
   FEATURES = [
       "idade", "co_dim_sexo",
       "st_nova_feature",    # ← Adicionar aqui
       "st_diabetes", "st_fumante", ...
   ]
   ```

4. **Re-treine via interface administrativa ou API:**
   ```bash
   curl -X POST /api/v1/pressao-arterial/modelo/treinar \
     -H "Authorization: Bearer {token}"
   ```

5. **O frontend detecta automaticamente:** O endpoint `/modelo/info` retorna as feature importances do novo modelo treinado.

---

### Mudar o algoritmo de ML

```python
# Em pipeline.py, substitua o estimador:
from sklearn.ensemble import GradientBoostingClassifier

modelo = GradientBoostingClassifier(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.1,
    # class_weight não suportado → usar sample_weight se necessário
)
```

---

### Ajustar thresholds de risco (HAS)

```python
# Em predictor.py:
def _nivel_risco(prob: float) -> tuple[str, str]:
    if prob < 0.20:  # ← ajustar aqui
        return "Baixo", "green"
    if prob < 0.35:  # ← ajustar aqui
        return "Moderado", "amber"
    return "Alto", "red"
```

---

## 15. Variáveis de Ambiente e Configuração

**Arquivo:** `backend/.env` (copiar de `.env.example`)

```bash
# Modo do banco de dados
ENVIRONMENT=development
DB_MODE=fdw           # "fdw" (dois bancos) ou "single" (um banco)

# Banco PEC (e-SUS — somente leitura)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pet_saude
DB_USER=postgres
DB_PASSWORD=sua_senha

# Banco Admin (leitura/escrita — necessário apenas no modo FDW)
ADMIN_DB_HOST=localhost
ADMIN_DB_PORT=5432
ADMIN_DB_NAME=admin-esus
ADMIN_DB_USER=postgres
ADMIN_DB_PASSWORD=sua_senha

# Segurança JWT (OBRIGATÓRIO trocar em produção!)
JWT_SECRET_KEY=gere_com_openssl_rand_-hex_32
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8

# Validação de PA (limites fisiológicos)
PA_PAS_MIN=50          # Sistólica mínima aceita
PA_PAS_MAX=300         # Sistólica máxima aceita
PA_PAD_MIN=30          # Diastólica mínima aceita
PA_PAD_MAX=200         # Diastólica máxima aceita

# Detecção de outliers
OUTLIER_ZSCORE_THRESHOLD=3.0   # Mais baixo = mais sensível
OUTLIER_IQR_FACTOR=1.5         # Padrão Tukey (1.5 = moderado, 3.0 = conservador)

# Histórico de dados a carregar nas views
ANOS_HISTORICO=10
```

---

## Referência Rápida de Endpoints

### Hipertensão (`/api/v1/pressao-arterial`)
```
GET  /kpis                          → Indicadores gerais
GET  /tendencia?ano_inicio&ano_fim  → Evolução mensal
GET  /prevalencia?agrupamento&bairro → Por bairro/sexo/faixa_etária
GET  /fatores-risco?multiplos&bairro → Comorbidades
GET  /mapa                          → Dados para mapa
GET  /ubs?ano_inicio&ano_fim        → Por Unidade de Saúde
GET  /modelo/info                   → Status e métricas do modelo ML
POST /modelo/treinar                → Inicia treinamento em background
POST /predizer-risco                → Predição individual (JSON body)
POST /admin/refresh/{view}          → Atualiza view materializada
POST /admin/treinar/{modulo}        → Treina modelo (has/dm/ob)
```

### Diabetes (`/api/v1/diabetes`)
```
GET  /kpis                    → Indicadores gerais
GET  /tendencia               → Evolução mensal HbA1c
GET  /hba1c/faixa             → Distribuição por faixa de HbA1c
GET  /controle/grupo          → Controlados vs descontrolados por grupo etário
GET  /controle/bairro         → Controle por bairro
GET  /controle/comorbidades   → Comorbidades vs controle
POST /predizer-controle       → Predição individual
```

### Obesidade (`/api/v1/obesidade`)
```
GET  /kpis                → Indicadores gerais + tendência
GET  /tendencia           → Evolução mensal IMC
GET  /distribuicao        → Distribuição 6 classes OMS
GET  /fatores-risco       → Comorbidades por classe IMC
POST /predizer-imc        → Predição individual (6 classes)
```

### Autenticação (`/api/v1/auth`)
```
POST /login               → { email, senha } → { access_token }
GET  /me                  → Dados do usuário autenticado
POST /usuarios            → Criar usuário (admin)
```
