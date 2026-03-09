# Guia de Inicialização — Plataforma de Saúde Pública

Guia passo a passo para instalar e colocar a plataforma em funcionamento do zero. Siga as etapas na ordem indicada.

---

## Pré-requisitos

Instale as seguintes ferramentas antes de começar:

| Ferramenta | Versão mínima | Verificar |
|------------|---------------|-----------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| PostgreSQL | 12+ | `psql --version` |
| Git | qualquer | `git --version` |

**Banco de dados:** Você precisa ter acesso ao banco PostgreSQL do **e-SUS PEC** da sua instalação municipal. O banco deve estar acessível via rede (host, porta, usuário e senha).

---

## Etapa 1 — Obter o Código

```bash
# Clonar o repositório (ou copiar os arquivos para o servidor)
git clone <url-do-repositorio> plataforma-saude
cd plataforma-saude
```

---

## Etapa 2 — Entender os Modos de Banco de Dados

Antes de configurar, escolha o modo de banco de dados:

### Modo `fdw` (recomendado para produção)

Usa **dois bancos separados**:
- **Banco PEC** (`pet_saude`): banco do e-SUS PEC — **somente leitura**. A plataforma nunca altera este banco.
- **Banco Admin** (`admin-esus`): banco separado onde serão criadas as views materializadas, tabelas de controle e schema `auth`.

```
┌──────────────────┐    ┌─────────────────────┐
│   pet_saude      │    │   admin-esus         │
│   (e-SUS PEC)    │    │   (views, auth,      │
│   somente leitura│◄───│    controle)         │
└──────────────────┘    └─────────────────────┘
```

Requer criar o banco `admin-esus` previamente:
```sql
-- Execute no PostgreSQL como superusuário:
CREATE DATABASE "admin-esus" OWNER postgres;
```

### Modo `single` (mais simples, para desenvolvimento)

Tudo em um único banco — as views são criadas no próprio banco do e-SUS PEC.

> **Atenção:** Em produção, use `fdw` para não correr o risco de alterar dados do e-SUS PEC.

---

## Etapa 3 — Configurar o Backend

### 3.1 Criar ambiente virtual Python

```bash
cd plataforma-saude/backend

# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate

# Ativar (Linux/Mac)
# source venv/bin/activate
```

Você verá `(venv)` no início do prompt quando o ambiente estiver ativo.

### 3.2 Instalar dependências

```bash
pip install -r requirements.txt
```

Isso instala FastAPI, SQLAlchemy, scikit-learn, pandas, geopandas e todas as dependências. Pode levar 2-5 minutos.

### 3.3 Criar o arquivo `.env`

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Abra o arquivo `.env` em um editor e preencha as credenciais:

```env
# Ambiente
ENVIRONMENT=development

# Modo de banco: "fdw" (dois bancos) ou "single" (um banco)
DB_MODE=fdw

# ── Banco PEC (e-SUS — somente leitura) ──────────────────────
DB_HOST=localhost
DB_PORT=5432
DB_NAME=pet_saude
DB_USER=postgres
DB_PASSWORD=SUA_SENHA_AQUI

# ── Banco Admin (leitura/escrita — apenas para DB_MODE=fdw) ──
ADMIN_DB_HOST=localhost
ADMIN_DB_PORT=5432
ADMIN_DB_NAME=admin-esus
ADMIN_DB_USER=postgres
ADMIN_DB_PASSWORD=SUA_SENHA_AQUI

# ── Qualidade de dados ────────────────────────────────────────
OUTLIER_ZSCORE_THRESHOLD=3.0
OUTLIER_IQR_FACTOR=1.5
PA_PAS_MIN=50
PA_PAS_MAX=300
PA_PAD_MIN=30
PA_PAD_MAX=200

# ── Autenticação JWT ──────────────────────────────────────────
# IMPORTANTE: gere uma chave segura com: openssl rand -hex 32
JWT_SECRET_KEY=CHANGE-ME-in-production-use-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=8
```

**Gerar chave JWT segura:**
```bash
# Linux/Mac
openssl rand -hex 32

# Windows (PowerShell)
[System.Web.Security.Membership]::GeneratePassword(64, 10)
# Ou instale OpenSSL: https://slproweb.com/products/Win32OpenSSL.html
```

---

## Etapa 4 — Configurar o Banco de Dados

