import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dmApi } from '../../api/diabetes.js'
import { useAuth } from '../../contexts/AuthContext.jsx'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, Cell,
} from 'recharts'
import { Activity, Users, CheckCircle, XCircle, TrendingUp, Search } from 'lucide-react'

// ── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, color = 'emerald' }) {
  const colors = {
    emerald: 'text-emerald-600 bg-emerald-50',
    blue:    'text-blue-600 bg-blue-50',
    amber:   'text-amber-600 bg-amber-50',
    red:     'text-red-600 bg-red-50',
  }
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-start gap-3">
      <div className={`p-2 rounded-lg ${colors[color]}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-xl font-bold text-slate-800">{value ?? '—'}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

// ── Formatadores ──────────────────────────────────────────────────────────────

const fmtN = v => v != null ? Number(v).toLocaleString('pt-BR') : '—'
const fmtPct = v => v != null ? `${v}%` : '—'
const fmtHba1c = v => v != null ? `${Number(v).toFixed(1)}%` : '—'

const LIMITE_PAGINA = 50
const anoAtual = new Date().getFullYear()

// ── Gráfico tendência ─────────────────────────────────────────────────────────

function GraficoTendencia({ data }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="mes_ano" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="hba1c" domain={[5, 10]} tick={{ fontSize: 11 }} unit="%" />
        <YAxis yAxisId="qtd" orientation="right" tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        <Line
          yAxisId="hba1c"
          type="monotone"
          dataKey="media_hba1c"
          name="HbA1c média"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
        />
        <Line
          yAxisId="qtd"
          type="monotone"
          dataKey="total_exames"
          name="Total exames"
          stroke="#94a3b8"
          strokeWidth={1.5}
          dot={false}
          strokeDasharray="4 2"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Gráfico histograma HbA1c ──────────────────────────────────────────────────

function GraficoHistograma({ data }) {
  if (!data?.length) return null

  const cor = (faixa) => {
    const v = parseFloat(faixa)
    if (v < 7) return '#10b981'
    if (v < 8) return '#f59e0b'
    return '#ef4444'
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="faixa_hba1c" tick={{ fontSize: 10 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => fmtN(v)} />
        <Bar dataKey="quantidade" name="Exames" radius={[3, 3, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={cor(entry.faixa_hba1c)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

const GRUPO_LABELS = {
  adulto:      'Adultos (18–64)',
  idoso_65_79: 'Idosos (65–79)',
  'idoso_80+': 'Idosos (≥80)',
}

// ── Página principal (filtros unificados, dados dos endpoints) ─────────────────

export default function DmPainel() {
  const { usuario } = useAuth?.() || {}
  const isGestor =
    usuario?.nome?.toLowerCase() === 'gestor' ||
    usuario?.perfil?.toLowerCase() === 'admin'

  const [busca, setBusca] = useState('')
  const [filtroUbsGestor, setFiltroUbsGestor] = useState('')
  const [filtroFaixa, setFiltroFaixa] = useState('')
  const [filtroStatus, setFiltroStatus] = useState('')
  const [filtroArea, setFiltroArea] = useState('')
  const [filtroMicroarea, setFiltroMicroarea] = useState('')
  const [anoInicio, setAnoInicio] = useState(anoAtual - 1)
  const [anoFim, setAnoFim] = useState(anoAtual)
  const [offset, setOffset] = useState(0)

  const coUnidadeSaudeAtiva = isGestor
    ? (filtroUbsGestor ? Number(filtroUbsGestor) : undefined)
    : undefined

  const paramsIndividuos = (() => {
    const p = {
      limite: LIMITE_PAGINA,
      offset,
      faixa_etaria: filtroFaixa || undefined,
      controle_status: filtroStatus || undefined,
      nu_area: filtroArea || undefined,
      nu_micro_area: filtroMicroarea || undefined,
      co_unidade_saude: coUnidadeSaudeAtiva || undefined,
    }
    const termo = busca.trim()
    if (termo) {
      const cod = Number(termo)
      if (Number.isInteger(cod) && !Number.isNaN(cod)) p.co_cidadao = cod
      else p.no_cidadao = termo
    }
    return p
  })()

  const paramsAno = { ano_inicio: anoInicio, ano_fim: anoFim }

  const { data: dadosIndividuos, isLoading: loadIndividuos, isError: errIndividuos } = useQuery({
    queryKey: ['dm-individuos', busca, filtroUbsGestor, filtroFaixa, filtroStatus, filtroArea, filtroMicroarea, offset],
    queryFn: () => dmApi.individuos(paramsIndividuos),
    keepPreviousData: true,
  })

  const { data: ubsData } = useQuery({
    queryKey: ['dm-ubs-lista'],
    queryFn: () => dmApi.ubs({}),
    enabled: isGestor,
    staleTime: 60_000,
  })
  const listaUbs = ubsData?.dados ?? []

  const { data: kpis, isLoading: loadKpis } = useQuery({
    queryKey: ['dm-kpis'],
    queryFn: dmApi.kpis,
  })

  const { data: tendencia, isLoading: loadTend } = useQuery({
    queryKey: ['dm-tendencia', paramsAno],
    queryFn: () => dmApi.tendencia(paramsAno),
  })

  const { data: histograma, isLoading: loadHist } = useQuery({
    queryKey: ['dm-hba1c-faixa', paramsAno],
    queryFn: () => dmApi.hba1cFaixa(paramsAno),
  })

  const { data: faixaEtaria, isLoading: loadFaixaEtaria } = useQuery({
    queryKey: ['dm-hba1c-faixa-etaria', paramsAno],
    queryFn: () => dmApi.hba1cFaixaEtaria(paramsAno),
  })

  const totalMonitorado = dadosIndividuos?.total ?? 0
  const totalControlados = dadosIndividuos?.total_controlados ?? 0
  const totalDescontrolados = dadosIndividuos?.total_descontrolados ?? 0
  const dados = dadosIndividuos?.dados ?? []
  const temDadosTendencia = Array.isArray(tendencia) && tendencia.length > 0
  const temDadosHistograma = Array.isArray(histograma) && histograma.length > 0
  const temDadosFaixaEtaria = Array.isArray(faixaEtaria) && faixaEtaria.length > 0

  // ── Painel extra para gestor: controle glicêmico agregado ────────────────────
  const { data: controleGrupo, isLoading: loadControleGrupo } = useQuery({
    queryKey: ['dm-controle-grupo-gestor', paramsAno],
    queryFn: () => dmApi.controleGrupo(paramsAno),
    enabled: isGestor,
  })

  const dadosFaixaPorStatus = useMemo(() => {
    if (!Array.isArray(controleGrupo)) return { controlados: [], descontrolados: [] }
    const base = { Controlado: [], Descontrolado: [] }
    for (const row of controleGrupo) {
      const status = row.controle_glicemico
      if (!base[status]) continue
      base[status].push({
        faixa_etaria: row.grupo_etario,
        total: Number(row.total ?? 0),
      })
    }
    return {
      controlados: base.Controlado.sort((a, b) => a.faixa_etaria.localeCompare(b.faixa_etaria)),
      descontrolados: base.Descontrolado.sort((a, b) => a.faixa_etaria.localeCompare(b.faixa_etaria)),
    }
  }, [controleGrupo])

  const dadosAreaMicro = useMemo(() => {
    if (!Array.isArray(dados)) return []
    const agg = new Map()
    for (const row of dados) {
      const terr = row.territorio || {}
      const area = terr.area ?? '—'
      const micro = terr.microarea ?? '—'
      const status = row.status_atual || 'Indefinido'
      const key = `${area}|${micro}`
      const prev = agg.get(key) || {
        area,
        microarea: micro,
        controlados: 0,
        descontrolados: 0,
      }
      if (status === 'Controlado') prev.controlados += 1
      else if (status === 'Descontrolado') prev.descontrolados += 1
      agg.set(key, prev)
    }
    return Array.from(agg.values()).sort((a, b) => {
      if (a.area === b.area) return `${a.microarea}`.localeCompare(`${b.microarea}`)
      return `${a.area}`.localeCompare(`${b.area}`)
    })
  }, [dados])

  return (
    <div className="p-6 space-y-6 bg-slate-50 min-h-screen font-sans text-slate-900">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Painel — Diabetes Mellitus</h1>
        <p className="text-sm text-slate-500 mt-1">
          Controle glicêmico baseado em HbA1c · Critérios SBD 2024
        </p>
      </div>

      {/* KPIs: Total monitorado, Controlados e Descontrolados vêm de /individuos; Total exames e HbA1c média de /kpis */}
      {loadKpis && loadIndividuos ? (
        <p className="text-sm text-slate-400">Carregando KPIs...</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <KpiCard label="Total monitorado" value={fmtN(totalMonitorado)} icon={Users} color="emerald" />
          <KpiCard label="HbA1c média" value={fmtHba1c(kpis?.media_hba1c)} icon={TrendingUp} color="amber" />
          <KpiCard label="Controlados" value={fmtN(totalControlados)} sub={totalMonitorado ? fmtPct((totalControlados / totalMonitorado * 100).toFixed(1)) : null} icon={CheckCircle} color="emerald" />
          <KpiCard label="Descontrolados" value={fmtN(totalDescontrolados)} icon={XCircle} color="red" />

          {/* Filtro de ano (apenas para gráficos) — estilo KPI */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-start gap-3">
            <div className="p-2 rounded-lg text-slate-600 bg-slate-50">
              <TrendingUp size={18} />
            </div>
            <div className="flex-1">
              <p className="text-xs text-slate-500">Ano (gráficos)</p>
              <div className="mt-1 flex items-center ">
                <input
                  type="number"
                  value={anoInicio}
                  onChange={(e) => setAnoInicio(Number(e.target.value) || anoAtual - 1)}
                  min={2000}
                  max={anoAtual}
                  className="border border-slate-300 rounded-lg px-2 py-1.5 text-sm w-18 outline-none bg-white"
                />
                <span className="text-slate-400">–</span>
                <input
                  type="number"
                  value={anoFim}
                  onChange={(e) => setAnoFim(Number(e.target.value) || anoAtual)}
                  min={2000}
                  max={anoAtual}
                  className="border border-slate-300 rounded-lg px-2 py-1.5 text-sm w-18 outline-none bg-white"
                />
              </div>
              <p className="text-[11px] text-slate-400 mt-1">Aplica-se aos gráficos</p>
            </div>
          </div>
        </div>
      )}

      {/* Gráficos (dados dos endpoints; mensagem quando não houver dados) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-800 mb-4">HbA1c média mensal</h2>
          {loadTend && <p className="text-sm text-slate-400">Carregando...</p>}
          {!loadTend && temDadosTendencia && <GraficoTendencia data={tendencia} />}
          {!loadTend && !temDadosTendencia && <p className="text-sm text-slate-400">Sem dados para o período selecionado.</p>}
        </div>

        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-800 mb-1">Distribuição de HbA1c</h2>
          <p className="text-xs text-slate-400 mb-3">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />{'<7%: Controlado · '}
            <span className="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1" />{'7–8%: Atenção · '}
            <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />{'>8%: Descontrolado'}
          </p>
          {loadHist && <p className="text-sm text-slate-400">Carregando...</p>}
          {!loadHist && temDadosHistograma && <GraficoHistograma data={histograma} />}
          {!loadHist && !temDadosHistograma && <p className="text-sm text-slate-400">Sem dados para o período selecionado.</p>}
        </div>
      </div>

      {/* Painel do Gestor — apenas para usuários gestores */}
      {isGestor && (
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-800 mb-4">
              Distribuição por Área e Microárea (APS)
            </h2>
            <p className="text-xs text-slate-500 mb-3">
              Cidadãos em acompanhamento com último HbA1c em 12 meses, agrupados por território.
            </p>
            {loadIndividuos ? (
              <p className="text-sm text-slate-400">Carregando...</p>
            ) : dadosAreaMicro.length === 0 ? (
              <p className="text-sm text-slate-400">
                Nenhum registro encontrado para os filtros atuais.
              </p>
            ) : (
              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={dadosAreaMicro} margin={{ top: 10, right: 16, left: 0, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis
                    dataKey="microarea"
                    tickFormatter={(v, idx) => {
                      const row = dadosAreaMicro[idx]
                      return row ? `${row.area}-${row.microarea}` : v
                    }}
                    angle={-25}
                    textAnchor="end"
                    height={60}
                    tick={{ fontSize: 10 }}
                  />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="controlados" name="Controlados" stackId="a" fill="#10b981" />
                  <Bar dataKey="descontrolados" name="Descontrolados" stackId="a" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-800 mb-4">
                Faixa etária (Controlados)
              </h2>
              {loadControleGrupo ? (
                <p className="text-sm text-slate-400">Carregando...</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={dadosFaixaPorStatus.controlados}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="faixa_etaria" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="total" name="Controlados" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-800 mb-4">
                Faixa etária (Descontrolados)
              </h2>
              {loadControleGrupo ? (
                <p className="text-sm text-slate-400">Carregando...</p>
              ) : (
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={dadosFaixaPorStatus.descontrolados}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="faixa_etaria" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Bar dataKey="total" name="Descontrolados" fill="#ef4444" />
                  </BarChart>
                </ResponsiveContainer>
              )}
            </div>
          </div>
        </div>
      )}

      {/* HbA1c por grupo etário (endpoint /hba1c/faixa-etaria) */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-4">HbA1c por grupo etário</h2>
        {loadFaixaEtaria && <p className="text-sm text-slate-400">Carregando...</p>}
        {!loadFaixaEtaria && temDadosFaixaEtaria && (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {faixaEtaria.map(row => (
              <div key={row.grupo_etario} className="bg-slate-50 rounded-lg p-4 text-center">
                <p className="text-sm font-medium text-slate-700">{GRUPO_LABELS[row.grupo_etario] ?? row.grupo_etario}</p>
                <p className="text-2xl font-bold text-emerald-700 mt-1">{Number(row.media_hba1c).toFixed(1)}%</p>
                <p className="text-xs text-slate-400 mt-0.5">
                  Meta: {row.meta_sbd}% · {fmtN(row.total_exames)} exames
                </p>
              </div>
            ))}
          </div>
        )}
        {!loadFaixaEtaria && !temDadosFaixaEtaria && <p className="text-sm text-slate-400">Sem dados para o período selecionado.</p>}
      </div>

      {/* Filtros do prontuário (aplicados ao painel e à tabela) */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap gap-3 items-end shadow-sm">
        {isGestor && (
          <div>
            <label className="block text-xs font-medium text-slate-600 mb-1">USF/UBS</label>
            <select
              value={filtroUbsGestor}
              onChange={(e) => { setFiltroUbsGestor(e.target.value); setOffset(0) }}
              className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-60 outline-none bg-white"
            >
              <option value="">Todas as USFs/UBSs</option>
              {listaUbs.map(u => (
                <option key={u.co_seq_unidade_saude} value={u.co_seq_unidade_saude}>
                  {u.no_unidade_saude}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex-1 min-w-[180px]">
          <label className="block text-xs font-medium text-slate-600 mb-1">Paciente (nome ou código)</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
            <input
              type="text"
              placeholder="Buscar..."
              value={busca}
              onChange={(e) => { setBusca(e.target.value); setOffset(0); }}
              className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 w-full"
            />
          </div>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Faixa etária</label>
          <select
            value={filtroFaixa}
            onChange={(e) => { setFiltroFaixa(e.target.value); setOffset(0); }}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-44 outline-none bg-white"
          >
            <option value="">Todas</option>
            <option value="18-29">18-29 anos</option>
            <option value="30-39">30-39 anos</option>
            <option value="40-49">40-49 anos</option>
            <option value="50-59">50-59 anos</option>
            <option value="60-64">60-64 anos</option>
            <option value="65+">65+ anos</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Área</label>
          <input
            type="text"
            value={filtroArea}
            onChange={(e) => { setFiltroArea(e.target.value); setOffset(0); }}
            placeholder="Ex: 046"
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-24 outline-none bg-white"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Microárea</label>
          <input
            type="text"
            value={filtroMicroarea}
            onChange={(e) => { setFiltroMicroarea(e.target.value); setOffset(0); }}
            placeholder="Ex: 03"
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-24 outline-none bg-white"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
          <select
            value={filtroStatus}
            onChange={(e) => { setFiltroStatus(e.target.value); setOffset(0); }}
            className="border border-slate-300 rounded-lg px-3 py-2 text-sm w-40 outline-none bg-white"
          >
            <option value="">Todos</option>
            <option value="Controlado">Controlado</option>
            <option value="Descontrolado">Descontrolado</option>
          </select>
        </div>

      </div>

      {/* Prontuário (dados de /individuos com os mesmos filtros) */}
      <TabelaProntuario
        dados={dados}
        total={totalMonitorado}
        isLoading={loadIndividuos}
        isError={errIndividuos}
        offset={offset}
        setOffset={setOffset}
      />
    </div>
  )
}

// ── Tabela de Prontuário (apresentação; dados vêm do pai) ─────────────────────

function TabelaProntuario({ dados, total, isLoading, isError, offset, setOffset }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      <div className="p-5 border-b border-slate-100">
        <h2 className="text-lg font-semibold text-slate-800">Prontuário e Acompanhamento</h2>
        <p className="text-sm text-slate-500 mt-1">
          Pacientes em acompanhamento (último HbA1c em 12 meses) · Critérios SBD
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-slate-50 text-slate-600 font-medium border-b border-slate-200">
            <tr>
              <th className="px-6 py-4">Paciente / Perfil</th>
              <th className="px-6 py-4">Território</th>
              <th className="px-6 py-4">HbA1c (último)</th>
              <th className="px-6 py-4">Outras Condições</th>
              <th className="px-6 py-4 text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-slate-700">
            {isError && (
              <tr>
                <td colSpan="5" className="px-6 py-8 text-center text-red-600">
                  Erro ao carregar dados da API.
                </td>
              </tr>
            )}
            {!isError && isLoading && (
              <tr>
                <td colSpan="5" className="px-6 py-8 text-center text-slate-400">
                  Carregando...
                </td>
              </tr>
            )}
            {!isError && !isLoading && dados.length === 0 && (
              <tr>
                <td colSpan="5" className="px-6 py-8 text-center text-slate-400">
                  Nenhum paciente encontrado para os filtros informados.
                </td>
              </tr>
            )}
            {!isError && !isLoading && dados.length > 0 && dados.map((row) => {
              const perfil = row.paciente_perfil || {}
              const terr = row.territorio || {}
              const hba1c = row.hba1c_atual
              const isControlado = row.status_atual === 'Controlado'
              return (
                <tr key={row.co_cidadao} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-slate-900">{perfil.nome ?? row.co_cidadao}</div>
                    <div className="text-xs text-slate-500 mt-0.5">
                      {perfil.idade != null && `${perfil.idade} anos`} · Sexo: {perfil.sexo ?? '—'}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-slate-700">Área {terr.area ?? '—'}</div>
                    <div className="text-xs text-slate-500">Microárea {terr.microarea ?? '—'}</div>
                  </td>
                  <td className="px-6 py-4">
                    {hba1c?.valor != null ? (
                      <span className="font-mono font-medium">{Number(hba1c.valor).toFixed(1)}%</span>
                    ) : '—'}
                    {hba1c?.data && (
                      <div className="text-xs text-slate-500 mt-0.5">{hba1c.data}</div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {row.outras_condicoes?.length > 0 ? (
                      <div className="flex flex-wrap gap-1">
                        {row.outras_condicoes.map((c, i) => (
                          <span key={i} className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 rounded font-medium">
                            {c}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span className="text-slate-400 text-xs italic">Nenhuma informada</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${
                      isControlado ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'
                    }`}>
                      {row.status_atual ?? '—'}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {total > 0 && (
        <div className="px-5 py-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-sm">
          <span className="text-slate-500 font-medium">
            Mostrando <b>{dados.length}</b> de <b>{total}</b> registros
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setOffset(Math.max(0, offset - LIMITE_PAGINA))}
              disabled={offset === 0}
              className="px-4 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-600 font-medium disabled:opacity-50 hover:bg-slate-50"
            >
              Anterior
            </button>
            <button
              type="button"
              onClick={() => setOffset(offset + LIMITE_PAGINA)}
              disabled={offset + LIMITE_PAGINA >= total}
              className="px-4 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-600 font-medium disabled:opacity-50 hover:bg-slate-50"
            >
              Próxima
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
