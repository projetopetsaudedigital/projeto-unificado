import { useQuery } from '@tanstack/react-query'
import { obApi } from '../../api/obesidade.js'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import { Scale, Users, TrendingUp, AlertTriangle, Activity } from 'lucide-react'

// ── KPI Card ──────────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, icon: Icon, color = 'orange' }) {
  const colors = {
    orange: 'text-orange-600 bg-orange-50',
    blue:   'text-blue-600 bg-blue-50',
    amber:  'text-amber-600 bg-amber-50',
    red:    'text-red-600 bg-red-50',
    slate:  'text-slate-600 bg-slate-100',
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

const fmtN   = v => v != null ? Number(v).toLocaleString('pt-BR') : '—'
const fmtPct = v => v != null ? `${v}%` : '—'
const fmtImc = v => v != null ? Number(v).toFixed(1) : '—'

// ── Gráfico tendência ─────────────────────────────────────────────────────────

function GraficoTendencia({ data }) {
  if (!data?.length) return <p className="text-sm text-slate-400 py-8 text-center">Sem dados de tendência.</p>
  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="mes_ano" tick={{ fontSize: 11 }} />
        <YAxis yAxisId="imc" domain={[20, 35]} tick={{ fontSize: 11 }} label={{ value: 'IMC', angle: -90, position: 'insideLeft', style: { fontSize: 11 } }} />
        <YAxis yAxisId="qtd" orientation="right" tick={{ fontSize: 11 }} />
        <Tooltip />
        <Legend />
        <Line
          yAxisId="imc"
          type="monotone"
          dataKey="imc_medio"
          name="IMC médio"
          stroke="#f97316"
          strokeWidth={2}
          dot={false}
        />
        <Line
          yAxisId="qtd"
          type="monotone"
          dataKey="total_medicoes"
          name="Medições"
          stroke="#94a3b8"
          strokeWidth={1.5}
          dot={false}
          strokeDasharray="4 2"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

// ── Componente principal ───────────────────────────────────────────────────────

export default function ObPainel() {
  const { data: kpisData, isLoading: loadingKpis, error: errKpis } = useQuery({
    queryKey: ['ob-kpis'],
    queryFn: () => obApi.kpis(),
  })

  const { data: tendData, isLoading: loadingTend } = useQuery({
    queryKey: ['ob-tendencia'],
    queryFn: () => obApi.tendencia(),
  })

  const kpis = kpisData?.kpis

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Obesidade — Painel Geral</h1>
        <p className="text-sm text-slate-500 mt-0.5">Indicadores de IMC e estado nutricional da população adulta cadastrada</p>
      </div>

      {/* KPIs */}
      {errKpis ? (
        <p className="text-sm text-red-500">Erro ao carregar KPIs: {errKpis.message}</p>
      ) : loadingKpis ? (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 animate-pulse">
          {[...Array(5)].map((_, i) => <div key={i} className="h-20 bg-slate-100 rounded-xl" />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
          <KpiCard label="Total de Medições"   value={fmtN(kpis?.total_medicoes)}         icon={Activity}      color="slate"  />
          <KpiCard label="Adultos Únicos"       value={fmtN(kpis?.total_adultos)}           icon={Users}         color="blue"   />
          <KpiCard label="IMC Médio"            value={fmtImc(kpis?.imc_medio)}            icon={Scale}         color="orange" sub="kg/m²" />
          <KpiCard label="Sobrepeso (IMC≥25)"   value={fmtPct(kpis?.prevalencia_sobrepeso_pct)}  icon={TrendingUp}    color="amber"  />
          <KpiCard label="Obesidade (IMC≥30)"   value={fmtPct(kpis?.prevalencia_obesidade_pct)}  icon={AlertTriangle} color="red"    />
        </div>
      )}

      {/* Tendência */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Evolução mensal do IMC</h2>
        {loadingTend ? (
          <div className="h-64 bg-slate-50 rounded-lg animate-pulse" />
        ) : (
          <GraficoTendencia data={tendData?.serie} />
        )}
      </div>

      {/* Nota de rodapé */}
      {kpis?.tendencia_mensal != null && (
        <p className="text-xs text-slate-400">
          Tendência mensal do IMC: {kpis.tendencia_mensal > 0 ? '+' : ''}{Number(kpis.tendencia_mensal).toFixed(3)} por mês
        </p>
      )}
    </div>
  )
}
