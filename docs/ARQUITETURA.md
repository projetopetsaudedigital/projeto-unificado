# Arquitetura do Sistema

## Visão Geral

A plataforma é um sistema **full-stack** que analisa dados reais do banco PostgreSQL do **e-SUS PEC** (Prontuário Eletrônico do Cidadão), usado pelas unidades básicas de saúde (UBS) de um município.

```
┌─────────────────────────────────────────────────────┐
│                     Frontend                         │
│   React 19 + Vite + TailwindCSS + Recharts + Leaflet│
│                    (porta 5173)                      │
└────────────────────────┬────────────────────────────┘
                         │  HTTP / JSON  (JWT Bearer)
┌────────────────────────▼────────────────────────────┐
│                     Backend                          │
│         FastAPI + SQLAlchemy + scikit-learn           │
│                    (porta 8000)                      │
└────────────────────────┬────────────────────────────┘
                         │  SQL (psycopg2)
┌────────────────────────▼────────────────────────────┐
│              PostgreSQL                               │
│  ┌────────────────┐  ┌───────────────────────────┐  │
│  │ Schema: public │  │ Schema: dashboard          │  │
│  │ (e-SUS PEC —  │  │ (views materializadas +    │  │
│  │  408 tabelas)  │  │  tabelas de suporte)       │  │
│  └────────────────┘  └───────────────────────────┘  │
│  ┌──────────────────────────────────────────────┐    │
│  │ Schema: auth  (usuários, roles, JWT)          │    │
│  └──────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

### Modo Dual-Database (FDW vs Single)

A plataforma suporta dois modos de banco de dados, configurável via `DB_MODE` no `.env`:

| Modo | Configuração | Quando usar |
|------|-------------|-------------|
| `fdw` (padrão) | Banco PEC (somente leitura) + banco admin separado (leitura/escrita para views e controle) | Produção — não altera o banco do e-SUS PEC |
| `single` | Tudo em um único banco | Desenvolvimento / ambiente simplificado |

---

## Backend — Estrutura Modular

### Core (`app/core/`)

| Arquivo | Responsabilidade |
|---------|-----------------|
| `config.py` | Configurações via `pydantic-settings` (carrega `.env`) |
| `database.py` | Engine SQLAlchemy, pool de conexões, `execute_query()` |
| `logging_config.py` | Configuração centralizada de logging |

### Autenticação (`app/auth/`)

| Arquivo | Responsabilidade |
|---------|-----------------|
| `routes.py` | Endpoints REST: login, me, CRUD de usuários |
| `jwt.py` | Criação/verificação de tokens JWT, bcrypt, dependências FastAPI |

**Roles disponíveis:** `admin` (total), `operador` (escrita), `leitor` (somente leitura).

**Schema `auth`:** Tabela `auth.tb_usuarios` com nome, email, senha (hash bcrypt), perfil e timestamps.

### Módulos (`app/modules/`)

Cada módulo segue a mesma estrutura:

```
modulo/
├── routes/          # Endpoints FastAPI (rotas REST)
├── analytics/       # Funções de consulta analítica (SQL)
├── ml/              # Pipeline de ML (treino) + Predictor (inferência)
├── processors/      # Processamento de dados (normalização, etc.)
├── quality/         # Validação e auditoria de dados
├── views/           # Gerenciamento de views materializadas
└── schemas.py       # Pydantic models para request/response
```

#### Módulo Pressão Arterial (`pressao_arterial/`)

| Componente | Arquivos | O que faz |
|------------|----------|-----------|
| **Routes** | `admin.py`, `analytics.py`, `health.py`, `ml.py`, `qualidade.py` | Endpoints REST para cada funcionalidade |
| **Analytics** | `fatores_risco.py`, `mapa.py`, `prevalencia.py`, `tendencia.py`, `ubs.py` | Queries agregadas sobre as views materializadas |
| **ML** | `pipeline.py`, `predictor.py` | Treinamento (RandomForest + TimeSeriesSplit) e inferência de risco de HAS |
| **Processors** | `normalizador_bairros.py` | Normalização de nomes de bairros (ViaCEP + fuzzy) |
| **Quality** | `audit_table.py`, `outlier_detector.py`, `validator.py` | Detecção de outliers via Z-score/IQR, validação de faixas de PA |
| **Views** | `manager.py` | Criação e refresh das views materializadas |

#### Módulo Diabetes (`diabetes/`)

| Componente | Arquivos | O que faz |
|------------|----------|-----------|
| **Routes** | `analytics.py`, `ml.py` | Endpoints REST |
| **Analytics** | `controle.py`, `kpis.py`, `tendencia.py` | KPIs, controle glicêmico, tendências de HbA1c |
| **ML** | `pipeline.py`, `predictor.py` | Treinamento e inferência do controle glicêmico (binário) |

#### Módulo Obesidade (`obesidade/`)

| Componente | Arquivos | O que faz |
|------------|----------|-----------|
| **Routes** | `analytics.py`, `ml.py` | Endpoints REST |
| **Analytics** | `kpis.py`, `tendencia.py`, `distribuicao.py`, `fatores_risco.py` | KPIs de IMC, série mensal, 6 classes OMS, comorbidades, bairros |
| **ML** | `pipeline.py`, `predictor.py` | Treinamento e inferência de classificação de IMC (multiclasse, 6 classes) |

---

## Schema `dashboard` — Views Materializadas

O schema `dashboard` isola os dados analíticos do schema `public` (dados brutos do e-SUS PEC).

```
                    Schema: public (e-SUS PEC)
     ┌─────────────────────┬──────────────────────┐
     │ tb_fat_cad_individual│ tb_fat_cidadao_pec   │
     │ tb_cidadao           │ tb_medicao           │
     │ tb_dim_sexo          │ tb_atend_prof        │
     │ tb_dim_raca_cor      │ tb_lotacao           │
     │ tb_exame_hemoglobina │ tb_exame_requisitado │
     │ tb_prontuario        │ ... (408 tabelas)    │
     └──────────┬──────────┴──────────┬───────────┘
                │                     │
     ┌──────────▼─────────────────────▼───────────┐
     │         Schema: dashboard                    │
     │                                              │
     │  ┌─ mv_pa_cadastros (1 linha/cidadão)        │
     │  │  └─ Dados demográficos, fatores de risco  │
     │  │     comorbidades, geolocalização           │
     │  │                                            │
     │  ├─ mv_pa_medicoes (medições de PA)           │
     │  │  └─ PA, sinais vitais, vinculada a UBS     │
     │  │                                            │
     │  ├─ mv_pa_medicoes_cidadaos (PA + cidadão)    │
     │  │  └─ Visão longitudinal por paciente        │
     │  │                                            │
     │  ├─ mv_dm_hemoglobina (exames HbA1c)          │
     │  │  └─ Controle glicêmico por cidadão         │
     │  │                                            │
     │  ├─ mv_obesidade (IMC por medição)            │
     │  │  └─ Peso, altura, IMC recalculado,         │
     │  │     classificação OMS por cidadão           │
     │  │                                            │
     │  ├─ vw_bairro_canonico (view regular)          │
     │  │  └─ Resolve bairro normalizado              │
     │  │                                            │
     │  ├─ tb_bairros_mapeamento                      │
     │  │  └─ Tabela de-para: bairro raw → canônico   │
     │  │                                            │
     │  ├─ tb_auditoria_outliers                      │
     │  │  └─ Registro de outliers detectados          │
     │  │                                            │
     │  └─ tb_controle_processamento                  │
     │     └─ Histórico de processamentos              │
     └────────────────────────────────────────────────┘
