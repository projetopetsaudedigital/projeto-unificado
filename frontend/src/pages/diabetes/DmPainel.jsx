import { useQuery } from '@tanstack/react-query'
import { dmApi } from '../../api/diabetes.js'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
  BarChart, Bar, Cell,
} from 'recharts'
import { Activity, Users, CheckCircle, XCircle, TrendingUp } from 'lucide-react'

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

// ── Página principal ──────────────────────────────────────────────────────────

export default function DmPainel() {
  const { data: kpis, isLoading: loadKpis } = useQuery({
    queryKey: ['dm-kpis'],
    queryFn: dmApi.kpis,
  })

  const { data: tendencia, isLoading: loadTend } = useQuery({
    queryKey: ['dm-tendencia'],
    queryFn: () => dmApi.tendencia(),
  })

  const { data: histograma, isLoading: loadHist } = useQuery({
    queryKey: ['dm-hba1c-faixa'],
    queryFn: () => dmApi.hba1cFaixa(),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Painel — Diabetes Mellitus</h1>
        <p className="text-sm text-slate-500 mt-1">
          Controle glicêmico baseado em HbA1c · Critérios SBD 2024
        </p>
      </div>

      {/* KPIs */}
      {loadKpis ? (
        <p className="text-sm text-slate-400">Carregando KPIs...</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <KpiCard label="Pacientes diabéticos" value={fmtN(kpis?.total_diabeticos)} icon={Users} color="emerald" />
          <KpiCard label="Total de exames" value={fmtN(kpis?.total_exames)} icon={Activity} color="blue" />
          <KpiCard label="HbA1c média" value={fmtHba1c(kpis?.media_hba1c)} icon={TrendingUp} color="amber" />
          <KpiCard label="Controlados" value={fmtN(kpis?.total_controlados)} sub={fmtPct(kpis?.pct_controlados)} icon={CheckCircle} color="emerald" />
          <KpiCard label="Descontrolados" value={fmtN(kpis?.total_descontrolados)} icon={XCircle} color="red" />
        </div>
      )}

      {/* Gráficos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Tendência mensal */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-800 mb-4">HbA1c média mensal</h2>
          {loadTend ? (
            <p className="text-sm text-slate-400">Carregando...</p>
          ) : (
            <GraficoTendencia data={tendencia} />
          )}
        </div>

        {/* Histograma */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-800 mb-1">Distribuição de HbA1c</h2>
          <p className="text-xs text-slate-400 mb-3">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1" />{'<7%: Controlado · '}
            <span className="inline-block w-2 h-2 rounded-full bg-amber-400 mr-1" />{'7–8%: Atenção · '}
            <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-1" />{'>8%: Descontrolado'}
          </p>
          {loadHist ? (
            <p className="text-sm text-slate-400">Carregando...</p>
          ) : (
            <GraficoHistograma data={histograma} />
          )}
        </div>
      </div>

      {/* Grupos etários */}
      <DmGruposEtarios />
    </div>
  )
}

const GRUPO_LABELS = {
  adulto:      'Adultos (18–64)',
  idoso_65_79: 'Idosos (65–79)',
  'idoso_80+': 'Idosos (≥80)',
}

function DmGruposEtarios() {
  const { data, isLoading } = useQuery({
    queryKey: ['dm-hba1c-faixa-etaria'],
    queryFn: () => dmApi.hba1cFaixaEtaria(),
  })

  if (isLoading) return null

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h2 className="font-semibold text-slate-800 mb-4">HbA1c por grupo etário</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {data?.map(row => (
          <div key={row.grupo_etario} className="bg-slate-50 rounded-lg p-4 text-center">
            <p className="text-sm font-medium text-slate-700">{GRUPO_LABELS[row.grupo_etario] ?? row.grupo_etario}</p>
            <p className="text-2xl font-bold text-emerald-700 mt-1">{Number(row.media_hba1c).toFixed(1)}%</p>
            <p className="text-xs text-slate-400 mt-0.5">
              Meta: {row.meta_sbd}% · {fmtN(row.total_exames)} exames
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
