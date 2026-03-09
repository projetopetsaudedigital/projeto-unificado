# Dados — Mapeamento do e-SUS PEC

## Visão Geral

O banco PostgreSQL contém **408 tabelas** do e-SUS PEC (Prontuário Eletrônico do Cidadão). A plataforma utiliza um subconjunto dessas tabelas, mapeadas abaixo, distribuídas entre 3 módulos clínicos: Hipertensão Arterial (HAS), Diabetes Mellitus (DM) e Obesidade (OB).

---

## Tabelas Utilizadas

### Tabelas Principais

| Tabela | Registros típicos | Módulos | Descrição |
|--------|-------------------|---------|-----------|
| `tb_fat_cad_individual` | 50k+ | HAS, DM, OB | Fichas de cadastro individual (dados demográficos, condições de saúde) |
| `tb_fat_cidadao_pec` | 30k+ | HAS, DM, OB | ID unificado do cidadão no PEC |
| `tb_cidadao` | 30k+ | HAS, DM, OB | Dados do cidadão (bairro, CEP, logradouro) |
| `tb_medicao` | 100k+ | HAS, OB | Medições clínicas (PA, peso, altura, IMC, glicemia, etc.) |
| `tb_exame_hemoglobina_glicada` | 5k+ | DM | Resultados de exames de HbA1c |
| `tb_exame_requisitado` | 50k+ | DM | Exames requisitados (liga medição → cidadão) |
| `tb_prontuario` | 30k+ | DM | Prontuários (liga exame → cidadão) |
| `tb_atend_prof` | 100k+ | HAS, OB | Atendimentos profissionais (liga medição → UBS) |
| `tb_lotacao` | 500+ | HAS, OB | Lotações de profissionais (contém UBS e equipe) |

### Tabelas Dimensionais

| Tabela | Registros | Descrição |
|--------|-----------|-----------|
| `tb_dim_sexo` | 4 | Dimensão sexo (1=M, 3=F, etc.) |
| `tb_dim_raca_cor` | 7 | Dimensão raça/cor |
| `tb_dim_tipo_escolaridade` | ~15 | Dimensão escolaridade |

---

## Campos Críticos

### Cadastro Individual (`tb_fat_cad_individual`)

| Campo | Tipo | Descrição | Uso |
|-------|------|-----------|-----|
| `co_seq_fat_cad_individual` | INT (PK) | ID da ficha | PK da view mv_pa_cadastros |
| `co_fat_cidadao_pec` | INT (FK) | ID do cidadão no PEC | Deduplicação (DISTINCT ON) |
| `co_dim_tempo` | INT | Data como YYYYMMDD | Ordenação temporal |
| `dt_nascimento` | TIMESTAMP | Data de nascimento | Cálculo de idade |
| `co_dim_sexo` | INT (FK) | Código do sexo | Feature ML + filtros |
| `st_hipertensao_arterial` | SMALLINT | 0/1 — hipertenso | **TARGET do modelo HAS** |
| `st_diabete` | SMALLINT | 0/1 — diabético | Feature ML |
| `st_fumante` | SMALLINT | 0/1 — fumante | Feature ML |
| `st_alcool` | SMALLINT | 0/1 — uso de álcool | Feature ML |
| `st_outra_droga` | SMALLINT | 0/1 | Feature ML |
| `st_doenca_cardiaca` | SMALLINT | 0/1 | Feature ML |
| `st_problema_rins` | SMALLINT | 0/1 | Feature ML |
| `st_avc` | SMALLINT | 0/1 | Feature ML |
| `st_infarto` | SMALLINT | 0/1 | Feature ML |
| `st_doenca_respiratoria` | SMALLINT | 0/1 | Feature ML |
| `st_cancer` | SMALLINT | 0/1 | Feature ML |
| `st_hanseniase` | SMALLINT | 0/1 | Feature ML |
| `st_tuberculose` | SMALLINT | 0/1 | Feature ML |
| `st_recusa_cadastro` | SMALLINT | 0/1 | Filtro (excluir) |
| `st_gestante` | SMALLINT | 0/1 | Indicador |
| `st_acamado` | SMALLINT | 0/1 | Indicador |
| `st_domiciliado` | SMALLINT | 0/1 | Indicador |

