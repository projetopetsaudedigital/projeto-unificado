"""
Normalização de nomes de bairros.

Problema: o campo no_bairro_filtro do e-SUS PEC contém 2302 variações distintas
para um município com ~100 bairros reais. Causas típicas:
  - Erros de digitação ("patagoia" → "patagonia")
  - Falta de acento ("espirito santo" → "espírito santo")
  - Logradouro no campo de bairro ("rua das flores 123")
  - Nomes abreviados ou parciais
  - Dados de zonas rurais sem bairro real

Estratégia em duas camadas:
  1. CEP → ViaCEP API: para os 77% de registros com CEP, consulta o
     Correios via ViaCEP (gratuito, sem autenticação) para obter o bairro oficial.
  2. rapidfuzz: para os 23% sem CEP, usa similaridade de string (WRatio)
     para mapear o nome raw ao canônico mais próximo, com threshold de 80%.

Resultado: tabela dashboard.tb_bairros_mapeamento (raw → canônico).
Queries de analytics fazem LEFT JOIN nesta tabela.
"""

import time
import urllib.request
import urllib.error
import json
import re
from typing import Optional

from unidecode import unidecode
from rapidfuzz import process, fuzz

from app.core.database import execute_query, engine
from app.core.logging_config import setup_logging

logger = setup_logging("pa.processors.bairros")

# ─── Normalização básica ────────────────────────────────────────────────────

def normalizar_texto(nome: str) -> str:
    """
    Remove acentos, converte para minúsculas, colapsa espaços.
    Ex: "Espírito  Santo" → "espirito santo"
    """
    if not nome:
        return ""
    sem_acento = unidecode(nome.strip())
    return re.sub(r"\s+", " ", sem_acento).lower()


def parece_bairro(nome: str) -> bool:
    """
    Heurística: descarta entradas que claramente não são nomes de bairros.
    Retorna False se o nome parece ser um logradouro, CEP, número ou texto longo.
    """
    if not nome or len(nome) < 3 or len(nome) > 80:
        return False
    # Descarta se começa com "rua ", "av ", "avenida ", "travessa ", etc.
    padroes_logradouro = r"^(rua|av|ave|avenida|travessa|trav|estrada|rod|rodovia|beco|vl|vila)\b"
    if re.match(padroes_logradouro, nome.lower()):
        return False
    # Descarta se tem muitos dígitos (endereço numérico)
    if sum(c.isdigit() for c in nome) > 4:
        return False
    return True


# ─── ViaCEP API ─────────────────────────────────────────────────────────────

# Sentinela: distingue "CEP não existe" (permanente) de "erro de rede" (transitório)
_CEP_NAO_ENCONTRADO = object()