```

### Views Materializadas

| View | Fonte | Registros típicos | Atualização |
|------|-------|-------------------|-------------|
| `mv_pa_cadastros` | `tb_fat_cad_individual` + `tb_cidadao` + dims | 1 por cidadão (DISTINCT ON) | `REFRESH MATERIALIZED VIEW CONCURRENTLY` |
| `mv_pa_medicoes` | `tb_medicao` + `tb_atend_prof` + `tb_lotacao` | Todas com PA preenchida (10 anos) | Idem |
| `mv_pa_medicoes_cidadaos` | `tb_medicao` + cadeia de joins até `tb_cidadao` | PA vinculada a cidadão | Idem |
| `mv_dm_hemoglobina` | `tb_exame_hemoglobina_glicada` + cidadão + cadastro | Exames HbA1c de diabéticos | Idem |
| `mv_obesidade` | `tb_medicao` (peso + altura) + cidadão + cadastro | Medições com IMC calculado | Idem |

---

## Frontend — Estrutura

### Tecnologias

| Lib | Versão | Uso |
|-----|--------|-----|
| React | 19 | Framework UI |
| Vite | 7 | Build tool + dev server |
| TailwindCSS | 4 | Estilização CSS |
| Recharts | 3 | Gráficos (barras, linhas, pizza, área) |
| Leaflet | 1.9 | Mapas geográficos |
| React Query | 5 | Cache e gerenciamento de requisições |
| Zustand | 5 | Estado global |
| react-router-dom | 7 | Roteamento SPA |

### Páginas

| Página | Rota | Módulo | Descrição |
|--------|------|--------|-----------|
| `Painel.jsx` | `/` | HAS | KPIs gerais de hipertensão |
| `Prevalencia.jsx` | `/prevalencia` | HAS | Prevalência por bairro |
| `FatoresRisco.jsx` | `/fatores-risco` | HAS | Comorbidades e hábitos |
| `Mapa.jsx` | `/mapa` | HAS | Mapa georreferenciado (Leaflet) |
| `UBS.jsx` | `/ubs` | HAS | Comparação entre unidades |
| `RiscoIndividual.jsx` | `/risco` | HAS | Predição ML para cidadão |
| `Qualidade.jsx` | `/qualidade` | HAS | Auditoria de dados |
| `Admin.jsx` | `/admin` | Sistema | Setup e gerenciamento |
| `Login.jsx` | `/login` | Auth | Autenticação JWT |
| `DmPainel.jsx` | `/diabetes` | DM | KPIs de diabetes |
| `DmControle.jsx` | `/diabetes/controle` | DM | Controle glicêmico |
| `DmTendencias.jsx` | `/diabetes/tendencias` | DM | Tendências HbA1c |
| `DmRisco.jsx` | `/diabetes/risco` | DM | Risco glicêmico ML |
| `ObPainel.jsx` | `/obesidade` | OB | KPIs de IMC e obesidade |
| `ObDistribuicao.jsx` | `/obesidade/distribuicao` | OB | Distribuição das 6 classes OMS |
| `ObFatoresRisco.jsx` | `/obesidade/fatores-risco` | OB | Comorbidades por faixa de IMC |
| `ObRisco.jsx` | `/obesidade/risco` | OB | Predição de classificação de IMC |

### Comunicação com Backend

A camada `src/api/` encapsula todas as chamadas HTTP:

- `pressaoArterial.js` → endpoints `/api/v1/pressao-arterial/*`
- `diabetes.js` → endpoints `/api/v1/diabetes/*`
- `obesidade.js` → endpoints `/api/v1/obesidade/*`

O Vite faz proxy automático para `localhost:8000` via `vite.config.js`.

O `AuthContext` (`src/contexts/`) gerencia o JWT, armazenando o token e fornecendo `login()`, `logout()` e cabeçalho `Authorization: Bearer <token>` para todas as requisições.

---

## Fluxo de Dados

```
1. UBS registra atendimento no e-SUS PEC
   └─→ Dados salvos no PostgreSQL (schema public)

2. Script de setup cria views materializadas
   └─→ python scripts/setup.py
   └─→ Cria schema dashboard + 5 views + schema auth

3. Normalização de bairros (opcional mas recomendado)
   └─→ python scripts/normalizar_bairros.py
   └─→ Cria tb_bairros_mapeamento (ViaCEP + fuzzy)

4. Backend serve dados processados via REST API
   └─→ Analytics queries sobre as views
   └─→ ML predictions via modelo treinado
   └─→ Auth via JWT (roles: admin/operador/leitor)

5. Frontend exibe dashboards interativos
   └─→ Gráficos, mapas, tabelas, predições
```

---

## Decisões Arquiteturais

| Decisão | Razão |
|---------|-------|
| **Views materializadas** (não tabelas ETL) | Dados sempre derivados do original; basta dar REFRESH |
| **DISTINCT ON** em mv_pa_cadastros | Deduplicação: cidadãos recadastrados teriam contagem inflada |
| **TimeSeriesSplit** no ML | Evita data leakage temporal — treina no passado, valida no futuro |
| **ViaCEP + fuzzy** para bairros | 2 camadas: CEP quando disponível, matching por similaridade quando não |
| **Schema separado** (dashboard) | Isolamento dos dados brutos do e-SUS — não altera schema public |
| **Modelos salvos em disco** (.joblib) | Simples e eficiente para o escopo atual; sem necessidade de MLflow |
| **IMC recalculado** (não armazenado) | Valor bruto no e-SUS pode ter erros; recalcular de peso/altura é mais confiável |
| **Schema auth separado** | Dados de autenticação isolados dos dados clínicos |
| **FDW/single mode** | Não modificar o banco do e-SUS PEC em produção (modo fdw recomendado) |
