# Referência da API — Plataforma de Saúde Pública

Documentação completa de todos os endpoints REST. A documentação interativa (Swagger UI) está disponível em `http://localhost:8000/docs` quando a API estiver rodando.

---

## Informações Gerais

| Propriedade | Valor |
|-------------|-------|
| **Base URL** | `http://localhost:8000` |
| **Prefixo** | `/api/v1` |
| **Formato** | JSON (Content-Type: application/json) |
| **Autenticação** | JWT Bearer Token |
| **OpenAPI JSON** | `http://localhost:8000/openapi.json` |
| **ReDoc** | `http://localhost:8000/redoc` |

---

## Autenticação

Todos os endpoints (exceto `GET /api/v1/health`) requerem **JWT Bearer Token**.

### Obter o token

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "admin@saude.gov.br",
  "senha": "sua_senha"
}
```

**Resposta:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer",
  "usuario": {
    "id": 1,
    "nome": "Administrador",
    "email": "admin@saude.gov.br",
    "perfil": "admin"
  }
}
```

### Usar o token

Inclua o token em todas as requisições:

```http
Authorization: Bearer eyJhbGci...
```

No Swagger UI, clique em **Authorize** (ícone de cadeado) e cole o token.

### Roles

| Perfil | Permissões |
|--------|-----------|
| `admin` | Acesso total — leitura, escrita, gerenciamento de usuários |
| `operador` | Leitura + operações de escrita (refresh de views, treinamento) |
| `leitor` | Somente leitura dos dashboards |

---

## Parâmetros de Filtro Comuns

A maioria dos endpoints de analytics aceita os seguintes query params:

| Parâmetro | Tipo | Descrição |
|-----------|------|-----------|
| `ano_inicio` | int | Ano inicial do filtro temporal |
| `ano_fim` | int | Ano final do filtro temporal |
| `bairro` | string | Filtrar por bairro (`no_bairro_filtro`) |
| `co_unidade_saude` | int | Filtrar por UBS (código da unidade) |
| `sexo` | string | Filtrar por sexo: `M` ou `F` |

---

## Tag: health

### `GET /api/v1/health`

Verifica a disponibilidade da API e a conectividade com os bancos de dados.

**Autenticação:** Não requerida.

**Resposta 200:**
```json
{
  "status": "ok",
  "banco_pec": "conectado",
  "banco_admin": "conectado",
  "views": {
    "mv_pa_cadastros": "ok",
    "mv_pa_medicoes": "ok",
    "mv_dm_hemoglobina": "ok",
    "mv_obesidade": "ok"
  }
}
```

---

## Tag: auth

### `POST /api/v1/auth/login`

Autentica com email e senha, retorna JWT Bearer token.

**Body:**
```json
{
  "email": "string",
  "senha": "string"
}
```

---

### `GET /api/v1/auth/me`

Retorna os dados do usuário autenticado.

**Resposta 200:**
```json
{
  "id": 1,
  "nome": "João Silva",
  "email": "joao@saude.gov.br",
  "perfil": "operador"
}
```

---

### `GET /api/v1/auth/usuarios`

Lista todos os usuários cadastrados. **Requer perfil admin.**

---

### `POST /api/v1/auth/usuarios`

Cria um novo usuário. **Requer perfil admin.**

**Body:**
```json
{
  "nome": "Maria Santos",
  "email": "maria@saude.gov.br",
  "senha": "senha_segura",
  "perfil": "leitor"
}
```

Perfis válidos: `admin`, `operador`, `leitor`.

---

## Tag: analytics (Hipertensão Arterial)

### `GET /api/v1/pressao-arterial/kpis`

KPIs gerais de hipertensão arterial.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`, `sexo`

**Resposta:**
```json
{
  "total_cadastros": 15420,
  "total_hipertensos": 5634,
  "prevalencia_pct": 36.5,
  "media_pas": 128.4,
  "media_pad": 82.1,
  "total_medicoes": 42300
}
```

---

### `GET /api/v1/pressao-arterial/prevalencia`

Prevalência de hipertensão por bairro, sexo e faixa etária.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`, `sexo`

---

### `GET /api/v1/pressao-arterial/fatores-risco`