def consultar_viacep(cep: str, tentativas: int = 3, timeout: int = 10) -> Optional[str]:
    """
    Consulta ViaCEP para obter o bairro oficial associado ao CEP.

    Retorna:
      - str: bairro normalizado
      - None: CEP existe mas sem bairro cadastrado
      - _CEP_NAO_ENCONTRADO: CEP inválido/inexistente (não retentar)
      - lança TimeoutError: falha de rede transitória (não salvar no banco)
    """
    cep_limpo = re.sub(r"\D", "", str(cep))
    if len(cep_limpo) != 8:
        return _CEP_NAO_ENCONTRADO
    if cep_limpo in ("45099899", "45100000"):
        return _CEP_NAO_ENCONTRADO

    url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
    ultimo_erro = None

    for tentativa in range(1, tentativas + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("erro"):
                return _CEP_NAO_ENCONTRADO
            bairro = data.get("bairro", "").strip()
            return normalizar_texto(bairro) if bairro else None
        except (TimeoutError, urllib.error.URLError) as exc:
            ultimo_erro = exc
            if tentativa < tentativas:
                espera = tentativa * 2  # 2s, 4s
                logger.debug(f"ViaCEP timeout CEP {cep_limpo} (tentativa {tentativa}/{tentativas}), aguardando {espera}s...")
                time.sleep(espera)
        except Exception as exc:
            logger.warning(f"ViaCEP erro inesperado para CEP {cep_limpo}: {exc}")
            return _CEP_NAO_ENCONTRADO

    logger.warning(f"ViaCEP falhou para CEP {cep_limpo} após {tentativas} tentativas: {ultimo_erro}")
    raise TimeoutError(f"ViaCEP timeout para CEP {cep_limpo}")


# ─── Matching fuzzy ──────────────────────────────────────────────────────────

def mapear_fuzzy(
    nome_raw: str,
    canonicos: list[str],
    threshold: float = 80.0,
) -> Optional[str]:
    """
    Encontra o bairro canônico mais similar ao nome_raw usando rapidfuzz WRatio.
    Retorna None se nenhum atingir o threshold (evita falsos positivos).
    """
    if not canonicos or not nome_raw:
        return None
    nome_norm = normalizar_texto(nome_raw)
    resultado = process.extractOne(
        nome_norm,
        canonicos,
        scorer=fuzz.WRatio,
        score_cutoff=threshold,
    )
    return resultado[0] if resultado else None


# ─── Tabela de mapeamento ───────────────────────────────────────────────────

DDL_MAPEAMENTO = """
CREATE TABLE IF NOT EXISTS dashboard.tb_bairros_mapeamento (
    co_seq_bairro_map   SERIAL PRIMARY KEY,
    no_bairro_raw       TEXT NOT NULL,          -- nome original (normalizado básico)
    no_bairro_canonico  TEXT,                   -- nome canônico após normalização
    tp_origem           VARCHAR(20) NOT NULL,   -- 'viacep' | 'fuzzy' | 'manual'
    vl_similaridade     NUMERIC(5,2),           -- score do fuzzy (NULL se viacep/manual)
    st_revisado         SMALLINT DEFAULT 0,     -- 0=automático, 1=revisado pelo gestor
    dt_criacao          TIMESTAMP DEFAULT NOW(),
    UNIQUE (no_bairro_raw)
);
CREATE INDEX IF NOT EXISTS idx_bairros_map_raw ON dashboard.tb_bairros_mapeamento (no_bairro_raw);
CREATE INDEX IF NOT EXISTS idx_bairros_map_canonico ON dashboard.tb_bairros_mapeamento (no_bairro_canonico);
"""


def criar_tabela_mapeamento() -> None:
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text(DDL_MAPEAMENTO))
        conn.commit()
    logger.info("Tabela tb_bairros_mapeamento pronta.")


def buscar_mapeamentos_existentes() -> dict[str, str]:
    """Retorna {raw: canonico} para todos os mapeamentos já gravados."""
    rows = execute_query(
        "SELECT no_bairro_raw, no_bairro_canonico FROM dashboard.tb_bairros_mapeamento", {}
    )
    return {r["no_bairro_raw"]: r["no_bairro_canonico"] for r in rows}


def gravar_mapeamento(raw: str, canonico: Optional[str], origem: str, similaridade: float = None) -> None:
    from sqlalchemy import text
    sql = """
    INSERT INTO dashboard.tb_bairros_mapeamento
        (no_bairro_raw, no_bairro_canonico, tp_origem, vl_similaridade)
    VALUES (:raw, :canonico, :origem, :sim)
    ON CONFLICT (no_bairro_raw) DO UPDATE
        SET no_bairro_canonico = EXCLUDED.no_bairro_canonico,
            tp_origem = EXCLUDED.tp_origem,
            vl_similaridade = EXCLUDED.vl_similaridade
    """
    with engine.connect() as conn:
        conn.execute(text(sql), {"raw": raw, "canonico": canonico, "origem": origem, "sim": similaridade})
        conn.commit()


# ─── Pipeline principal ──────────────────────────────────────────────────────

