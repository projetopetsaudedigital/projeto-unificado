# Plataforma de Saúde Pública

Sistema de análise epidemiológica e gestão de dados da **Atenção Básica**, construído sobre o banco do **e-SUS PEC** (Prontuário Eletrônico do Cidadão).

## O que faz

| Módulo | Funcionalidades |
|--------|----------------|
| **Hipertensão Arterial (HAS)** | Dashboard de prevalência, fatores de risco, mapa por bairro, análise por UBS, qualidade de dados, predição de risco individual via ML |
| **Diabetes Mellitus (DM)** | Dashboard de controle glicêmico (HbA1c), tendências temporais, análise por bairro, predição de risco via ML |
| **Obesidade (OB)** | Dashboard de IMC, distribuição das 6 classes OMS, comorbidades por faixa de IMC, evolução temporal, predição de classificação via ML |
| **Administração** | Setup guiado do banco, refresh de views, normalização de bairros, geocodificação, treinamento de modelos |

## Stack Tecnológica

- **Backend:** Python 3.10+ / FastAPI / SQLAlchemy / scikit-learn
- **Frontend:** React 19 / Vite 7 / TailwindCSS v4 / Recharts / Leaflet
- **Banco:** PostgreSQL (e-SUS PEC) com schema `dashboard` (views materializadas) e `auth` (usuários)
- **ML:** RandomForestClassifier com validação TimeSeriesSplit
- **Auth:** JWT Bearer (roles: admin, operador, leitor)

## Pré-requisitos

- Python 3.10+
- Node.js 18+
- PostgreSQL 12+ (com banco do e-SUS PEC)
- Git

> Para guia completo de instalação passo a passo, veja [docs/INICIALIZACAO.md](docs/INICIALIZACAO.md).

## Setup Rápido

### 1. Backend

```bash
cd plataforma-saude/backend

# Criar ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Instalar dependências
pip install -r requirements.txt

# Configurar credenciais
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
# Edite o .env com suas credenciais do PostgreSQL

# Configurar banco (schema, views materializadas, auth, auditoria)
python scripts/setup.py --all
# Flags disponíveis: --all | --auth | --views-pa | --views-dm | --normalizacao

# Iniciar API
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

A documentação da API estará em: http://localhost:8000/docs

### 2. Frontend

```bash
cd plataforma-saude/frontend

# Instalar dependências
npm install

# Iniciar dev server
npm run dev
```

O frontend estará em: http://localhost:5173

### 3. Processamentos Adicionais (ver [docs/PROCESSAMENTOS.md](docs/PROCESSAMENTOS.md))

```bash
cd plataforma-saude/backend

# Normalização de bairros (necessário para análise geográfica)
python scripts/normalizar_bairros.py

# Migração de deduplicação (1 cidadão = 1 registro)
python scripts/migrar_mv_cadastros.py
```

## Estrutura do Projeto

```
plataforma-saude/
├── backend/
│   ├── main.py                    # Entry point FastAPI
│   ├── app/
│   │   ├── core/                  # Config, database, logging
│   │   ├── auth/                  # JWT, login, usuários (roles: admin/operador/leitor)
│   │   └── modules/
│   │       ├── pressao_arterial/  # Módulo de hipertensão
│   │       │   ├── routes/        # Endpoints REST
│   │       │   ├── analytics/     # Queries analíticas
│   │       │   ├── ml/            # Pipeline + predictor ML
│   │       │   ├── processors/    # Normalização de bairros
│   │       │   ├── quality/       # Auditoria + outliers
│   │       │   └── views/         # Gerenciamento de views
│   │       ├── diabetes/          # Módulo de diabetes
│   │       └── obesidade/         # Módulo de obesidade e IMC
│   ├── scripts/                   # Scripts de setup e processamento
│   ├── sql/                       # DDL das views materializadas
│   └── models/                    # Artefatos ML (.joblib + .json)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx                # Roteamento + Layout
│   │   ├── pages/                 # 15 páginas (HAS, DM, OB, Admin)
│   │   ├── components/            # Componentes reutilizáveis
│   │   ├── api/                   # Camada de comunicação com backend
│   │   └── contexts/              # AuthContext (JWT)
│   └── package.json
│
└── docs/                          # Documentação técnica
    ├── INICIALIZACAO.md
    ├── SWAGGER.md
    ├── ARQUITETURA.md
    ├── MODELOS_ML.md
    ├── PROCESSAMENTOS.md
    ├── DADOS.md
    └── DOCUMENTACAO_TECNICA.md