Prevalência de comorbidades e fatores de risco na população hipertensa.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`, `sexo`

---

### `GET /api/v1/pressao-arterial/mapa`

Dados georreferenciados para mapa coroplético por bairro.

**Query params:** `ano_inicio`, `ano_fim`

**Nota:** Requer importação de GeoJSON (ver `scripts/importar_geojson.py`).

---

### `GET /api/v1/pressao-arterial/ubs`

Análise comparativa entre Unidades Básicas de Saúde.

**Query params:** `ano_inicio`, `ano_fim`

---

### `GET /api/v1/pressao-arterial/tendencia`

Evolução temporal mensal de indicadores de pressão arterial.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`, `sexo`

---

### `GET /api/v1/pressao-arterial/bairros/exportar`

Exporta indicadores por bairro em formato JSON para uso externo.

---

## Tag: qualidade

### `GET /api/v1/pressao-arterial/qualidade/outliers`

Lista medições de PA identificadas como outliers (Z-score ou IQR).

**Query params:** `limite` (padrão: 50), `revisado` (booleano)

---

### `GET /api/v1/pressao-arterial/qualidade/fila-revisao`

Fila de outliers pendentes de revisão manual.

---

### `POST /api/v1/pressao-arterial/qualidade/revisar/{id}`

Marca um outlier como revisado manualmente.

---

### `GET /api/v1/pressao-arterial/qualidade/auditoria`

Histórico completo de outliers auditados.

---

## Tag: ml (Hipertensão Arterial)

### `GET /api/v1/pressao-arterial/modelo/info`

Status e métricas do modelo de risco de HAS.

**Resposta:**
```json
{
  "modelo_treinado": true,
  "treinado_em": "2026-03-06T19:30:00",
  "total_registros": 15000,
  "metricas": {
    "roc_auc": {"media": 0.812, "std": 0.023},
    "f1": {"media": 0.745, "std": 0.031}
  },
  "feature_importances": {
    "idade": 0.35,
    "st_diabetes": 0.12
  },
  "treino_em_andamento": false
}
```

---

### `POST /api/v1/pressao-arterial/modelo/treinar`

Inicia o treinamento do modelo de risco HAS em background.

**Resposta:**
```json
{
  "status": "iniciado",
  "mensagem": "Treinamento iniciado em background."
}
```

---

### `GET /api/v1/pressao-arterial/modelo/status-treino`

Verifica se o treinamento está em andamento.

**Resposta:**
```json
{ "treino_em_andamento": false }
```

---

### `POST /api/v1/pressao-arterial/predizer-risco`

Predição de risco individual de hipertensão arterial.

**Body:**
```json
{
  "idade": 55,
  "co_dim_sexo": 3,
  "st_diabetes": 1,
  "st_fumante": 0,
  "st_alcool": 0,
  "st_outra_droga": 0,
  "st_doenca_cardiaca": 1,
  "st_problema_rins": 0,
  "st_avc": 0,
  "st_infarto": 0,
  "st_doenca_respiratoria": 0,
  "st_cancer": 0,
  "st_hanseniase": 0,
  "st_tuberculose": 0
}
```

Campos binários omitidos são tratados como `0`.

**Resposta:**
```json
{
  "probabilidade_risco": 0.42,
  "nivel_risco": "alto",
  "fatores_principais": ["idade", "st_diabetes", "st_doenca_cardiaca"]
}
```

---

## Tag: admin

### `GET /api/v1/pressao-arterial/admin/status`

Status de todos os componentes: schema, views materializadas, tabelas de controle.

---

### `POST /api/v1/pressao-arterial/admin/refresh/{view}`

Executa `REFRESH MATERIALIZED VIEW CONCURRENTLY` na view especificada.

**Views válidas:** `mv_pa_medicoes`, `mv_pa_cadastros`, `mv_pa_medicoes_cidadaos`

**Resposta:**
```json
{
  "status": "concluido",
  "view": "mv_pa_cadastros",
  "duracao_segundos": 12.4
}
```

---

### `GET /api/v1/pressao-arterial/admin/historico`

Histórico de processamentos registrado em `tb_controle_processamento`.

---

### `POST /api/v1/pressao-arterial/admin/geocodificar`

Inicia geocodificação de bairros via Nominatim (offline/online).

---

## Tag: diabetes-analytics

### `GET /api/v1/diabetes/kpis`