def executar_normalizacao(
    delay_viacep: float = 0.3,
    threshold_fuzzy: float = 80.0,
    limite_ceps: int = None,
) -> dict:
    """
    Pipeline completo de normalização de bairros:
      1. Cria tabela de mapeamento
      2. Busca todos os CEPs distintos e consulta ViaCEP
      3. Busca nomes sem CEP e aplica fuzzy matching
      4. Grava resultados

    Args:
        delay_viacep: segundos entre chamadas à API (default 0.3s)
        threshold_fuzzy: score mínimo para aceitar match fuzzy (0-100)
        limite_ceps: limitar número de CEPs consultados (None = todos)
    """
    criar_tabela_mapeamento()
    existentes = buscar_mapeamentos_existentes()
    stats = {"viacep_ok": 0, "viacep_sem_bairro": 0, "fuzzy_ok": 0, "fuzzy_sem_match": 0, "ja_existia": 0}

    # ── Fase 1: CEP → ViaCEP ────────────────────────────────────────────────
    logger.info("Fase 1: consultando ViaCEP para CEPs distintos...")

    ceps_query = """
        SELECT DISTINCT ds_cep, no_bairro_filtro
        FROM dashboard.mv_pa_cadastros
        WHERE ds_cep IS NOT NULL
          AND LENGTH(TRIM(ds_cep)) >= 8
        ORDER BY ds_cep
    """
    if limite_ceps:
        ceps_query += f" LIMIT {limite_ceps}"

    ceps = execute_query(ceps_query, {})
    logger.info(f"{len(ceps)} CEPs distintos encontrados.")

    canonicos_viacep: set[str] = set()

    stats["viacep_timeout"] = 0

    for i, row in enumerate(ceps):
        cep = row["ds_cep"]
        raw_norm = normalizar_texto(row["no_bairro_filtro"] or "")

        if raw_norm in existentes:
            stats["ja_existia"] += 1
            if existentes[raw_norm]:
                canonicos_viacep.add(existentes[raw_norm])
            continue

        try:
            bairro_oficial = consultar_viacep(cep)
        except TimeoutError:
            # Erro de rede transitório: NÃO salva no banco para ser retentado depois
            stats["viacep_timeout"] += 1
            if (i + 1) % 50 == 0:
                logger.info(f"  {i+1}/{len(ceps)} CEPs processados...")
            time.sleep(delay_viacep)
            continue

        if bairro_oficial is _CEP_NAO_ENCONTRADO:
            # CEP inválido/inexistente — salva para não tentar de novo
            gravar_mapeamento(raw_norm, raw_norm if parece_bairro(raw_norm) else None, "viacep")
            existentes[raw_norm] = raw_norm
            stats["viacep_sem_bairro"] += 1
        elif bairro_oficial and parece_bairro(bairro_oficial):
            canonicos_viacep.add(bairro_oficial)
            gravar_mapeamento(raw_norm, bairro_oficial, "viacep")
            existentes[raw_norm] = bairro_oficial
            stats["viacep_ok"] += 1
        else:
            # CEP existe mas sem bairro na API — salva raw
            gravar_mapeamento(raw_norm, raw_norm if parece_bairro(raw_norm) else None, "viacep")
            existentes[raw_norm] = raw_norm
            stats["viacep_sem_bairro"] += 1

        if (i + 1) % 50 == 0:
            logger.info(f"  {i+1}/{len(ceps)} CEPs processados...")
        time.sleep(delay_viacep)

    # ── Fase 2: Fuzzy para nomes sem CEP ────────────────────────────────────
    logger.info("Fase 2: fuzzy matching para bairros sem CEP...")

    canonicos_lista = sorted(canonicos_viacep)
    logger.info(f"  Lista canônica com {len(canonicos_lista)} bairros confirmados via ViaCEP.")

    sem_cep_query = """
        SELECT DISTINCT no_bairro_filtro
        FROM dashboard.mv_pa_cadastros
        WHERE (ds_cep IS NULL OR LENGTH(TRIM(ds_cep)) < 8)
          AND no_bairro_filtro IS NOT NULL
    """
    sem_cep = execute_query(sem_cep_query, {})

    for row in sem_cep:
        raw_norm = normalizar_texto(row["no_bairro_filtro"] or "")
        if not raw_norm or raw_norm in existentes:
            stats["ja_existia"] += 1
            continue

        canonico = mapear_fuzzy(raw_norm, canonicos_lista, threshold=threshold_fuzzy)
        if canonico:
            score = fuzz.WRatio(raw_norm, canonico)
            gravar_mapeamento(raw_norm, canonico, "fuzzy", similaridade=score)
            stats["fuzzy_ok"] += 1
        else:
            gravar_mapeamento(raw_norm, raw_norm if parece_bairro(raw_norm) else None, "fuzzy")
            stats["fuzzy_sem_match"] += 1

    logger.info(f"Normalização concluída: {stats}")
    return stats
