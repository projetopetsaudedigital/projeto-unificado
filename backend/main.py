"""
Plataforma de Saúde Pública — Backend FastAPI

Iniciar:
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

Documentação automática:
    http://localhost:8000/docs
"""

import sys
from pathlib import Path

# Garante encoding UTF-8 no Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.modules.pressao_arterial.routes.health import router as health_router
from app.modules.pressao_arterial.routes.qualidade import router as qualidade_router
from app.modules.pressao_arterial.routes.analytics import router as analytics_router
from app.modules.pressao_arterial.routes.admin import router as admin_router
from app.modules.pressao_arterial.routes.ml import router as ml_router
from app.modules.diabetes.routes.analytics import router as dm_analytics_router
from app.modules.diabetes.routes.ml import router as dm_ml_router
from app.auth.routes import router as auth_router

logger = setup_logging("main")

APP_DESCRIPTION = """
Backend para análise epidemiológica da **Atenção Básica**, construído sobre o banco do
**e-SUS PEC** (Prontuário Eletrônico do Cidadão). Cobre hipertensão arterial, diabetes
mellitus, obesidade e predição de risco individual via Machine Learning.

---

## Pré-requisitos

- **Python** 3.10+
- **Node.js** 18+ (apenas para o frontend)
- **PostgreSQL** 12+ com o banco do e-SUS PEC disponível
- **Git**

---

## Passo 1 — Configurar o backend

```bash
cd plataforma-saude/backend

# 1. Criar e ativar o ambiente virtual
python -m venv venv
venv\\Scripts\\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Criar o arquivo de configuração
copy .env.example .env       # Windows
# cp .env.example .env       # Linux/Mac
```

Edite o arquivo `.env` com as credenciais dos dois bancos de dados:

| Variável | Descrição | Padrão |
|----------|-----------|--------|
| `DB_HOST` | Host do PostgreSQL (banco PEC, somente leitura) | `localhost` |
| `DB_PORT` | Porta do PostgreSQL | `5432` |
| `DB_NAME` | Nome do banco e-SUS PEC | `pet_saude` |
| `DB_USER` | Usuário do banco PEC | `postgres` |
| `DB_PASSWORD` | Senha do banco PEC | *(obrigatorio)* |
| `ADMIN_DB_HOST` | Host do banco admin (leitura/escrita) | `localhost` |
| `ADMIN_DB_PORT` | Porta do banco admin | `5432` |
| `ADMIN_DB_NAME` | Nome do banco admin | `admin-esus` |
| `ADMIN_DB_USER` | Usuário do banco admin | `postgres` |
| `ADMIN_DB_PASSWORD` | Senha do banco admin | *(obrigatorio)* |
| `JWT_SECRET_KEY` | Chave secreta JWT — **troque em producao!** | *(obrigatorio)* |
| `JWT_EXPIRE_HOURS` | Validade do token em horas | `8` |

> **Dica:** gere uma chave segura com `openssl rand -hex 32`

---

## Passo 2 — Configurar o banco de dados

Execute o script de setup uma unica vez. Ele cria o schema `dashboard`, as views
materializadas e a tabela de auditoria no banco admin:

```bash
python scripts/setup.py
```

---

## Passo 3 — Processos adicionais (analise geografica)

Necessario para os endpoints de mapa e prevalencia por bairro:

```bash
# Normaliza os nomes de bairros do e-SUS (fuzzy matching + VDC)
python scripts/normalizar_bairros.py

# Migra a view de cadastros para deduplicacao (1 cidadao = 1 registro)
python scripts/migrar_mv_cadastros.py
```

---

## Passo 4 — Iniciar a API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

A API estara disponivel em:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Passo 5 — Frontend (opcional)

```bash
cd plataforma-saude/frontend
npm install
npm run dev
```

O frontend React estara em: http://localhost:5173

---

## Autenticacao

Todos os endpoints (exceto `/api/v1/health`) requerem autenticacao via **JWT Bearer token**.

1. Chame `POST /api/v1/auth/login` com `email` e `password`
2. Copie o campo `access_token` da resposta
3. No Swagger, clique em **Authorize** (cadeado) e cole o token

Roles disponiveis: `admin`, `operador`, `leitor`.
"""

