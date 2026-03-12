"""
Endpoints de administração e setup da plataforma.

GET  /admin/status          → verifica o estado de cada componente
POST /admin/refresh/{view}  → executa REFRESH MATERIALIZED VIEW
GET  /admin/processamentos  → histórico de processamentos
POST /admin/treinar/{modulo}→ treinar modelo de ML (has ou dm)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import Response
import httpx

from app.core.database import execute_query, engine
from app.core.logging_config import setup_logging
from app.modules.pressao_arterial.views.manager import atualizar_view
from app.shared.controle_processamento import (
    criar_tabela_controle,
    listar_processamentos,
    ultimo_processamento,
)

logger = setup_logging("pa.routes.admin")

router = APIRouter()

# Views que podem ser atualizadas via API (whitelist de segurança)
_VIEWS_PERMITIDAS = {
    "mv_pa_medicoes",
    "mv_pa_medicoes_cidadaos",
    "mv_pa_cadastros",
}


def _existe_objeto(sql: str, params: dict) -> bool:
    try:
        rows = execute_query(sql, params)
        return bool(rows)
    except Exception:
        return False


def _contar_linhas(tabela: str) -> int | None:
    try:
        rows = execute_query(f"SELECT COUNT(*) AS n FROM {tabela}", {})
        return rows[0]["n"] if rows else 0
    except Exception:
        return None


@router.get("/status", summary="Status de todos os componentes da plataforma")
def status_plataforma():
    """
    Verifica se cada componente está criado e em que estado está:
      - Schema dashboard
      - Views materializadas (3) + vw_bairro_canonico
      - Tabela de auditoria de outliers
      - Migração de deduplicação (índice único em co_fat_cidadao_pec)
      - Normalização de bairros (tb_bairros_mapeamento)
    """

    # 1. Schema dashboard
    schema_ok = _existe_objeto(
        "SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'dashboard'",
        {},
    )

    # 2. Views materializadas
    views_status = {}
    for view in ["mv_pa_medicoes", "mv_pa_cadastros", "mv_pa_medicoes_cidadaos"]:
        existe = _existe_objeto(
            "SELECT matviewname FROM pg_matviews WHERE schemaname='dashboard' AND matviewname=:v",
            {"v": view},
        )
        linhas = _contar_linhas(f"dashboard.{view}") if existe else None
        views_status[view] = {"existe": existe, "linhas": linhas}

    # 3. vw_bairro_canonico
    vw_bairro_ok = _existe_objeto(
        "SELECT viewname FROM pg_views WHERE schemaname='dashboard' AND viewname='vw_bairro_canonico'",
        {},
    )

    # 4. Tabela de auditoria
    auditoria_ok = _existe_objeto(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='dashboard' AND table_name='tb_auditoria_outliers'",
        {},
    )

    # 5. Migração de deduplicação: verifica índice único em co_fat_cidadao_pec
    dedup_aplicada = _existe_objeto(
        "SELECT indexname FROM pg_indexes "
        "WHERE schemaname='dashboard' AND tablename='mv_pa_cadastros' "
        "AND indexname='idx_mv_pa_cad_cidadao_pec'",
        {},
    )

    # 6. Normalização de bairros
    tb_mapeamento_ok = _existe_objeto(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='dashboard' AND table_name='tb_bairros_mapeamento'",
        {},
    )

    mapeamento_linhas = None
    total_ceps = None
    pct_normalizado = None

    if tb_mapeamento_ok:
        mapeamento_linhas = _contar_linhas("dashboard.tb_bairros_mapeamento")
        try:
            r = execute_query(
                "SELECT COUNT(DISTINCT ds_cep) AS n FROM tb_cidadao WHERE ds_cep IS NOT NULL AND ds_cep != ''",
                {},
            )
            total_ceps = r[0]["n"] if r else None
            if total_ceps and mapeamento_linhas is not None:
                pct_normalizado = round(mapeamento_linhas / total_ceps * 100, 1)
        except Exception:
            pass

    return {
        "schema_dashboard": schema_ok,
        "views": views_status,
        "vw_bairro_canonico": vw_bairro_ok,
        "tb_auditoria_outliers": auditoria_ok,
        "migracao_deduplicacao": {
            "aplicada": dedup_aplicada,
            "descricao": "DISTINCT ON por cidadão em mv_pa_cadastros (índice idx_mv_pa_cad_cidadao_pec)",
        },
        "normalizacao_bairros": {
            "tabela_existe": tb_mapeamento_ok,
            "bairros_mapeados": mapeamento_linhas,
            "total_ceps_unicos": total_ceps,
            "pct_normalizado": pct_normalizado,
        },
    }


@router.post(
    "/refresh/{view_name}",
    summary="Atualiza (REFRESH) uma view materializada",
)
def refresh_view(view_name: str):
    """
    Executa REFRESH MATERIALIZED VIEW CONCURRENTLY para a view informada.
    Apenas as 3 views principais são aceitas.

    Atenção: pode demorar alguns minutos dependendo do volume de dados.
    """
    if view_name not in _VIEWS_PERMITIDAS:
        raise HTTPException(
            status_code=400,
            detail=f"View '{view_name}' não permitida. Use: {sorted(_VIEWS_PERMITIDAS)}",
        )

    logger.info(f"Refresh solicitado via API: dashboard.{view_name}")
    ok = atualizar_view(view_name, concurrently=True)

    if not ok:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao atualizar dashboard.{view_name}. Verifique os logs do servidor.",
        )

    linhas = _contar_linhas(f"dashboard.{view_name}")
    return {
        "view": f"dashboard.{view_name}",
        "status": "atualizada",
        "linhas": linhas,
    }


@router.get("/processamentos", summary="Histórico de processamentos")
def historico_processamentos(tipo: str = None, limite: int = 20):
    """Lista os últimos processamentos registrados (normalizações, treinamentos, refreshes)."""
    try:
        criar_tabela_controle()
        return listar_processamentos(tp_processamento=tipo, limite=limite)
    except Exception as e:
        logger.error(f"Erro ao listar processamentos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


_MODULOS_TREINO = {"has", "dm", "ob"}
_treinamento_em_andamento = {}


@router.post("/treinar/{modulo}", summary="Treina modelo de ML")
def treinar_modelo_admin(modulo: str, background_tasks: BackgroundTasks):
    """
    Treina (ou re-treina) o modelo de ML para o módulo especificado.
    Módulos aceitos: 'has' (hipertensão), 'dm' (diabetes) ou 'ob' (obesidade).
    """
    if modulo not in _MODULOS_TREINO:
        raise HTTPException(
            status_code=400,
            detail=f"Módulo '{modulo}' não reconhecido. Use: {sorted(_MODULOS_TREINO)}",
        )

    if _treinamento_em_andamento.get(modulo):
        raise HTTPException(
            status_code=409,
            detail=f"Treinamento de '{modulo}' já em andamento.",
        )

    def _treinar_bg():
        _treinamento_em_andamento[modulo] = True
        try:
            if modulo == "has":
                from app.modules.pressao_arterial.ml.pipeline import treinar_modelo
            elif modulo == "dm":
                from app.modules.diabetes.ml.pipeline import treinar_modelo
            else:
                print("Módulo Desconhecido")
            treinar_modelo()
            logger.info(f"Treinamento '{modulo}' concluído.")
        except Exception as e:
            logger.error(f"Erro no treinamento '{modulo}': {e}")
        finally:
            _treinamento_em_andamento[modulo] = False

    background_tasks.add_task(_treinar_bg)

    nomes = {"has": "Hipertensão Arterial", "dm": "Diabetes Mellitus"}
    return {
        "status": "iniciado",
        "modulo": modulo,
        "mensagem": f"Treinamento de {nomes[modulo]} iniciado em background.",
    }


# ── Sincronização Base Geográfica ──────────────────────────────────────────────

_sincronizacao_em_andamento = False
_sincronizacao_progresso = {"atual": 0, "total": 0, "status": "idle"}


@router.post("/sincronizar-base-geografica", summary="Inicia sincronização da Base Geográfica Oficial")
def sincronizar_base_geografica(
    background_tasks: BackgroundTasks,
    threshold: float = 80.0,
):
    """
    Inicia a sincronização de bairros em background usando os arquivos GeoJSON (Offline).
    """
    global _sincronizacao_em_andamento

    if _sincronizacao_em_andamento:
        raise HTTPException(status_code=409, detail="Sincronização já em andamento.")

    def _sincronizar_bg():
        global _sincronizacao_em_andamento, _sincronizacao_progresso
        _sincronizacao_em_andamento = True
        _sincronizacao_progresso = {"atual": 0, "total": 0, "status": "executando"}
        try:
            from app.modules.pressao_arterial.processors.normalizador_bairros import criar_tabela_mapeamento
            from scripts.sincronizar_base_geografica import DDL_MAPEAMENTO, carregar_arquivos_geojson, popular_geocodificacao, mapear_esus_para_geojson
            from sqlalchemy import text
            from app.core.database import engine
            
            with engine.connect() as conn:
                conn.execute(text(DDL_MAPEAMENTO))
                conn.commit()
                
            bairros, loteamentos = carregar_arquivos_geojson()
            popular_geocodificacao(bairros, loteamentos)
            stats = mapear_esus_para_geojson(threshold=threshold)
            
            _sincronizacao_progresso = {
                "atual": stats.get("exato", 0) + stats.get("fuzzy", 0),
                "total": stats.get("exato", 0) + stats.get("fuzzy", 0) + stats.get("orfao", 0),
                "status": "concluido",
                "resultado": stats,
            }
            logger.info(f"Sincronização concluída: {stats}")
        except Exception as e:
            logger.error(f"Erro na sincronização: {e}")
            import traceback
            traceback.print_exc()
            _sincronizacao_progresso["status"] = f"erro: {str(e)}"
        finally:
            _sincronizacao_em_andamento = False

    background_tasks.add_task(_sincronizar_bg)
    return {
        "status": "iniciado",
        "mensagem": "Sincronização de base geográfica iniciada em background.",
        "threshold": threshold,
    }

@router.get("/sincronizar-base-geografica/status", summary="Status da sincronização em andamento")
def status_sincronizacao():
    """Retorna o progresso da sincronização."""
    return {
        "em_andamento": _sincronizacao_em_andamento,
        **_sincronizacao_progresso,
    }


# ── Geocodificação (Nominatim) ───────────────────────────────────────────

_geocodificacao_andamento = False
_geocodificacao_progresso = {"atual": 0, "total": 0, "status": "idle"}

from pydantic import BaseModel
class GeocodeRequest(BaseModel):
    bairros: list[str]

@router.post("/geocodificar", summary="Geocodifica bairros selecionados via Nominatim")
def geocodificar_bairros(req: GeocodeRequest, background_tasks: BackgroundTasks):
    """
    Busca as coordenadas de bairros específicos usando a API do Nominatim (OpenStreetMap).
    """
    global _geocodificacao_andamento

    if _geocodificacao_andamento:
        raise HTTPException(status_code=409, detail="Geocodificação já em andamento.")

    import time
    import httpx

    bairros = req.bairros
    if not bairros:
        return {"status": "concluido", "mensagem": "Nenhum bairro informado."}

    def _geocode_bg():
        global _geocodificacao_andamento, _geocodificacao_progresso
        _geocodificacao_andamento = True
        _geocodificacao_progresso = {"atual": 0, "total": len(bairros), "status": "executando"}
        
        sucesso = 0
        erros = 0
        
        try:
            with httpx.Client(timeout=10.0) as client:
                for i, bairro in enumerate(bairros):
                    _geocodificacao_progresso["atual"] = i + 1
                    
                    q = f"{bairro}, Vitória da Conquista, Bahia, Brasil"
                    try:
                        res = client.get(
                            "https://nominatim.openstreetmap.org/search",
                            params={"q": q, "format": "json", "limit": 1},
                            headers={"User-Agent": "PlataformaSaudeVDC/1.0", "Accept-Language": "pt-BR"}
                        )
                        res.raise_for_status()
                        data = res.json()
                        
                        if data:
                            lat = float(data[0]["lat"])
                            lng = float(data[0]["lon"])
                            execute_query("""
                                INSERT INTO dashboard.tb_geocodificacao (no_bairro, nu_latitude, nu_longitude, ds_fonte)
                                VALUES (:bairro, :lat, :lng, 'nominatim')
                                ON CONFLICT (no_bairro) DO UPDATE 
                                SET nu_latitude = EXCLUDED.nu_latitude,
                                    nu_longitude = EXCLUDED.nu_longitude,
                                    ds_fonte = 'nominatim'
                            """, {"bairro": bairro, "lat": lat, "lng": lng})
                            sucesso += 1
                        time.sleep(1.2)  # Limite rígido do Nominatim (max 1/segundo)
                    except Exception as e:
                        logger.error(f"Erro ao geocodificar '{bairro}': {e}")
                        erros += 1
                        time.sleep(2.0)
                        
            _geocodificacao_progresso = {
                "atual": len(bairros),
                "total": len(bairros),
                "status": "concluido",
                "sucesso": sucesso,
                "erros": erros
            }
        except Exception as e:
            _geocodificacao_progresso["status"] = f"erro: {e}"
        finally:
            _geocodificacao_andamento = False

    background_tasks.add_task(_geocode_bg)
    return {
        "status": "iniciado",
        "mensagem": f"Geocodificação fallback de {len(bairros)} bairros iniciada.",
        "total": len(bairros)
    }


@router.get("/geocodificar/status", summary="Status da Geocodificação Nominatim")
def status_geocodificacao():
    return {
        "em_andamento": _geocodificacao_andamento,
        **_geocodificacao_progresso,
    }


@router.get("/geocodificacao/exportar", summary="Exportar Coordenadas (CSV)")
def exportar_geocodificacao():
    from fastapi.responses import Response
    import csv
    import io

    rows = execute_query(
        "SELECT no_bairro, nu_latitude, nu_longitude, ds_fonte FROM dashboard.tb_geocodificacao ORDER BY no_bairro",
        {}
    )
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["bairro", "latitude", "longitude", "fonte"])
    
    for r in rows:
        writer.writerow([r["no_bairro"], r["nu_latitude"], r["nu_longitude"], r["ds_fonte"]])
        
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=bairros_coordenadas.csv"}
    )

@router.get("/setup-info", summary="Guia de setup via CLI — flags disponíveis")
def setup_info():
    """
    Documenta os comandos do script `scripts/setup.py` para inicializar a plataforma.

    ## Setup completo (novo servidor)
    ```
    cd backend
    python scripts/setup.py --all
    ```

    ## Flags disponíveis

    | Flag | Descrição |
    |------|-----------|
    | `--all` | Executa tudo na ordem correta (schema → auth → tabelas → views) |
    | `--check` | Testa conexão e exibe status atual das views |
    | `--schema` | Cria schemas e aliases pec.* (modo single) ou configura FDW |
    | `--auth` | Cria `auth.tb_usuarios` e insere o admin padrão |
    | `--tabelas` | Cria tabelas de suporte (auditoria, controle, bairros_mapeamento) |
    | `--views-pa` | Cria as 3 views materializadas de Pressão Arterial |
    | `--views-diabetes` | Cria `mv_dm_hemoglobina` |
    | `--views-regulares` | Cria `vw_bairro_canonico` e `vw_loteamento_canonico` |
    | `--normalizacao` | Normalização de bairros via ViaCEP + fuzzy (executar após --all) |
    | `--refresh` | REFRESH CONCURRENTLY em todas as views materializadas |

    ## Flags auxiliares para --normalizacao

    - `--limite-ceps N` — limita a N CEPs (testes rápidos)
    - `--threshold FLOAT` — threshold fuzzy (padrão: 80.0)
    - `--delay FLOAT` — delay entre chamadas ViaCEP em segundos (padrão: 0.3)

    ## Credenciais padrão do admin

    - **Email:** admin@plataforma.saude
    - **Senha:** admin123 *(alterar em produção!)*
    """
    return {
        "script": "python scripts/setup.py",
        "flags": {
            "--all": "Setup completo (schema + auth + tabelas + todas as views)",
            "--check": "Testa conexão e exibe status das views",
            "--schema": "Cria schemas e aliases pec.* (modo single) ou configura FDW",
            "--auth": "Cria auth.tb_usuarios e insere admin padrão",
            "--tabelas": "Cria tabelas de suporte (auditoria, controle, bairros)",
            "--views-pa": "Cria as 3 views materializadas de Pressão Arterial",
            "--views-diabetes": "Cria mv_dm_hemoglobina",
            "--views-regulares": "Cria vw_bairro_canonico e vw_loteamento_canonico",
            "--normalizacao": "Normalização de bairros via ViaCEP + fuzzy (executar após --all)",
            "--refresh": "REFRESH CONCURRENTLY em todas as views materializadas",
        },
        "flags_normalizacao": {
            "--limite-ceps": "Limita a N CEPs (para testes rápidos)",
            "--threshold": "Threshold fuzzy match (padrão: 80.0)",
            "--delay": "Delay entre chamadas ViaCEP em segundos (padrão: 0.3)",
        },
        "admin_padrao": {
            "email": "admin@plataforma.saude",
            "senha": "admin123 (TROCAR EM PRODUCAO)",
        },
    }


@router.get("/geocodificacao/orfaos", summary="Lista bairros sem mapeamento na base geográfica")
def listar_bairros_orfaos():
    """
    Retorna a lista de bairros brutos do e-SUS que não foram encontrados
    nos arquivos GeoJSON (Bairros ou Loteamentos) e precisam de fallback via Nominatim.
    """
    rows = execute_query("""
        SELECT no_bairro_raw, dt_criacao
        FROM dashboard.tb_bairros_mapeamento
        WHERE no_bairro_canonico IS NULL
        ORDER BY no_bairro_raw
    """, {})
    
    return {"orfaos": rows, "total": len(rows)}

