import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { api } from '../../api/pressaoArterial.js'

const BADGE_COLORS = {
  baixa:  'bg-green-100 text-green-800',
  media:  'bg-amber-100 text-amber-800',
  alta:   'bg-red-100   text-red-800',
}

function prevalenciaBadge(pct) {
  if (pct == null) return <span className="text-slate-400">—</span>
  const cls = pct < 20 ? BADGE_COLORS.baixa : pct < 30 ? BADGE_COLORS.media : BADGE_COLORS.alta
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>{pct.toFixed(1)}%</span>
}

function barColor(pct) {
  if (pct == null) return '#94a3b8'
  if (pct < 20) return '#22c55e'
  if (pct < 30) return '#f59e0b'
  return '#ef4444'
}

const SORT_FIELDS = [
  { key: 'hipertensos',    label: 'Hipertensos'    },
  { key: 'total_pacientes',label: 'Total pacientes' },
  { key: 'total_medicoes', label: 'Medições'        },
  { key: 'prevalencia_pct',label: 'Prevalência %'  },
]

export default function UBS() {
  const [anoInicio, setAnoInicio] = useState('')
  const [anoFim,    setAnoFim]    = useState('')
  const [sortKey,   setSortKey]   = useState('hipertensos')
  const [search,    setSearch]    = useState('')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['ubs', anoInicio, anoFim],
    queryFn:  () => api.ubs({ ano_inicio: anoInicio, ano_fim: anoFim }),
  })

  const ubsList = data?.dados ?? []

  const filtered = ubsList
    .filter(u =>
      !search ||
      u.no_unidade_saude?.toLowerCase().includes(search.toLowerCase()) ||
      u.bairro_ubs?.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => (b[sortKey] ?? 0) - (a[sortKey] ?? 0))

  const top15 = filtered.slice(0, 15)

  const chartData = top15.map(u => ({
    nome:         (u.no_unidade_saude ?? '').replace(/^(UBS|PSF|ESF|CS)\s*/i, '').slice(0, 28),
    hipertensos:  u.hipertensos,
    prevalencia:  u.prevalencia_pct,
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Unidades Básicas de Saúde</h1>
        <p className="text-sm text-slate-500 mt-1">
          Hipertensos e medições de PA por UBS — localização e prevalência
        </p>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Ano início</label>
          <input
            type="number" min="2015" max="2030"
            value={anoInicio} onChange={e => setAnoInicio(e.target.value)}
            placeholder="Todos"
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Ano fim</label>
          <input
            type="number" min="2015" max="2030"
            value={anoFim} onChange={e => setAnoFim(e.target.value)}
            placeholder="Todos"
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Buscar UBS / Bairro</label>
          <input
            type="text"
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="ex: patagonia"
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-52 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Ordenar por</label>
          <select
            value={sortKey} onChange={e => setSortKey(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {SORT_FIELDS.map(f => (
              <option key={f.key} value={f.key}>{f.label}</option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && (
        <div className="text-center py-16 text-slate-500">Carregando dados das UBS...</div>
      )}
      {isError && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
          Erro ao carregar UBS: {error?.message}
        </div>
      )}

      {!isLoading && !isError && (
        <>
          {/* Gráfico top 15 */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="text-sm font-semibold text-slate-700 mb-4">
              Top 15 UBS — Hipertensos {search ? `(filtro: "${search}")` : '(maior volume)'}
            </h2>
            {chartData.length === 0 ? (
              <p className="text-slate-400 text-sm text-center py-8">Nenhuma UBS encontrada.</p>
            ) : (
              <ResponsiveContainer width="100%" height={360}>
                <BarChart
                  layout="vertical"
                  data={chartData}
                  margin={{ top: 0, right: 60, left: 8, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis
                    type="category" dataKey="nome"
                    width={180} tick={{ fontSize: 11 }}
                  />
                  <Tooltip
                    formatter={(val, name) => [
                      val?.toLocaleString('pt-BR'),
                      name === 'hipertensos' ? 'Hipertensos' : name,
                    ]}
                  />
                  <Bar dataKey="hipertensos" radius={[0, 4, 4, 0]}>
                    {chartData.map((entry, i) => (
                      <Cell key={i} fill={barColor(entry.prevalencia)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
            <div className="flex gap-4 mt-3 text-xs text-slate-500">
              <span><span className="inline-block w-3 h-3 rounded-sm bg-green-500 mr-1" />Prevalência &lt; 20%</span>
              <span><span className="inline-block w-3 h-3 rounded-sm bg-amber-400 mr-1" />20–30%</span>
              <span><span className="inline-block w-3 h-3 rounded-sm bg-red-500 mr-1" />&gt; 30%</span>
            </div>
          </div>

          {/* Tabela completa */}
          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
            <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-slate-700">
                Todas as UBS ({filtered.length})
              </h2>
              <span className="text-xs text-slate-400">
                {data?.total ?? 0} unidades com medições de PA
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wide">
                  <tr>
                    <th className="px-4 py-2 text-left">UBS</th>
                    <th className="px-4 py-2 text-left">Bairro da UBS</th>
                    <th className="px-4 py-2 text-left">CNES</th>
                    <th className="px-4 py-2 text-right">Pacientes</th>
                    <th className="px-4 py-2 text-right">Hipertensos</th>
                    <th className="px-4 py-2 text-right">Prevalência</th>
                    <th className="px-4 py-2 text-right">Medições</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filtered.map((u, i) => (
                    <tr key={u.co_seq_unidade_saude} className="hover:bg-slate-50">
                      <td className="px-4 py-2 font-medium text-slate-800 max-w-xs truncate">
                        <span className="text-slate-400 text-xs mr-1">{i + 1}.</span>
                        {u.no_unidade_saude}
                      </td>
                      <td className="px-4 py-2 text-slate-600">
                        {u.bairro_ubs ?? <span className="text-slate-300">—</span>}
                      </td>
                      <td className="px-4 py-2 text-slate-500 font-mono text-xs">
                        {u.nu_cnes ?? '—'}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-700">
                        {u.total_pacientes?.toLocaleString('pt-BR')}
                      </td>
                      <td className="px-4 py-2 text-right font-semibold text-slate-800">
                        {u.hipertensos?.toLocaleString('pt-BR')}
                      </td>
                      <td className="px-4 py-2 text-right">
                        {prevalenciaBadge(u.prevalencia_pct)}
                      </td>
                      <td className="px-4 py-2 text-right text-slate-500">
                        {u.total_medicoes?.toLocaleString('pt-BR')}
                      </td>
                    </tr>
                  ))}
                  {filtered.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                        Nenhuma UBS encontrada.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