KPIs gerais de diabetes mellitus.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`, `sexo`

**Resposta:**
```json
{
  "total_diabeticos": 2340,
  "total_exames_hba1c": 1820,
  "pct_controlados": 58.3,
  "hba1c_media": 7.8,
  "pct_adultos_controlados": 61.2,
  "pct_idosos_controlados": 54.1
}
```

---

### `GET /api/v1/diabetes/controle`

Controle glicêmico por grupo etário, sexo e bairro.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`, `sexo`

---

### `GET /api/v1/diabetes/tendencia`

Evolução temporal mensal de HbA1c e taxas de controle.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`

---

### `GET /api/v1/diabetes/bairros`

Controle glicêmico médio e prevalência por bairro.

**Query params:** `ano_inicio`, `ano_fim`, `co_unidade_saude`

---

## Tag: diabetes-ml

### `GET /api/v1/diabetes/modelo/info`

Status e métricas do modelo de controle glicêmico.

---

### `POST /api/v1/diabetes/modelo/treinar`

Inicia o treinamento do modelo de controle glicêmico em background.

---

### `GET /api/v1/diabetes/modelo/status-treino`

Verifica se o treinamento está em andamento.

---

### `POST /api/v1/diabetes/predizer-controle`

Predição individual de controle glicêmico para paciente diabético.

**Body:**
```json
{
  "idade": 68,
  "co_dim_sexo": 1,
  "hba1c": 7.2,
  "st_hipertensao": 1,
  "st_doenca_cardiaca": 0,
  "st_insuf_cardiaca": 0,
  "st_infarto": 0,
  "st_problema_rins": 0,
  "st_avc": 0,
  "st_fumante": 0,
  "st_alcool": 0,
  "st_doenca_respiratoria": 0,
  "st_cancer": 0
}
```

**Resposta:**
```json
{
  "probabilidade_controlado": 0.67,
  "classificacao": "controlado",
  "threshold_aplicado": 7.5,
  "grupo_etario": "idoso_65_79"
}
```

---

## Tag: obesidade-analytics

### `GET /api/v1/obesidade/kpis`

KPIs gerais de obesidade e IMC.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`, `sexo`

**Resposta:**
```json
{
  "total_medicoes": 28450,
  "adultos_unicos": 12300,
  "imc_medio": 26.8,
  "pct_sobrepeso": 34.2,
  "pct_obesidade_g1": 18.5,
  "pct_obesidade_g2": 7.3,
  "pct_obesidade_g3": 2.8,
  "tendencia_mensal": "+0.012"
}
```

---

### `GET /api/v1/obesidade/tendencia`

Série mensal com IMC médio e distribuição das classes ao longo do tempo.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`

---

### `GET /api/v1/obesidade/distribuicao`

Distribuição das 6 classes OMS de IMC (total, por sexo e por faixa etária).

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`

---

### `GET /api/v1/obesidade/fatores-risco`

Prevalência de comorbidades estratificada por cada classificação de IMC.

**Query params:** `ano_inicio`, `ano_fim`, `bairro`, `co_unidade_saude`

---

### `GET /api/v1/obesidade/bairros`

IMC médio, total de medições/adultos e prevalência de obesidade por bairro.

Retorna apenas bairros com pelo menos 10 medições.

**Query params:** `ano_inicio`, `ano_fim`, `co_unidade_saude`

---

## Tag: obesidade-ml

### `GET /api/v1/obesidade/modelo/info`

Status e métricas do modelo de classificação de IMC.

**Resposta:**
```json
{
  "modelo_treinado": true,
  "treinado_em": "2026-03-07T10:15:00",
  "total_registros": 24800,
  "metricas": {
    "acuracia": {"media": 0.94, "std": 0.02},
    "macro_f1": {"media": 0.87, "std": 0.03}
  },
  "metricas_por_classe": {
    "baixo_peso": {"f1": 0.71},
    "normal": {"f1": 0.95},
    "sobrepeso": {"f1": 0.92},
    "obesidade_1": {"f1": 0.89},
    "obesidade_2": {"f1": 0.82},
    "obesidade_3": {"f1": 0.76}
  },
  "treino_em_andamento": false
}
```

---

### `POST /api/v1/obesidade/modelo/treinar`

Inicia o treinamento do modelo de classificação de IMC em background.

---

### `GET /api/v1/obesidade/modelo/status-treino`

Verifica se o treinamento está em andamento.

---

### `POST /api/v1/obesidade/predizer-imc`