TAGS_METADATA = [
    {
        "name": "health",
        "description": "Verifica disponibilidade da API e conectividade com os bancos de dados (PEC e Admin).",
    },
    {
        "name": "auth",
        "description": (
            "Autenticacao JWT e gerenciamento de usuarios. "
            "Use `POST /auth/login` para obter o token e clique em **Authorize** no topo da pagina."
        ),
    },
    {
        "name": "analytics",
        "description": (
            "Analises epidemiologicas de **hipertensao arterial**: KPIs gerais, evolucao temporal, "
            "prevalencia por bairro/sexo/faixa etaria, fatores de risco, mapa coropletico e analise por UBS. "
            "Fonte: views materializadas `mv_pa_medicoes` e `mv_pa_cadastros` no schema `dashboard`."
        ),
    },
    {
        "name": "qualidade",
        "description": (
            "Monitoramento de qualidade de dados de pressao arterial: deteccao de outliers (Z-score + IQR), "
            "fila de revisao manual, pipeline de auditoria e status das views materializadas."
        ),
    },
    {
        "name": "ml",
        "description": (
            "Pipeline de **Machine Learning para hipertensao arterial**: treinamento de modelo "
            "RandomForest com validacao TimeSeriesSplit, metricas de performance e predicao de risco "
            "individual a partir de perfil demografico e comorbidades."
        ),
    },
    {
        "name": "admin",
        "description": (
            "Administracao da plataforma: status dos componentes (schema, views, migracoes), "
            "refresh manual de views materializadas, historico de processamentos, "
            "sincronizacao da base geografica (GeoJSON) e geocodificacao de bairros via Nominatim."
        ),
    },
    {
        "name": "diabetes-analytics",
        "description": (
            "Analises epidemiologicas de **diabetes mellitus**: KPIs, evolucao de HbA1c, "
            "distribuicao por faixa de valor, controle glicemico por grupo demografico e bairro, "
            "e analise de comorbidades em pacientes controlados vs nao controlados."
        ),
    },
    {
        "name": "diabetes-ml",
        "description": (
            "Pipeline de **Machine Learning para diabetes**: treinamento de modelo de predicao "
            "de controle glicemico, metricas e inferencia individual a partir de perfil do paciente diabetico."
        ),
    },
]

app = FastAPI(
    title="Plataforma de Saude Publica — API",
    description=APP_DESCRIPTION,
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
    license_info={"name": "Uso academico interno"},
)

# CORS — permite requisições do frontend React (localhost:3000 em dev)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(qualidade_router, prefix="/api/v1/pressao-arterial", tags=["qualidade"])
app.include_router(analytics_router, prefix="/api/v1/pressao-arterial", tags=["analytics"])
app.include_router(admin_router,    prefix="/api/v1/pressao-arterial/admin", tags=["admin"])
app.include_router(ml_router,          prefix="/api/v1/pressao-arterial",       tags=["ml"])
app.include_router(dm_analytics_router, prefix="/api/v1/diabetes",              tags=["diabetes-analytics"])
app.include_router(dm_ml_router,        prefix="/api/v1/diabetes",              tags=["diabetes-ml"])
app.include_router(auth_router,         prefix="/api/v1",                       tags=["auth"])


@app.on_event("startup")
async def startup_event():
    logger.info("=" * 60)
    logger.info("Plataforma de Saúde Pública — API iniciada")
    logger.info(f"Ambiente: {settings.ENVIRONMENT}")
    logger.info(f"Banco PEC: {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME} (somente leitura)")
    logger.info(f"Banco Admin: {settings.ADMIN_DB_HOST}:{settings.ADMIN_DB_PORT}/{settings.ADMIN_DB_NAME} (leitura/escrita)")
    logger.info("Documentação: http://localhost:8000/docs")
    logger.info("=" * 60)


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("API encerrada.")