```

## Documentação

| Documento | Conteúdo |
|-----------|----------|
| [docs/INICIALIZACAO.md](docs/INICIALIZACAO.md) | Guia completo de instalação e primeiro uso |
| [docs/SWAGGER.md](docs/SWAGGER.md) | Referência completa de todos os endpoints da API |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Arquitetura do sistema, fluxo de dados, schema |
| [docs/MODELOS_ML.md](docs/MODELOS_ML.md) | Features, treinamento, métricas, como retreinar (3 modelos) |
| [docs/PROCESSAMENTOS.md](docs/PROCESSAMENTOS.md) | Normalização, views, deduplicação, controle |
| [docs/DADOS.md](docs/DADOS.md) | Tabelas do e-SUS PEC usadas, campos críticos |
| [docs/DOCUMENTACAO_TECNICA.md](docs/DOCUMENTACAO_TECNICA.md) | Guia completo de arquivos e funções para desenvolvedores |

## API Endpoints Principais

A documentação interativa completa está em `http://localhost:8000/docs`. Para referência offline, veja [docs/SWAGGER.md](docs/SWAGGER.md).

### Autenticação

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/api/v1/auth/login` | Login com email + senha → JWT |
| GET | `/api/v1/auth/me` | Dados do usuário logado |
| GET | `/api/v1/auth/usuarios` | Listar usuários (admin) |
| POST | `/api/v1/auth/usuarios` | Criar usuário (admin) |

### Health

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/health` | Health check (conexão DB, status views) |

### Hipertensão Arterial

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/pressao-arterial/kpis` | KPIs de hipertensão |
| GET | `/api/v1/pressao-arterial/prevalencia` | Prevalência por bairro |
| GET | `/api/v1/pressao-arterial/fatores-risco` | Fatores de risco e comorbidades |
| GET | `/api/v1/pressao-arterial/mapa` | Dados geográficos para mapa coroplético |
| GET | `/api/v1/pressao-arterial/ubs` | Análise por UBS |
| POST | `/api/v1/pressao-arterial/modelo/treinar` | Treinar modelo HAS |
| POST | `/api/v1/pressao-arterial/predizer-risco` | Predição individual HAS |
| GET | `/api/v1/pressao-arterial/admin/status` | Status dos componentes |
| POST | `/api/v1/pressao-arterial/admin/refresh/{view}` | Refresh de view materializada |

### Diabetes Mellitus

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/diabetes/kpis` | KPIs de diabetes |
| GET | `/api/v1/diabetes/controle` | Controle glicêmico por grupo |
| GET | `/api/v1/diabetes/tendencia` | Tendências de HbA1c |
| GET | `/api/v1/diabetes/bairros` | Controle por bairro |
| POST | `/api/v1/diabetes/modelo/treinar` | Treinar modelo DM |
| POST | `/api/v1/diabetes/predizer-controle` | Predição individual DM |

### Obesidade

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/api/v1/obesidade/kpis` | KPIs de IMC e obesidade |
| GET | `/api/v1/obesidade/tendencia` | Evolução temporal do IMC |
| GET | `/api/v1/obesidade/distribuicao` | Distribuição das 6 classes OMS |
| GET | `/api/v1/obesidade/fatores-risco` | Comorbidades por classificação de IMC |
| GET | `/api/v1/obesidade/bairros` | IMC médio e obesidade por bairro |
| POST | `/api/v1/obesidade/modelo/treinar` | Treinar modelo de classificação de IMC |
| POST | `/api/v1/obesidade/predizer-imc` | Predição individual de classificação de IMC |

## Variáveis de Ambiente

Ver `.env.example` para a lista completa. As mais importantes:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DB_MODE` | Modo: `fdw` (dois bancos) ou `single` (um banco) | `fdw` |
| `DB_HOST` | Host do PostgreSQL (banco PEC — somente leitura) | `localhost` |
| `DB_PORT` | Porta do PostgreSQL | `5432` |
| `DB_NAME` | Nome do banco e-SUS PEC | `pet_saude` |
| `DB_USER` | Usuário do banco PEC | `postgres` |
| `DB_PASSWORD` | Senha do banco PEC | *(obrigatório)* |
| `ADMIN_DB_HOST` | Host do banco admin (leitura/escrita, só em modo fdw) | `localhost` |
| `ADMIN_DB_NAME` | Nome do banco admin | `admin-esus` |
| `ADMIN_DB_PASSWORD` | Senha do banco admin | *(obrigatório em fdw)* |
| `JWT_SECRET_KEY` | Chave secreta JWT — gere com `openssl rand -hex 32` | *(obrigatório)* |
| `JWT_EXPIRE_HOURS` | Validade do token em horas | `8` |

## Licença

Projeto acadêmico — uso interno.