### Cidadão (`tb_cidadao`)

| Campo | Tipo | Descrição | Uso |
|-------|------|-----------|-----|
| `co_seq_cidadao` | INT (PK) | ID do cidadão | Join com prontuário |
| `no_bairro` | TEXT | Bairro (nome) | Geolocalização |
| `no_bairro_filtro` | TEXT | Bairro normalizado (e-SUS) | **Chave de normalização** |
| `ds_cep` | VARCHAR | CEP | Consulta ViaCEP |
| `co_localidade` | INT | Localidade | Agrupamento |
| `nu_area` | INT | Área | Agrupamento |
| `nu_micro_area` | INT | Microárea | Agrupamento |
| `ds_logradouro` | TEXT | Logradouro | Geolocalização |
| `nu_numero` | TEXT | Número | Geolocalização |
| `co_dim_raca_cor` | INT (FK) | Raça/cor | Dimensão |
| `co_dim_escolaridade_pessoa` | INT (FK) | Escolaridade | Dimensão |

### Medição (`tb_medicao`)

| Campo | Tipo | Descrição | Módulo | Uso |
|-------|------|-----------|--------|-----|
| `co_seq_medicao` | INT (PK) | ID da medição | HAS, OB | PK da view |
| `co_atend_prof` | INT (FK) | Atendimento profissional | HAS, OB | Join para UBS |
| `dt_medicao` | TIMESTAMP | Data/hora da medição | HAS, OB | Temporal |
| `nu_medicao_pressao_arterial` | VARCHAR | PA formato "160/80" | **HAS** | **Dado principal HAS** |
| `nu_medicao_peso` | NUMERIC | Peso (kg) | **OB** | **Dado principal OB** |
| `nu_medicao_altura` | NUMERIC | Altura (m) | **OB** | **Dado principal OB** |
| `nu_medicao_imc` | NUMERIC | IMC (armazenado no e-SUS) | OB | Referência (recalculado) |
| `nu_medicao_frequencia_cardiaca` | INT | FC (bpm) | HAS | Sinais vitais |
| `nu_medicao_glicemia` | NUMERIC | Glicemia | HAS | Sinais vitais |
| `nu_medicao_circunf_abdominal` | NUMERIC | Circunferência abdominal | OB | Sinais vitais |

### Hemoglobina Glicada (`tb_exame_hemoglobina_glicada`)

| Campo | Tipo | Descrição | Uso |
|-------|------|-----------|-----|
| `co_seq_hemoglobina_glicada` | INT (PK) | ID do exame | PK da view DM |
| `co_exame_requisitado` | INT (FK) | Exame requisitado | Join com data |
| `vl_hemoglobina_glicada` | NUMERIC | Valor HbA1c (%) | **Dado principal DM** (range 3-20) |

---

## Módulo Obesidade — Dados Específicos

O módulo de Obesidade usa exclusivamente `tb_medicao` como fonte de medições. O IMC é **sempre recalculado** a partir dos campos brutos de peso e altura:

```sql
IMC = nu_medicao_peso / (nu_medicao_altura * nu_medicao_altura)
```

O valor `nu_medicao_imc` armazenado pelo e-SUS **não é utilizado** pois pode conter erros de digitação ou arredondamentos inconsistentes.

### View `mv_obesidade`

| Campo | Descrição |
|-------|-----------|
| `co_seq_medicao` | PK da medição |
| `dt_medicao` | Data da medição |
| `nu_medicao_peso` | Peso bruto (kg) |
| `nu_medicao_altura` | Altura bruta (m) |
| `imc_calculado` | IMC recalculado (peso/altura²) |
| `classificacao_oms` | Classe OMS: baixo_peso, normal, sobrepeso, obesidade_1/2/3 |
| `co_fat_cidadao_pec` | ID do cidadão |
| `idade` | Idade calculada |
| `co_dim_sexo` | Sexo |
| `no_bairro_canonico` | Bairro normalizado |
| `co_unidade_saude` | UBS vinculada |

