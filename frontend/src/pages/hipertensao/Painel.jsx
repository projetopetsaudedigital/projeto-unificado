import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  BarChart, Bar, ResponsiveContainer,
} from 'recharts'
import { Users, HeartPulse, Percent, MapPin } from 'lucide-react'
import { api } from '../../api/pressaoArterial.js'

const MESES = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

function KPICard({ icon: Icon, label, value, cor }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${cor}`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-slate-800 mt-0.5">
          {value !== undefined ? value.toLocaleString('pt-BR') : '—'}
        </p>
      </div>
    </div>
  )
}

function FiltroAnos({ anoInicio, anoFim, onChange }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <label className="text-slate-600">De</label>
      <input
        type="number" min="2015" max="2030" value={anoInicio || ''}
        onChange={e => onChange('anoInicio', e.target.value ? +e.target.value : null)}
        placeholder="2020"
        className="w-24 border border-slate-200 rounded-md px-2 py-1 text-slate-700"
      />
      <label className="text-slate-600">até</label>
      <input
        type="number" min="2015" max="2030" value={anoFim || ''}
        onChange={e => onChange('anoFim', e.target.value ? +e.target.value : null)}
        placeholder="2024"
        className="w-24 border border-slate-200 rounded-md px-2 py-1 text-slate-700"
      />
    </div>
  )
}

const SERIES_CLASSIFICACAO = [
  { key: 'normal',        label: 'Normal',  cor: '#22c55e' },
  { key: 'elevada',       label: 'Elevada', cor: '#f59e0b' },
  { key: 'has_estagio_1', label: 'HAS I',   cor: '#f97316' },
  { key: 'has_estagio_2', label: 'HAS II',  cor: '#ef4444' },
  { key: 'has_estagio_3', label: 'HAS III', cor: '#7f1d1d' },
]

export default function Painel() {
  const [filtros, setFiltros] = useState({ anoInicio: null, anoFim: null })

  const { data: kpisData, isLoading: kpiLoading } = useQuery({
    queryKey: ['kpis'],
    queryFn: api.kpis,
  })

  const { data: tendenciaData, isLoading: tendenciaLoading } = useQuery({
    queryKey: ['tendencia', filtros],
    queryFn: () => api.tendencia({
      ano_inicio: filtros.anoInicio,
      ano_fim: filtros.anoFim,
    }),
  })

  const kpis = kpisData?.dados ?? {}

  // O backend retorna uma linha por mês com colunas: normal, elevada, has_estagio_1/2/3, media_pas, media_pad
  const dadosTendencia = tendenciaData?.dados ?? []
  const dadosGrafico = dadosTendencia.map(d => ({
    ...d,
    mes_label: `${String(d.mes).padStart(2,'0')}/${d.ano}`,
  }))

  const handleFiltro = (campo, valor) => {
    setFiltros(prev => ({ ...prev, [campo]: valor }))
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Painel do Gestor</h1>
        <p className="text-slate-500 text-sm mt-1">Indicadores gerais de saúde — Pressão Arterial</p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard icon={Users}     label="Total de Cadastros"  value={kpis.total_cadastros}       cor="bg-blue-500" />
        <KPICard icon={HeartPulse}label="Hipertensos"         value={kpis.total_hipertensos}     cor="bg-red-500"  />
        <KPICard icon={Percent}   label="Prevalência Geral"   value={kpis.prevalencia_geral_pct} cor="bg-amber-500"/>
        <KPICard icon={MapPin}    label="Bairros"             value={kpis.total_bairros}         cor="bg-emerald-500"/>
      </div>

      {/* Tendência */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-lg font-semibold text-slate-800">Evolução Mensal de Medições</h2>
            <p className="text-sm text-slate-500">Contagem por classificação de PA</p>
          </div>
          <FiltroAnos
            anoInicio={filtros.anoInicio}
            anoFim={filtros.anoFim}
            onChange={handleFiltro}
          />
        </div>

        {tendenciaLoading ? (
          <div className="h-64 flex items-center justify-center text-slate-400">Carregando...</div>
        ) : dadosGrafico.length === 0 ? (
          <div className="h-64 flex items-center justify-center text-slate-400">Nenhum dado encontrado</div>
        ) : (
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={dadosGrafico} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="mes_label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              {SERIES_CLASSIFICACAO.map(s => (
                <Line
                  key={s.key}
                  type="monotone"
                  dataKey={s.key}
                  name={s.label}
                  stroke={s.cor}
                  strokeWidth={2}
                  dot={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Médias PAS/PAD */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-6">Médias de PAS e PAD por Mês</h2>
        {tendenciaLoading ? (
          <div className="h-64 flex items-center justify-center text-slate-400">Carregando...</div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={dadosGrafico.slice(0, 24)}
              margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="mes_label" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
              <YAxis domain={[60, 160]} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="media_pas" name="PAS média" fill="#3b82f6" radius={[2, 2, 0, 0]} />
              <Bar dataKey="media_pad" name="PAD média" fill="#93c5fd" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}
