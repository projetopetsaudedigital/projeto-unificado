# Processamentos

Guia de todos os processamentos de dados da plataforma. Cada seção explica **o que faz**, **quando executar** e **como executar**.

---

## 1. Setup Inicial

**O que faz:** Cria o schema `dashboard`, o schema `auth`, a tabela de auditoria de outliers, as views materializadas e as tabelas de suporte.

**Quando executar:** Na primeira instalação, ou quando o banco for recriado.

**Código:** `scripts/setup.py`

```bash
cd plataforma-saude/backend
python scripts/setup.py
```

**Flags disponíveis:**

```bash
python scripts/setup.py --all            # Tudo (padrão)
python scripts/setup.py --auth           # Apenas schema auth + usuários
python scripts/setup.py --views-pa       # Apenas views de pressão arterial
python scripts/setup.py --views-dm       # Apenas views de diabetes
python scripts/setup.py --normalizacao   # Apenas tabelas de bairros
```

**Passo a passo interno:**
1. Testa conexão com o PostgreSQL
2. Cria schema `dashboard` e schema `auth`
3. Cria `dashboard.tb_auditoria_outliers` e `dashboard.tb_controle_processamento`
4. Cria `auth.tb_usuarios` e usuário admin padrão
5. Executa os SQL em `sql/pressao_arterial/` e `sql/diabetes/`:
   - `mv_pa_medicoes.sql` — medições de PA
   - `mv_pa_cadastros.sql` — cadastros com deduplicação
   - `mv_pa_medicoes_cidadaos.sql` — PA vinculada a cidadão
   - `mv_dm_hemoglobina.sql` — exames HbA1c
   - `vw_bairro_canonico.sql` — view de resolução de bairro
   - `create_audit_table.sql` — tabela de auditoria

---

## 2. Migração de Deduplicação

**O que faz:** Recria `mv_pa_cadastros` usando `DISTINCT ON (co_fat_cidadao_pec)` para manter apenas a ficha mais recente por cidadão.

**Por que é necessário:** Sem deduplicação, um cidadão recadastrado N vezes é contado N vezes na prevalência.

**Código:** `scripts/migrar_mv_cadastros.py`

```bash
# Verificar plano sem executar
python scripts/migrar_mv_cadastros.py --dry-run

# Executar a migração (~1-2 minutos de indisponibilidade)
python scripts/migrar_mv_cadastros.py
```

---

## 3. Normalização de Bairros

**O que faz:** Converte as 2.302+ variações de nomes de bairros em nomes canônicos padronizados.

**Por que é necessário:** O e-SUS armazena bairro como texto livre. Sem normalização, "PATAGÔNIA", "patagonia" e "Patagoinia" são tratados como bairros diferentes.

**Código:** `scripts/normalizar_bairros.py` + `app/modules/pressao_arterial/processors/normalizador_bairros.py`

### Estratégia em 2 camadas

| Camada | Cobertura | Método |
|--------|-----------|--------|
| 1. ViaCEP | ~77% dos registros (com CEP) | Consulta API dos Correios para obter bairro oficial |
| 2. Fuzzy | ~23% restantes (sem CEP) | `rapidfuzz.WRatio` com threshold 80% contra lista canônica do ViaCEP |

### Resultado

Tabela `dashboard.tb_bairros_mapeamento`:

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `no_bairro_raw` | TEXT | Nome original normalizado |
| `no_bairro_canonico` | TEXT | Nome canônico final |
| `tp_origem` | VARCHAR | `'viacep'`, `'fuzzy'` ou `'manual'` |
| `vl_similaridade` | NUMERIC | Score do fuzzy (NULL se ViaCEP) |
| `st_revisado` | SMALLINT | 0=automático, 1=revisado manualmente |

### Como executar

```bash
# Teste rápido (50 CEPs, ~1 minuto)
python scripts/normalizar_bairros.py --limite-ceps 50

# Ver progresso
python scripts/normalizar_bairros.py --status

# Execução completa (~20 minutos)
python scripts/normalizar_bairros.py

# Com threshold de similaridade diferente
python scripts/normalizar_bairros.py --threshold 85
```

**Nota:** A normalização é **incremental** — registros já mapeados são pulados automaticamente. A primeira execução leva ~20 minutos; execuções subsequentes processam apenas novos CEPs.

---

## 4. Importação de GeoJSON

**O que faz:** Importa os dados geoespaciais (polígonos dos bairros/setores) para o banco de dados, habilitando o mapa coroplético do frontend.

**Quando executar:** Uma vez, durante a instalação inicial. Necessário para o endpoint `/api/v1/pressao-arterial/mapa`.

**Código:** `scripts/importar_geojson.py`

```bash
# Importar GeoJSON de bairros
python scripts/importar_geojson.py --arquivo caminho/para/bairros.geojson

# Verificar o que foi importado
python scripts/importar_geojson.py --status
```

**Pré-requisito:** Ter um arquivo GeoJSON com os polígonos dos bairros do município. O arquivo deve conter uma propriedade com o nome do bairro compatível com o e-SUS PEC.

---

## 5. Sincronização da Base Geográfica

**O que faz:** Sincroniza a base geográfica offline com dados externos (Nominatim/OSM), enriquecendo os polígonos e coordenadas dos bairros sem dependência de internet em tempo real.

**Quando executar:** Após importar o GeoJSON, opcionalmente para enriquecer com dados do OpenStreetMap.

**Código:** `scripts/sincronizar_base_geografica.py`

```bash
# Sincronizar todos os bairros
python scripts/sincronizar_base_geografica.py

# Apenas bairros sem coordenadas
python scripts/sincronizar_base_geografica.py --apenas-faltantes
```