Execute o script de setup. Ele cria o schema `dashboard`, o schema `auth`, as views materializadas e o usuário admin padrão:

```bash
cd plataforma-saude/backend
python scripts/setup.py
```

**O que é criado:**
- Schema `dashboard` com 5 views materializadas e tabelas de controle
- Schema `auth` com tabela de usuários
- Usuário admin padrão (veja a saída do script para as credenciais)

**Verificar se funcionou:**
```bash
# Iniciar a API temporariamente para checar
uvicorn main:app --port 8000

# Em outro terminal:
curl http://localhost:8000/api/v1/health
# Deve retornar: {"status": "ok", ...}
```

---

## Etapa 5 — Processamentos Iniciais

Estes processamentos são necessários para as análises geográficas e geração de mapas.

### 5.1 Migração de deduplicação (se necessário)

```bash
# Verifica e corrige a view de cadastros para 1 registro por cidadão
python scripts/migrar_mv_cadastros.py --dry-run   # verificar primeiro
python scripts/migrar_mv_cadastros.py
```

### 5.2 Normalização de bairros (recomendado)

Necessário para análise por bairro e mapa coroplético. Leva ~20 minutos na primeira execução.

```bash
# Teste com 50 CEPs (~1 minuto)
python scripts/normalizar_bairros.py --limite-ceps 50

# Execução completa
python scripts/normalizar_bairros.py
```

### 5.3 Importar GeoJSON para mapas (opcional)

Se você tiver um arquivo GeoJSON com os polígonos dos bairros do município:

```bash
python scripts/importar_geojson.py --arquivo /caminho/para/bairros.geojson
```

---

## Etapa 6 — Iniciar a API

```bash
cd plataforma-saude/backend

# Garantir que o venv está ativo
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Linux/Mac

# Desenvolvimento (com reload automático)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Produção (sem reload, mais performático)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
```

**Verificar:**
- API: http://localhost:8000/api/v1/health
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Etapa 7 — Instalar e Iniciar o Frontend

```bash
cd plataforma-saude/frontend

# Instalar dependências
npm install

# Desenvolvimento
npm run dev
```

O frontend estará em: **http://localhost:5173**

**Para produção (build estático):**
```bash
npm run build
# Arquivos gerados em: frontend/dist/
# Sirva com Nginx, Apache ou qualquer servidor estático
```

---

## Etapa 8 — Primeiro Acesso

### 8.1 Fazer login

1. Acesse http://localhost:5173
2. A tela de login aparecerá automaticamente
3. Use as credenciais do usuário admin criado pelo `setup.py` (verificar na saída do script)

### 8.2 Explorar o Swagger UI

1. Acesse http://localhost:8000/docs
2. Clique em `POST /api/v1/auth/login`
3. Clique em **Try it out** e preencha email e senha
4. Copie o `access_token` da resposta
5. Clique em **Authorize** (cadeado no topo) e cole o token
6. Agora você pode testar qualquer endpoint

### 8.3 Criar novos usuários (opcional)

Via Swagger ou via API:

```bash
# Primeiro, fazer login para obter o token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@saude.gov.br","senha":"sua_senha"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

# Criar novo usuário
curl -X POST http://localhost:8000/api/v1/auth/usuarios \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "nome": "Coordenador de Saúde",
    "email": "coordenador@saude.gov.br",
    "senha": "senha_segura",
    "perfil": "operador"
  }'
```

---

## Etapa 9 — Treinar os Modelos de Machine Learning

Os modelos precisam ser treinados antes de usar as páginas de predição individual.

```bash
# Obtenha o token primeiro (ver Etapa 8)

# Treinar modelo de Hipertensão
curl -X POST http://localhost:8000/api/v1/pressao-arterial/modelo/treinar \
  -H "Authorization: Bearer $TOKEN"

# Treinar modelo de Diabetes
curl -X POST http://localhost:8000/api/v1/diabetes/modelo/treinar \
  -H "Authorization: Bearer $TOKEN"

# Treinar modelo de Obesidade
curl -X POST http://localhost:8000/api/v1/obesidade/modelo/treinar \
  -H "Authorization: Bearer $TOKEN"
```

O treinamento roda em background. Verifique o status:

```bash
curl http://localhost:8000/api/v1/pressao-arterial/modelo/status-treino \
  -H "Authorization: Bearer $TOKEN"

# Quando concluído, veja as métricas:
curl http://localhost:8000/api/v1/pressao-arterial/modelo/info \
  -H "Authorization: Bearer $TOKEN"
```

Ou use o painel Admin no frontend (`/admin`) para treinar via interface gráfica.

---

## Verificação Final — Checklist

Após concluir todos os passos, verifique cada funcionalidade:

- [ ] `GET /api/v1/health` retorna `"status": "ok"`
- [ ] Login funciona via frontend e Swagger UI
- [ ] Dashboard de Hipertensão (`/`) exibe KPIs
- [ ] Mapa coroplético (`/mapa`) exibe dados por bairro
- [ ] Dashboard de Diabetes (`/diabetes`) exibe KPIs
- [ ] Dashboard de Obesidade (`/obesidade`) exibe KPIs
- [ ] Painel Admin (`/admin`) mostra status dos componentes
- [ ] Modelos treinados (verificar em `/admin` ou via API `/modelo/info`)
- [ ] Predição individual funciona (páginas de Risco)

---

## Troubleshooting

### Erro: `connection refused` ao conectar ao banco

```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Soluções:**
1. Verifique se o PostgreSQL está rodando: `pg_ctl status` ou `service postgresql status`
2. Confirme host, porta, usuário e senha no `.env`
3. Verifique se o usuário tem permissão de leitura no banco do e-SUS PEC

---

### Erro: `venv\Scripts\activate` não funciona no Windows

```
Não é possível carregar o arquivo ... Activate.ps1 porque a execução de scripts está desabilitada
```

**Solução:** Execute no PowerShell como administrador:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### Erro: `ModuleNotFoundError: No module named 'app'`

**Causa:** O arquivo `main.py` não está sendo executado a partir do diretório correto.

**Solução:**
```bash
cd plataforma-saude/backend   # certifique-se de estar neste diretório
uvicorn main:app --reload
```

---

### Erro: `Port 8000 is already in use`

**Solução:**
```bash
# Usar outra porta
uvicorn main:app --reload --port 8001

# Ou matar o processo que está usando a porta (Windows)
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

---

### Erro: `schema "dashboard" does not exist`

**Causa:** O script de setup ainda não foi executado, ou foi executado com erro.

**Solução:**
```bash
cd plataforma-saude/backend
python scripts/setup.py
```

---

### Erro: Views retornam dados vazios

**Causas possíveis:**
1. As views foram criadas mas ainda não foram populadas
2. Os filtros das views excluem todos os dados do banco

**Diagnóstico:**
```bash
# Via API de saúde
curl http://localhost:8000/api/v1/health

# Via SQL direto
psql -U postgres -d admin-esus -c "SELECT COUNT(*) FROM dashboard.mv_pa_cadastros;"
```

**Solução:**
```bash
# Executar REFRESH manualmente
psql -U postgres -d admin-esus -c "REFRESH MATERIALIZED VIEW dashboard.mv_pa_cadastros;"
```

---

### Modelo ML retorna erro "modelo não treinado"

**Solução:** Treinar o modelo conforme Etapa 9. Os artefatos `.joblib` precisam existir em `backend/models/`.

---

### Frontend não conecta ao backend (CORS error)

**Causa:** O Vite faz proxy para `localhost:8000`, mas o backend pode estar em outra porta ou endereço.

**Solução:** Verifique `frontend/vite.config.js` e ajuste o target do proxy se necessário.

---

## Configuração para Produção

Ajustes recomendados antes de colocar em produção:

1. **`.env`:**
   - `ENVIRONMENT=production`
   - `JWT_SECRET_KEY=` chave gerada com `openssl rand -hex 32` (nunca use o valor padrão)
   - Senhas seguras para os bancos de dados

2. **CORS:** Ajuste `ALLOWED_ORIGINS` em `app/core/config.py` para o domínio real

3. **HTTPS:** Use Nginx como reverse proxy com certificado SSL (Let's Encrypt)

4. **Processo:** Use `systemd`, `supervisord` ou Docker para manter a API rodando

5. **Refresh automático:** Configure um cron job para refresh periódico das views:
   ```bash
   # crontab -e
   0 3 * * 0 cd /opt/plataforma-saude/backend && venv/bin/python scripts/setup.py
   ```

6. **Treinamento periódico:** Retreine os modelos mensalmente após o refresh das views