Predição individual de classificação de IMC.

**Body:**
```json
{
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
}
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

## Referência Rápida — Todos os Endpoints

| Método | Endpoint | Tag | Auth |
|--------|----------|-----|------|
| GET | `/api/v1/health` | health | Não |
| POST | `/api/v1/auth/login` | auth | Não |
| GET | `/api/v1/auth/me` | auth | Sim |
| GET | `/api/v1/auth/usuarios` | auth | Admin |
| POST | `/api/v1/auth/usuarios` | auth | Admin |
| GET | `/api/v1/pressao-arterial/kpis` | analytics | Sim |
| GET | `/api/v1/pressao-arterial/prevalencia` | analytics | Sim |
| GET | `/api/v1/pressao-arterial/fatores-risco` | analytics | Sim |
| GET | `/api/v1/pressao-arterial/mapa` | analytics | Sim |
| GET | `/api/v1/pressao-arterial/ubs` | analytics | Sim |
| GET | `/api/v1/pressao-arterial/tendencia` | analytics | Sim |
| GET | `/api/v1/pressao-arterial/bairros/exportar` | analytics | Sim |
| GET | `/api/v1/pressao-arterial/qualidade/outliers` | qualidade | Sim |
| GET | `/api/v1/pressao-arterial/qualidade/fila-revisao` | qualidade | Sim |
| POST | `/api/v1/pressao-arterial/qualidade/revisar/{id}` | qualidade | Sim |
| GET | `/api/v1/pressao-arterial/qualidade/auditoria` | qualidade | Sim |
| GET | `/api/v1/pressao-arterial/modelo/info` | ml | Sim |
| POST | `/api/v1/pressao-arterial/modelo/treinar` | ml | Sim |
| GET | `/api/v1/pressao-arterial/modelo/status-treino` | ml | Sim |
| POST | `/api/v1/pressao-arterial/predizer-risco` | ml | Sim |
| GET | `/api/v1/pressao-arterial/admin/status` | admin | Sim |
| POST | `/api/v1/pressao-arterial/admin/refresh/{view}` | admin | Sim |
| GET | `/api/v1/pressao-arterial/admin/historico` | admin | Sim |
| POST | `/api/v1/pressao-arterial/admin/geocodificar` | admin | Sim |
| GET | `/api/v1/diabetes/kpis` | diabetes-analytics | Sim |
| GET | `/api/v1/diabetes/controle` | diabetes-analytics | Sim |
| GET | `/api/v1/diabetes/tendencia` | diabetes-analytics | Sim |
| GET | `/api/v1/diabetes/bairros` | diabetes-analytics | Sim |
| GET | `/api/v1/diabetes/modelo/info` | diabetes-ml | Sim |
| POST | `/api/v1/diabetes/modelo/treinar` | diabetes-ml | Sim |
| GET | `/api/v1/diabetes/modelo/status-treino` | diabetes-ml | Sim |
| POST | `/api/v1/diabetes/predizer-controle` | diabetes-ml | Sim |
| GET | `/api/v1/obesidade/kpis` | obesidade-analytics | Sim |
| GET | `/api/v1/obesidade/tendencia` | obesidade-analytics | Sim |
| GET | `/api/v1/obesidade/distribuicao` | obesidade-analytics | Sim |
| GET | `/api/v1/obesidade/fatores-risco` | obesidade-analytics | Sim |
| GET | `/api/v1/obesidade/bairros` | obesidade-analytics | Sim |
| GET | `/api/v1/obesidade/modelo/info` | obesidade-ml | Sim |
| POST | `/api/v1/obesidade/modelo/treinar` | obesidade-ml | Sim |
| GET | `/api/v1/obesidade/modelo/status-treino` | obesidade-ml | Sim |
| POST | `/api/v1/obesidade/predizer-imc` | obesidade-ml | Sim |

---

## Códigos de Status HTTP

| Código | Situação |
|--------|---------|
| 200 | Sucesso |
| 201 | Criado com sucesso (POST de usuário) |
| 400 | Dados inválidos no body da requisição |
| 401 | Token ausente ou inválido |
| 403 | Perfil sem permissão para esta operação |
| 404 | Recurso não encontrado |
| 409 | Conflito (ex: email já cadastrado) |
| 500 | Erro interno do servidor (ver logs em `backend/logs/`) |
