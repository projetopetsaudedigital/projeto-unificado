# Guia de Qualidade de Dados: Preenchimento de Bairros e Loteamentos no e-SUS

Este guia tem como objetivo orientar os Agentes Comunitários de Saúde (ACS) e técnicos de TI na padronização do preenchimento do campo "Bairro" no e-SUS PEC, garantindo que o painel de monitoramento de saúde municipal consiga mapear corretamente os cidadãos no território de Vitória da Conquista.

---

## O Problema Atual

Atualmente, **76% dos cadastros** em bairros grandes (como o Zabelê) estão registrados no e-SUS apenas com o nome genérico do bairro (ex: `"zabele"`). 

O município de Vitória da Conquista é geograficamente dividido em **Bairros Oficiais** e **Loteamentos** (desmembramentos menores dentro dos bairros). Quando o ACS insere apenas o nome do bairro, perdemos a capacidade de observar micro-focos de doenças (como Hipertensão) em Loteamentos específicos (ex: *Miro Cairo*, *Senhorinha Cairo*, *Vila Beatriz*, etc.).

---

## Recomendações de Preenchimento para ACS

Para que o mapa de calor e os relatórios epidemiológicos reflitam a realidade com precisão (granularidade por loteamento), siga estas regras na hora do Cadastro Individual e Domiciliar:

### 1. Prefira sempre o nome do Loteamento/Condomínio
Se o cidadão mora em um loteamento legalmente reconhecido que fica dentro de um bairro maior, **digite o nome do loteamento** no campo bairro.

❌ **Incorreto (Genérico):**
- Bairro: `Zabelê`
- Bairro: `Primavera`
- Bairro: `Candeias`

✅ **Correto (Específico):**
- Bairro: `Senhorinha Cairo` (Fica no Zabelê)
- Bairro: `Miro Cairo` (Fica no Zabelê)
- Bairro: `Morada dos Pássaros III` (Fica no Felícia)
- Bairro: `Alto das Araras` (Fica no Candeias)

> **Nota para o ACS:** O sistema de inteligência de dados já sabe que o "Senhorinha Cairo" pertence ao "Zabelê". Você não precisa escrever os dois nomes. Apenas o loteamento mais específico é suficiente!

### 2. Evite junções ou abreviações criativas
O sistema cruza o que você digita com a base de dados cartográfica da Prefeitura (GeoJSON). Nomes inventados, com barras (`/`), parênteses ou traços dificultam o trabalho automatizado do painel.

❌ **Incorreto (Não mapeável):**
- Bairro: `Zabele/Miro Cairo`
- Bairro: `Zabele (Senhorinha Cairo)`
- Bairro: `Zabele - Urbis V`
- Bairro: `Lot. Sta. Cruz`

✅ **Correto (Mapeável):**
- Bairro: `Miro Cairo`
- Bairro: `Senhorinha Cairo`
- Bairro: `Urbis V`
- Bairro: `Santa Cruz`

### 3. Evite palavras desnecessárias
Não escreva palavras como "Loteamento", "Lot.", "Bairro", "Condomínio" antes do nome, a menos que faça parte do nome oficial.

❌ **Incorreto:**
- Bairro: `Bairro Brasil`
- Bairro: `Lot Vila Serrana`

✅ **Correto:**
- Bairro: `Brasil`
- Bairro: `Vila Serrana I`

---

## Impacto no Dashbord (Mapa de Hipertensão)

Quando os dados são preenchidos genericamente (ex: `Zabelê`), o sistema agrupa esses cadastros em um ponto central chamado **"Zabelê (não espec. ou todo bairro)"**. 

Quando preenchidos com o loteamento exato (ex: `Ouro Verde`), o sistema exibe um ponto menor exatamente na coordenada daquele loteamento, permitindo que a gestão em saúde veja exatamente onde os casos de hipertensão ou diabetes estão concentrados, facilitando o envio de agentes de saúde ou a criação de campanhas de base territorializadas.
