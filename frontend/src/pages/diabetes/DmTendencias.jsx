import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dmApi } from '../../api/diabetes.js'
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, Cell,
} from 'recharts'

const fmtN = v => v != null ? Number(v).toLocaleString('pt-BR') : '—'

// ── Filtros ───────────────────────────────────────────────────────────────────

function Filtros({ params, setParams }) {
  return (
    <div className="flex flex-wrap gap-3">
      <div>
        <label className="block text-xs text-slate-500 mb-1">Ano início</label>
        <input
          type="number" min={2015} max={2030}
          value={params.ano_inicio ?? ''}
          onChange={e => setParams(p => ({ ...p, ano_inicio: e.target.value || null }))}
          className="border border-slate-200 rounded-lg px-2 py-1.5 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          placeholder="2020"
        />
      </div>
      <div>
        <label className="block text-xs text-slate-500 mb-1">Ano fim</label>
        <input
          type="number" min={2015} max={2030}
          value={params.ano_fim ?? ''}
          onChange={e => setParams(p => ({ ...p, ano_fim: e.target.value || null }))}
          className="border border-slate-200 rounded-lg px-2 py-1.5 text-sm w-24 focus:outline-none focus:ring-2 focus:ring-emerald-400"
          placeholder="2024"
        />
      </div>
    </div>
  )
}

// ── Gráfico de área empilhada — controlados vs descontrolados ─────────────────

function GraficoAreaEmpilhada({ data }) {
  if (!data?.length) return <p className="text-sm text-slate-400">Sem dados.</p>

  // Pivota por ano + grupo_etario
  const anos = [...new Set(data.map(d => d.ano))].sort()
  const pivotado = anos.map(ano => {
    const rows = data.filter(d => d.ano === ano)
    const ctrl = rows.filter(d => d.controle_glicemico === 'Controlado').reduce((s, d) => s + (d.quantidade ?? 0), 0)
    const desc = rows.filter(d => d.controle_glicemico === 'Descontrolado').reduce((s, d) => s + (d.quantidade ?? 0), 0)
    return { ano, controlados: ctrl, descontrolados: desc }
  })

  return (
    <ResponsiveContainer width="100%" height={260}>
      <AreaChart data={pivotado} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="ano" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={v => fmtN(v)} />
        <Legend />
        <Area type="monotone" dataKey="controlados" name="Controlados" stackId="1" stroke="#10b981" fill="#d1fae5" />
        <Area type="monotone" dataKey="descontrolados" name="Descontrolados" stackId="1" stroke="#ef4444" fill="#fee2e2" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

// ── Gráfico tendência HbA1c mensal ────────────────────────────────────────────

function GraficoTendenciaHba1c({ data }) {
  if (!data?.length) return <p className="text-sm text-slate-400">Sem dados.</p>

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="mes_ano" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
        <YAxis domain={[5.5, 10]} tick={{ fontSize: 11 }} unit="%" />
        <Tooltip formatter={(v, name) => [name === 'HbA1c média' ? `${Number(v).toFixed(1)}%` : fmtN(v), name]} />
        <Legend />
        <Line type="monotone" dataKey="media_hba1c" name="HbA1c média" stroke="#10b981" strokeWidth={2} dot={false} />
        <Line type="monotone" dataKey="controlados" name="Controlados" stroke="#059669" strokeWidth={1.5} dot={false} strokeDasharray="4 2" yAxisId={0} hide />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Gráfico por sexo ──────────────────────────────────────────────────────────

const CORES_SEXO = { M: '#3b82f6', F: '#f472b6' }

function GraficoSexo({ data }) {
  if (!data?.length) return null

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="sexo" tick={{ fontSize: 11 }} />
        <YAxis domain={[0, 12]} unit="%" tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => [`${Number(v).toFixed(1)}%`, 'HbA1c média']} />
        <Bar dataKey="media_hba1c" name="HbA1c média" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={CORES_SEXO[entry.sg_sexo] ?? '#94a3b8'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function DmTendencias() {
  const [params, setParams] = useState({})

  const { data: tendencia, isLoading: loadTend } = useQuery({
    queryKey: ['dm-tendencia', params],
    queryFn: () => dmApi.tendencia(params),
  })

  const { data: controleTendencia, isLoading: loadCtrl } = useQuery({
    queryKey: ['dm-controle-tendencia', params],
    queryFn: () => dmApi.controleTendencia(params),
  })

  const { data: sexo, isLoading: loadSexo } = useQuery({
    queryKey: ['dm-hba1c-sexo', params],
    queryFn: () => dmApi.hba1cSexo(params),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Tendências — Diabetes Mellitus</h1>
        <p className="text-sm text-slate-500 mt-1">Evolução temporal do controle glicêmico na população</p>
      </div>

      <Filtros params={params} setParams={setParams} />

      {/* HbA1c mensal */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-4">HbA1c média — evolução mensal</h2>
        {loadTend ? <p className="text-sm text-slate-400">Carregando...</p> : <GraficoTendenciaHba1c data={tendencia} />}
      </div>

      {/* Controlados vs descontrolados */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-4">Controlados vs descontrolados por ano</h2>
        {loadCtrl ? <p className="text-sm text-slate-400">Carregando...</p> : <GraficoAreaEmpilhada data={controleTendencia} />}
      </div>

      {/* Por sexo */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="font-semibold text-slate-800 mb-4">HbA1c média por sexo</h2>
        {loadSexo ? <p className="text-sm text-slate-400">Carregando...</p> : <GraficoSexo data={sexo} />}
      </div>
    </div>
  )
}
