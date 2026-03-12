import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Brain, History, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '../api/pressaoArterial.js'
import { dmApi } from '../api/diabetes.js'
import {
  Card, CardBody,
  PageHeader,
  StatusIcon, StatusBadge,
  CommandBlock,
  StepHeader,
  LoadingState, ErrorState,
} from '../components/ui.jsx'

// ── constantes ───────────────────────────────────────────────────────────────

const VIEWS = ['mv_pa_medicoes', 'mv_pa_cadastros', 'mv_pa_medicoes_cidadaos']

const MODELOS = [
  { id: 'has', nome: 'Hipertensão Arterial', apiInfo: () => api.modeloInfo(),   apiStatus: () => api.modeloStatusTreino() },
  { id: 'dm',  nome: 'Diabetes Mellitus',    apiInfo: () => dmApi.modeloInfo(), apiStatus: () => dmApi.modeloStatusTreino() },
]

const TP_LABELS = {
  treino_has: 'Treino HAS',
  treino_dm: 'Treino DM',
  normalizacao_bairros: 'Normalização',
  refresh_views: 'Refresh Views',
}

// ── componente principal ──────────────────────────────────────────────────────

export default function Admin() {
  const qc = useQueryClient()

  // ── status geral ──
  const { data: status, isLoading, isError, refetch } = useQuery({
    queryKey: ['admin-status'],
    queryFn: api.adminStatus,
    staleTime: 30 * 1000,
  })

  // ── modelos ML info ──
  const { data: infoHas } = useQuery({ queryKey: ['modelo-has-info'], queryFn: api.modeloInfo,   staleTime: 60_000 })
  const { data: infoDm }  = useQuery({ queryKey: ['modelo-dm-info'],  queryFn: dmApi.modeloInfo, staleTime: 60_000 })

  // ── historico de processamentos ──
  const { data: processamentos, refetch: refetchProc } = useQuery({
    queryKey: ['admin-processamentos'],
    queryFn: () => api.adminProcessamentos(null, 15),
    staleTime: 30_000,
  })

  // ── refresh de views ──
  const [refreshing, setRefreshing] = useState({})
  const [refreshResults, setRefreshResults] = useState({})

  async function handleRefresh(view) {
    setRefreshing(r => ({ ...r, [view]: true }))
    setRefreshResults(r => ({ ...r, [view]: null }))
    try {
      const res = await api.adminRefresh(view)
      setRefreshResults(r => ({ ...r, [view]: { ok: true, linhas: res.linhas } }))
      refetch()
    } catch (e) {
      setRefreshResults(r => ({ ...r, [view]: { ok: false, msg: e.message } }))
    } finally {
      setRefreshing(r => ({ ...r, [view]: false }))
    }
  }

  // ── treinamento de modelos ──
  const [treinando, setTreinando] = useState({})
  const [treinoMsg, setTreinoMsg] = useState({})

  async function handleTreinar(modulo) {
    setTreinando(r => ({ ...r, [modulo]: true }))
    setTreinoMsg(r => ({ ...r, [modulo]: null }))
    try {
      const res = await api.adminTreinar(modulo)
      setTreinoMsg(r => ({ ...r, [modulo]: { ok: true, msg: res.mensagem } }))
    } catch (e) {
      setTreinoMsg(r => ({ ...r, [modulo]: { ok: false, msg: e.message } }))
    } finally {
      // Não marca como false — será verificado no polling
      setTimeout(() => {
        setTreinando(r => ({ ...r, [modulo]: false }))
        qc.invalidateQueries({ queryKey: ['modelo-has-info'] })
        qc.invalidateQueries({ queryKey: ['modelo-dm-info'] })
        refetchProc()
      }, 5000)
    }
  }
  // ── Sincronização de Bairros (GeoJSON) ──
  const [sincronizando, setSincronizando] = useState(false)
  const [syncMsg, setSyncMsg] = useState(null)

  async function handleSincronizar() {
    setSincronizando(true)
    setSyncMsg(null)
    try {
      const res = await api.adminSincronizarBaseGeo()
      setSyncMsg({ ok: true, msg: res.mensagem })
      const poll = setInterval(async () => {
        try {
          const st = await api.adminSincronizarBaseGeoStatus()
          if (!st.em_andamento) {
            clearInterval(poll)
            setSincronizando(false)
            setSyncMsg({ 
              ok: st.status === 'concluido', 
              msg: st.status === 'concluido' 
                ? `Concluído: ${st.resultado?.exato || 0} Exatos, ${st.resultado?.fuzzy || 0} Fuzzy, ${st.resultado?.orfao || 0} Órfãos.` 
                : `Status: ${st.status}` 
            })
            // Refetches data to update the counts
            queryClient.invalidateQueries({ queryKey: ['admin-orfaos'] })
            refetch()
            refetchProc()
          } else {
            setSyncMsg({ ok: true, msg: `Sincronizando... ${st.atual}/${st.total || '?'}` })
          }
        } catch { /* continua polling */ }
      }, 5000)
    } catch (e) {
      setSincronizando(false)
      setSyncMsg({ ok: false, msg: e.message })
    }
  }

  // ── Geocodificação Fallback (Nominatim) ──
  const [geocoding, setGeocoding] = useState(false)
  const [geoMsg, setGeoMsg] = useState(null)
  const { data: orfaosData, refetch: refetchOrfaos } = useQuery({
    queryKey: ['admin-orfaos'],
    queryFn: api.adminListarOrfaos
  })
  const bairrosOrfaos = orfaosData?.orfaos || []
  const [selecionados, setSelecionados] = useState(new Set())

  function toggleOrfao(bairro) {
    const next = new Set(selecionados)
    if (next.has(bairro)) next.delete(bairro)
    else next.add(bairro)
    setSelecionados(next)
  }

  function toggleAllOrfaos() {
    if (selecionados.size === bairrosOrfaos.length) setSelecionados(new Set())
    else setSelecionados(new Set(bairrosOrfaos.map(o => o.no_bairro_raw)))
  }

  async function handleGeocodificarSelecionados() {
    const lista = Array.from(selecionados)
    if (!lista.length) return

    setGeocoding(true)
    setGeoMsg(null)
    try {
      const res = await api.adminGeocodificar(lista)
      setGeoMsg({ ok: true, msg: res.mensagem })
      const poll = setInterval(async () => {
        try {
          const st = await api.adminGeocodificarStatus()
          if (!st.em_andamento) {
            clearInterval(poll)
            setGeocoding(false)
            setSelecionados(new Set()) // limpa selecao pós sucesso
            setGeoMsg({ 
              ok: st.status === 'concluido', 
              msg: st.status === 'concluido' 
                ? `Concluído: ${st.sucesso || 0} sucesso, ${st.erros || 0} erros.` 
                : `Status: ${st.status}` 
            })
            refetchOrfaos() // Atualiza tabela de orfaos
          } else {
            setGeoMsg({ ok: true, msg: `Geocodificando via Nominatim... ${st.atual}/${st.total}` })
          }
        } catch { /* continue polling */ }
      }, 5000)
    } catch (e) {
      setGeocoding(false)
      setGeoMsg({ ok: false, msg: e.message })
    }
  }


  // ── estado derivado ──
  const s = status || {}
  const views = s.views || {}
  const norm  = s.normalizacao_bairros || {}

  const passo1Ok = s.schema_dashboard && Object.values(views).every(v => v.existe)
  const passo2Ok = s.migracao_deduplicacao?.aplicada
  const passo3Pct = norm.pct_normalizado ?? 0
  const passo3Ok  = passo3Pct >= 90
  const passo3Pending = norm.tabela_existe && passo3Pct > 0 && !passo3Ok

  // ── seção colapsável ──
  const [expandido, setExpandido] = useState({ historico: false })
  const toggle = key => setExpandido(e => ({ ...e, [key]: !e[key] }))

  return (
    <div className="space-y-6">
      <PageHeader title="Administração" description="Configuração, modelos de ML e histórico de processamentos">
        <button
          onClick={() => refetch()}
          className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-800 border border-slate-300 rounded-lg px-3 py-1.5 hover:bg-slate-50 transition-colors"
        >
          <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
          Atualizar
        </button>
      </PageHeader>

      {isError && <ErrorState message="Não foi possível verificar o status. O backend está rodando?" onRetry={refetch} />}

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* SEÇÃO: MODELOS DE ML                                              */}
      {/* ═══════════════════════════════════════════════════════════════════ */}

      <Card className="overflow-hidden">
        <StepHeader
          number={<Brain size={16} />}
          title="Modelos de Machine Learning"
          description="Treine ou re-treine os modelos diretamente pelo painel"
          color="bg-purple-600"
        />
        <CardBody className="space-y-4">
          {MODELOS.map(m => {
            const infoMap = { has: infoHas, dm: infoDm}
            const info = infoMap[m.id]
            const msg = treinoMsg[m.id]
            return (
              <div key={m.id} className="p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800">{m.nome}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {info?.disponivel
                        ? `Treinado em: ${new Date(info.treinado_em).toLocaleDateString('pt-BR')} — ${info.total_registros?.toLocaleString('pt-BR')} registros`
                        : 'Modelo não treinado'}
                    </p>
                    {info?.metricas && (
                      <div className="flex gap-3 mt-1.5">
                        {Object.entries(info.metricas).slice(0, 3).map(([k, v]) => (
                          <span key={k} className="text-xs text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200">
                            {k.toUpperCase()}: <span className="font-medium">{(v.media ?? v).toFixed ? (v.media ?? v).toFixed(3) : v}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => handleTreinar(m.id)}
                    disabled={treinando[m.id]}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                  >
                    <Brain size={14} className={treinando[m.id] ? 'animate-pulse' : ''} />
                    {treinando[m.id] ? 'Treinando…' : info?.disponivel ? 'Re-treinar' : 'Treinar'}
                  </button>
                </div>
                {msg && (
                  <p className={`text-xs ${msg.ok ? 'text-green-700' : 'text-red-600'}`}>{msg.msg}</p>
                )}
              </div>
            )
          })}
        </CardBody>
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* SEÇÃO: HISTÓRICO DE PROCESSAMENTOS                                */}
      {/* ═══════════════════════════════════════════════════════════════════ */}

      <Card className="overflow-hidden">
        <button
          onClick={() => toggle('historico')}
          className="w-full px-5 py-4 border-b border-slate-100 flex items-center gap-3 hover:bg-slate-50 transition-colors"
        >
          <span className="w-7 h-7 rounded-full bg-indigo-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
            <History size={14} />
          </span>
          <div className="flex-1 text-left">
            <h2 className="font-semibold text-slate-800">Histórico de processamentos</h2>
            <p className="text-xs text-slate-500">Normalizações, treinamentos de ML e refreshes recentes</p>
          </div>
          {expandido.historico ? <ChevronUp size={18} className="text-slate-400" /> : <ChevronDown size={18} className="text-slate-400" />}
        </button>
        {expandido.historico && (
          <CardBody className="p-0">
            {!processamentos || processamentos.length === 0 ? (
              <p className="text-sm text-slate-500 px-5 py-4">Nenhum processamento registrado.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-slate-50 text-slate-600 text-xs">
                      <th className="text-left px-4 py-2 font-medium">Tipo</th>
                      <th className="text-left px-4 py-2 font-medium">Início</th>
                      <th className="text-left px-4 py-2 font-medium">Duração</th>
                      <th className="text-left px-4 py-2 font-medium">Status</th>
                      <th className="text-right px-4 py-2 font-medium">Registros</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {processamentos.map((p, i) => {
                      const inicio = p.dt_inicio ? new Date(p.dt_inicio) : null
                      const fim = p.dt_fim ? new Date(p.dt_fim) : null
                      const duracao = inicio && fim ? Math.round((fim - inicio) / 1000) : null
                      const statusColor = p.st_status === 'concluido' ? 'text-green-700 bg-green-50' : p.st_status === 'erro' ? 'text-red-700 bg-red-50' : 'text-amber-700 bg-amber-50'
                      return (
                        <tr key={p.co_seq || i} className="hover:bg-slate-50">
                          <td className="px-4 py-2.5 font-medium text-slate-700">
                            {TP_LABELS[p.tp_processamento] || p.tp_processamento}
                            {p.ds_modelo && <span className="text-xs text-slate-400 ml-1">({p.ds_modelo})</span>}
                          </td>
                          <td className="px-4 py-2.5 text-slate-600">
                            {inicio?.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) ?? '—'}
                          </td>
                          <td className="px-4 py-2.5 text-slate-600">
                            {duracao != null ? (duracao >= 60 ? `${Math.floor(duracao/60)}min ${duracao%60}s` : `${duracao}s`) : '—'}
                          </td>
                          <td className="px-4 py-2.5">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${statusColor}`}>{p.st_status}</span>
                          </td>
                          <td className="px-4 py-2.5 text-right text-slate-600">
                            {p.qt_registros?.toLocaleString('pt-BR') ?? '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </CardBody>
        )}
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* PASSO 1: Setup inicial                                            */}
      {/* ═══════════════════════════════════════════════════════════════════ */}

      <Card className="overflow-hidden">
        <StepHeader number="1" title="Setup inicial" description="Cria o schema, tabelas de suporte e views materializadas" badge={!isLoading && <StatusBadge ok={passo1Ok} />} />
        <CardBody className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="flex items-center gap-2 text-sm">
              <StatusIcon ok={s.schema_dashboard} />
              <span className="text-slate-700">Schema <code className="text-xs bg-slate-100 px-1 rounded">dashboard</code></span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <StatusIcon ok={s.tb_auditoria_outliers} />
              <span className="text-slate-700">Tabela de auditoria</span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <StatusIcon ok={s.vw_bairro_canonico} />
              <span className="text-slate-700">vw_bairro_canonico</span>
            </div>
            {VIEWS.map(v => (
              <div key={v} className="flex items-center gap-2 text-sm">
                <StatusIcon ok={views[v]?.existe} />
                <span className="text-slate-700 truncate" title={v}>
                  {v.replace('mv_pa_', '')}
                  {views[v]?.linhas != null && (
                    <span className="text-slate-400 ml-1 text-xs">({views[v].linhas.toLocaleString('pt-BR')})</span>
                  )}
                </span>
              </div>
            ))}
          </div>

          {!passo1Ok && (
            <div className="pt-2 border-t border-slate-100">
              <p className="text-xs font-medium text-slate-600 mb-2">Execute na pasta <code className="bg-slate-100 px-1 rounded">plataforma-saude/backend</code>:</p>
              <CommandBlock cmd="python scripts/setup.py" description="Cria schema, tabelas e todas as views materializadas" />
            </div>
          )}
        </CardBody>
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* PASSO 2: Deduplicação                                             */}
      {/* ═══════════════════════════════════════════════════════════════════ */}

      <Card className="overflow-hidden">
        <StepHeader number="2" title="Migração — Deduplicação de cadastros" badge={!isLoading && <StatusBadge ok={passo2Ok} labels={['Aplicada', 'Pendente', 'Não aplicada']} />} />
        <CardBody className="space-y-3">
          <div className="flex items-start gap-2 text-sm">
            <StatusIcon ok={passo2Ok} />
            <div>
              <span className="text-slate-700">Índice único <code className="text-xs bg-slate-100 px-1 rounded">idx_mv_pa_cad_cidadao_pec</code></span>
              {passo2Ok
                ? <p className="text-xs text-green-700 mt-0.5">Deduplicação ativa — cada cidadão aparece uma vez.</p>
                : <p className="text-xs text-amber-700 mt-0.5">Migração pendente — pode haver contagem inflada.</p>
              }
            </div>
          </div>

          {!passo2Ok && (
            <div className="pt-2 border-t border-slate-100">
              <CommandBlock cmd="python scripts/migrar_mv_cadastros.py --dry-run" description="Verificar o plano sem executar" />
              <CommandBlock cmd="python scripts/migrar_mv_cadastros.py" description="Executar a migração (~1-2 min)" />
            </div>
          )}
        </CardBody>
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* PASSO 3: Sincronização da Base Geográfica Oficial                   */}
      {/* ═══════════════════════════════════════════════════════════════════ */}

      <Card className="overflow-hidden">
        <StepHeader number="3" title="Sincronização Geográfica Oficial" description="Mapeia todos os bairros do e-SUS para os Bairros e Loteamentos em GeoJSON (100% Offline)" />
        <CardBody className="space-y-3">
          <div className="text-sm text-slate-600 bg-slate-50 rounded-lg p-3 space-y-1">
            <p><span className="font-medium">O que isso faz?</span> Lê os nomes descritivos inseridos no e-SUS e tenta encontrar a localização geocodificada exata na nossa base de Loteamentos e Bairros (fornecida via arquivos GeoJSON).</p>
            <p><span className="font-medium">Vantagem:</span> Instantâneo e não depende de APIs da internet. O que não for encontrado ficará disponível para ajuste manual ou Nominatim no Passo 4.</p>
          </div>

          <div className="pt-2 border-t border-slate-100 flex flex-wrap gap-2 items-center">
            <button
              onClick={handleSincronizar}
              disabled={sincronizando}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {sincronizando ? '⏳ Sincronizando…' : 'Sincronizar Bairros e Mapa'}
            </button>
            {syncMsg && (
              <span className={`text-xs ml-2 ${syncMsg.ok ? 'text-green-700 font-medium' : 'text-red-600 font-medium'}`}>{syncMsg.msg}</span>
            )}
          </div>
        </CardBody>
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* PASSO 4: Fallback Geográfico (Nominatim)                            */}
      {/* ═══════════════════════════════════════════════════════════════════ */}

      <Card className="overflow-hidden">
        <StepHeader number="4" title="Geocodificação Avançada (Fallback Nominatim)" description="Tratamento de bairros ou distritos que não pertencem ao mapa urbano oficial." />
        <CardBody className="space-y-4">
          <div className="text-sm text-slate-600 bg-amber-50 rounded-lg p-3 space-y-1 border border-amber-100">
            <p>
              Encontramos <span className="font-bold text-amber-700">{bairrosOrfaos.length}</span> registros que não bateram com a base geográfica da prefeitura. 
              Isso geralmente ocorre com Distritos Rurais (ex: Inhobim, Bate Pé) ou ocupações irregulares recentes.
            </p>
          </div>

          {bairrosOrfaos.length > 0 && (
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <div className="bg-slate-50 px-4 py-2 border-b border-slate-200 flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Registros Órfãos (e-SUS)</span>
                <span className="text-xs font-medium bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full">{selecionados.size} selecionados</span>
              </div>
              <div className="max-h-64 overflow-y-auto">
                <table className="w-full text-sm text-left">
                  <thead className="sticky top-0 bg-slate-100 text-slate-600 text-xs shadow-sm">
                    <tr>
                      <th className="px-4 py-2 w-10 text-center">
                        <input 
                          type="checkbox" 
                          className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer" 
                          checked={selecionados.size === bairrosOrfaos.length && bairrosOrfaos.length > 0} 
                          onChange={toggleAllOrfaos}
                        />
                      </th>
                      <th className="px-4 py-2 font-medium">Nome Digitado no e-SUS</th>
                      <th className="px-4 py-2 font-medium w-32">Registrado em</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {bairrosOrfaos.map((orf, i) => (
                      <tr 
                        key={i} 
                        className={`hover:bg-blue-50 cursor-pointer transition-colors ${selecionados.has(orf.no_bairro_raw) ? 'bg-blue-50' : 'bg-white'}`}
                        onClick={() => toggleOrfao(orf.no_bairro_raw)}
                      >
                        <td className="px-4 py-2 text-center" onClick={(e) => e.stopPropagation()}>
                          <input 
                            type="checkbox" 
                            className="rounded border-slate-300 text-blue-600 focus:ring-blue-500 cursor-pointer" 
                            checked={selecionados.has(orf.no_bairro_raw)}
                            onChange={() => toggleOrfao(orf.no_bairro_raw)}
                          />
                        </td>
                        <td className="px-4 py-2 font-medium text-slate-700 truncate max-w-[200px]" title={orf.no_bairro_raw}>{orf.no_bairro_raw}</td>
                        <td className="px-4 py-2 text-xs text-slate-500">
                          {new Date(orf.dt_criacao).toLocaleDateString('pt-BR')}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="pt-2 flex flex-wrap gap-2 items-center">
            <button
              onClick={handleGeocodificarSelecionados}
              disabled={geocoding || selecionados.size === 0}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-indigo-600 border border-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {geocoding ? '⏳ Buscando no Nominatim…' : `Tentar Achar Coordenada (${selecionados.size})`}
            </button>
            <button
              onClick={() => api.exportarGeocode()}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-slate-100 border border-slate-300 text-slate-700 hover:bg-slate-200 transition-colors ml-auto"
            >
              Exportar Coordenadas Salvas (CSV)
            </button>
            {geoMsg && (
              <span className={`text-xs ml-2 w-full mt-2 ${geoMsg.ok ? 'text-green-700 font-medium' : 'text-red-600 font-medium'}`}>{geoMsg.msg}</span>
            )}
          </div>
        </CardBody>
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* PASSO 5: Refresh de views                                         */}
      {/* ═══════════════════════════════════════════════════════════════════ */}

      <Card className="overflow-hidden">
        <StepHeader number="5" title="Atualização das views" description="Atualize as views para refletir novos dados do e-SUS" />
        <CardBody className="space-y-4">
          <div className="space-y-3">
            {VIEWS.map(v => {
              const res = refreshResults[v]
              return (
                <div key={v} className="flex items-center justify-between gap-3 p-3 rounded-lg bg-slate-50 border border-slate-200">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 font-mono">{v}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {views[v]?.linhas != null ? `${views[v].linhas.toLocaleString('pt-BR')} linhas` : 'View não encontrada'}
                    </p>
                    {res && (
                      <p className={`text-xs mt-1 ${res.ok ? 'text-green-700' : 'text-red-600'}`}>
                        {res.ok ? `Atualizada — ${res.linhas?.toLocaleString('pt-BR')} linhas` : `Erro: ${res.msg}`}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleRefresh(v)}
                    disabled={refreshing[v] || !views[v]?.existe}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-blue-300 text-blue-700 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                  >
                    <RefreshCw size={13} className={refreshing[v] ? 'animate-spin' : ''} />
                    {refreshing[v] ? 'Atualizando…' : 'Refresh'}
                  </button>
                </div>
              )
            })}
          </div>

          <div className="pt-2 border-t border-slate-100">
            <CommandBlock cmd="python scripts/setup.py" description="Ou via terminal, para todas de uma vez" />
          </div>
        </CardBody>
      </Card>

      {/* ═══════════════════════════════════════════════════════════════════ */}
      {/* PASSO 5: Exportar bairros (opcional)                              */}
      {/* ═══════════════════════════════════════════════════════════════════ */}

      <Card className="overflow-hidden">
        <StepHeader number="5" title="Exportar dados de bairros" description="Gera JSON para ferramentas externas" color="bg-slate-400" />
        <CardBody>
          <CommandBlock cmd="python scripts/exportar_bairros.py" description="Gera data/bairros_analise.json com indicadores por bairro" />
          <p className="text-xs text-slate-500 mt-2">
            Ou via API: <code className="bg-slate-100 px-1 rounded">GET /api/v1/pressao-arterial/bairros/exportar</code>
          </p>
        </CardBody>
      </Card>
    </div>
  )
}