---

## 6. Migração de Tipo Geográfico

**O que faz:** Migra o tipo de dado das colunas geográficas no banco (ex: de `TEXT` para `GEOMETRY`), necessário quando a versão do PostGIS muda ou após uma importação em formato diferente.

**Quando executar:** Apenas se solicitado, geralmente após mudança de ambiente ou upgrade de banco.

**Código:** `scripts/migrar_tipo_geo.py`

```bash
python scripts/migrar_tipo_geo.py
```

---

## 7. Refresh das Views Materializadas

**O que faz:** Atualiza as views materializadas para refletir novos dados do e-SUS PEC.

**Quando executar:** Após novos dados serem inseridos no banco do e-SUS (recomendado: semanalmente ou após importação de lotes).

### Via API (recomendado)

```bash
# Refresh individual (requer autenticação JWT)
curl -X POST http://localhost:8000/api/v1/pressao-arterial/admin/refresh/mv_pa_medicoes \
  -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8000/api/v1/pressao-arterial/admin/refresh/mv_pa_cadastros \
  -H "Authorization: Bearer <token>"
curl -X POST http://localhost:8000/api/v1/pressao-arterial/admin/refresh/mv_pa_medicoes_cidadaos \
  -H "Authorization: Bearer <token>"

# Ou via painel admin no frontend: /admin (botões de Refresh)
```

### Via terminal

```bash
# Atualiza schema + views (não requer autenticação)
python scripts/setup.py
```

### Via SQL direto

```sql
REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_pa_medicoes;
REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_pa_cadastros;
REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_pa_medicoes_cidadaos;
REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_dm_hemoglobina;
REFRESH MATERIALIZED VIEW CONCURRENTLY dashboard.mv_obesidade;
```

---

## 8. Treinamento de Modelos ML

**O que faz:** Treina (ou retreina) os modelos de Machine Learning com os dados atuais.

**Quando executar:** Após refresh das views, quando houver volume significativo de novos dados. Recomendado: mensal.

```bash
# Hipertensão (roda em background, 2-5 min)
curl -X POST http://localhost:8000/api/v1/pressao-arterial/modelo/treinar \
  -H "Authorization: Bearer <token>"

# Diabetes
curl -X POST http://localhost:8000/api/v1/diabetes/modelo/treinar \
  -H "Authorization: Bearer <token>"

# Obesidade
curl -X POST http://localhost:8000/api/v1/obesidade/modelo/treinar \
  -H "Authorization: Bearer <token>"

# Verificar status de qualquer treino
curl http://localhost:8000/api/v1/pressao-arterial/modelo/status-treino \
  -H "Authorization: Bearer <token>"
curl http://localhost:8000/api/v1/pressao-arterial/modelo/info \
  -H "Authorization: Bearer <token>"
```

Ver detalhes completos em [MODELOS_ML.md](MODELOS_ML.md).

---

## 9. Exportação de Dados de Bairros

**O que faz:** Gera arquivo JSON com indicadores por bairro para uso externo.

**Código:** `scripts/exportar_bairros.py`

```bash
python scripts/exportar_bairros.py
# Gera: data/bairros_analise.json
```

Ou via API:
```bash
curl http://localhost:8000/api/v1/pressao-arterial/bairros/exportar \
  -H "Authorization: Bearer <token>"
```

---

## Tabela de Controle de Processamento

A tabela `dashboard.tb_controle_processamento` registra quando cada processamento foi executado:

```sql
SELECT tp_processamento, dt_inicio, dt_fim, st_status, ds_modelo
FROM dashboard.tb_controle_processamento
ORDER BY dt_inicio DESC
LIMIT 10;
```

| Campo | Descrição |
|-------|-----------|
| `tp_processamento` | Tipo: `'normalizacao_bairros'`, `'treino_has'`, `'treino_dm'`, `'treino_ob'`, `'refresh_views'` |
| `dt_inicio` / `dt_fim` | Timestamps de início e fim |
| `st_status` | `'em_andamento'`, `'concluido'`, `'erro'` |
| `ds_modelo` | Nome do modelo (ex: `'ha_risk_rf'`, `'ob_imc_rf'`) |
| `ds_metricas` | JSONB com métricas de ML ou stats de normalização |
| `qt_registros` | Quantidade de registros processados |

---

## Ordem Recomendada de Processamento

### Instalação completa desde o zero

```
1. python scripts/setup.py                         # Schema + views + auth
2. python scripts/migrar_mv_cadastros.py           # Deduplicação (se aplicável)
3. python scripts/normalizar_bairros.py            # Normalização de bairros (~20 min)
4. python scripts/importar_geojson.py              # GeoJSON para mapas
5. python scripts/sincronizar_base_geografica.py   # (opcional) enriquecimento OSM
6. POST /api/v1/pressao-arterial/modelo/treinar    # Modelo HAS (~2-5 min)
7. POST /api/v1/diabetes/modelo/treinar            # Modelo DM (~2-5 min)
8. POST /api/v1/obesidade/modelo/treinar           # Modelo OB (~2-5 min)
```

### Atualizações de rotina

```
1. POST /admin/refresh/mv_pa_medicoes              # Refresh views HAS
2. POST /admin/refresh/mv_pa_cadastros
3. POST /admin/refresh/mv_pa_medicoes_cidadaos
4. python scripts/setup.py (se mv_dm/mv_ob precisar)
5. python scripts/normalizar_bairros.py            # Normalizar novos bairros
6. POST /modelo/treinar (todos os módulos)         # Retreinar se necessário
```