**Filtros aplicados na view:**
- Peso entre 20 kg e 300 kg
- Altura entre 0.50 m e 2.50 m
- Medições dos últimos 10 anos
- Adultos (idade >= 18)
- Exclui falecidos e recusas de cadastro

---

## Joins Críticos

### Caminho: Medição → Cidadão (HAS e OB)

```
tb_medicao
  → tb_atend_prof (co_atend_prof = co_seq_atend_prof)
    → tb_lotacao (co_lotacao = co_ator_papel)          ← UBS e equipe
  → LATERAL tb_exame_requisitado (co_atend_prof)       ← liga ao prontuário
    → tb_prontuario (co_prontuario = co_seq_prontuario)
      → tb_cidadao (co_cidadao = co_seq_cidadao)       ← dados do cidadão
        → tb_fat_cidadao_pec (co_cidadao)              ← ID unificado PEC
```

**Atenção:** A PK de `tb_lotacao` é `co_ator_papel` (NÃO `co_seq_lotacao`).

### Caminho: HbA1c → Cidadão (DM)

```
tb_exame_hemoglobina_glicada
  → tb_exame_requisitado (co_exame_requisitado = co_seq_exame_requisitado)
    → tb_prontuario (co_prontuario = co_seq_prontuario)
      → tb_cidadao (co_cidadao = co_seq_cidadao)
        → tb_fat_cidadao_pec (co_cidadao)
          → LATERAL tb_fat_cad_individual (co_fat_cidadao_pec, st_diabete=1)
```

---

## Filtros Aplicados nas Views

Todas as views aplicam estes filtros padrão:

| Filtro | Razão |
|--------|-------|
| `dt_nascimento IS NOT NULL` | Necessário para calcular idade |
| `idade >= 18` | Apenas adultos |
| `st_faleceu = 0 OR NULL` | Exclui falecidos |
| `st_recusa_cadastro = 0 OR NULL` | Exclui recusas |
| `bairro IS NOT NULL` | Necessário para geolocalização |
| `últimos 10 anos` | Dados recentes (medições e exames) |

---

## Schema `auth`

Além dos schemas `public` (e-SUS PEC) e `dashboard` (analytics), a plataforma mantém um terceiro schema para autenticação de usuários:

### `auth.tb_usuarios`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `co_seq_usuario` | SERIAL (PK) | ID do usuário |
| `ds_nome` | TEXT | Nome completo |
| `ds_email` | TEXT (UNIQUE) | Email (usado no login) |
| `ds_senha_hash` | TEXT | Senha em bcrypt |
| `tp_perfil` | VARCHAR | `'admin'`, `'operador'` ou `'leitor'` |
| `st_ativo` | BOOLEAN | Usuário ativo |
| `dt_criacao` | TIMESTAMP | Data de criação |
| `dt_ultimo_login` | TIMESTAMP | Último acesso |

---

## Qualidade dos Dados

### Problemas conhecidos

| Problema | Impacto | Solução |
|----------|---------|---------|
| Bairro como texto livre | 2.302 variações para ~100 bairros | Normalização (ViaCEP + fuzzy) |
| Cidadãos recadastrados | Contagem inflada na prevalência | Deduplicação (DISTINCT ON) |
| PA como string "160/80" | Precisa parsing para análise | Feito nas queries analytics |
| Campos SMALLINT NULL vs 0 | Ausência vs negação | COALESCE nas views |
| CEP inválido/parcial | ~23% sem CEP útil | Fallback para fuzzy |
| IMC armazenado com erros | Valores inconsistentes no e-SUS | IMC recalculado a partir de peso/altura |

### Completude dos Campos (referência)

- **Pressão arterial:** Alta completude em registros de atendimento
- **Peso e altura:** Completude variável — apenas medições onde o profissional registrou ambos os valores
- **HbA1c:** Apenas para pacientes diabéticos com exame laboratorial registrado no e-SUS
- **Hipertensão (flags):** 55-100% dependendo da tabela e período
