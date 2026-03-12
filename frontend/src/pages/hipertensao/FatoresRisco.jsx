import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import { api } from '../../api/pressaoArterial.js'

const CORES = ['#ef4444', '#3b82f6', '#f59e0b', '#22c55e', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16', '#f97316', '#a855f7', '#0ea5e9']

const CORES_PIE = ['#22c55e','#f59e0b','#f97316','#ef4444','#7f1d1d','#1e3a5f','#4b0082']

export default function FatoresRisco() {
  const [multiplos, setMultiplos] = useState(false)
  const [bairro, setBairro] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['fatores-risco', multiplos, bairro],
    queryFn: () => api.fatoresRisco({ multiplos, bairro: bairro || null }),
  })

  const { data: bairrosData } = useQuery({
    queryKey: ['bairros'],
    queryFn: api.bairros,
  })

  const dados = data?.dados ?? []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Fatores de Risco</h1>
        <p className="text-slate-500 text-sm mt-1">Comorbidades e comportamentos em hipertensos vs não-hipertensos</p>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wide">Visualização</p>
            <div className="flex gap-2">
              <button
                onClick={() => setMultiplos(false)}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  !multiplos ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                Comparativo
              </button>
              <button
                onClick={() => setMultiplos(true)}
                className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                  multiplos ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                Múltiplos Fatores
              </button>
            </div>
          </div>

          <div>
            <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Bairro</p>
            <select
              value={bairro}
              onChange={e => setBairro(e.target.value)}
              className="border border-slate-200 rounded-md px-3 py-2 text-sm text-slate-700"
            >
              <option value="">Todos os bairros</option>
              {(bairrosData?.bairros ?? []).map(b => (
                <option key={b} value={b}>{b}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-6 h-80 flex items-center justify-center text-slate-400">
          Carregando...
        </div>
      ) : multiplos ? (
        <MultiplosFatores dados={dados} />
      ) : (
        <ComparativoComorbidades dados={dados} />
      )}
    </div>
  )
}

function ComparativoComorbidades({ dados }) {
  const top = [...dados].sort((a, b) => (b.pct_hipertensos ?? 0) - (a.pct_hipertensos ?? 0)).slice(0, 14)

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h2 className="text-lg font-semibold text-slate-800 mb-6">
        Prevalência de Comorbidades: Hipertensos vs Não-Hipertensos (%)
      </h2>
      {top.length === 0 ? (
        <div className="h-80 flex items-center justify-center text-slate-400">Nenhum dado</div>
      ) : (
        <ResponsiveContainer width="100%" height={420}>
          <BarChart
            data={top}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 160, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
            <XAxis type="number" tickFormatter={v => `${v}%`} tick={{ fontSize: 11 }} />
            <YAxis type="category" dataKey="fator" tick={{ fontSize: 12 }} width={155} />
            <Tooltip formatter={v => `${v}%`} />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Bar dataKey="pct_hipertensos"     name="Hipertensos (%)"     fill="#ef4444" radius={[0, 2, 2, 0]} />
            <Bar dataKey="pct_nao_hipertensos" name="Não-Hipertensos (%)" fill="#93c5fd" radius={[0, 2, 2, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}

function MultiplosFatores({ dados }) {
  const total = dados.reduce((s, d) => s + (d.total_hipertensos ?? 0), 0)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <h2 className="text-lg font-semibold text-slate-800 mb-6">
          Distribuição de Fatores Simultâneos em Hipertensos
        </h2>
        <ResponsiveContainer width="100%" height={300}>
          <PieChart>
            <Pie
              data={dados}
              dataKey="total_hipertensos"
              nameKey="n_fatores"
              cx="50%" cy="50%"
              outerRadius={110}
              label={({ n_fatores, pct_do_total }) => `${n_fatores} fator${n_fatores !== 1 ? 'es' : ''}: ${pct_do_total}%`}
            >
              {dados.map((_, i) => (
                <Cell key={i} fill={CORES_PIE[i % CORES_PIE.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(v, n) => [v.toLocaleString('pt-BR'), `${n} fator(es)`]} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100">
          <h2 className="text-base font-semibold text-slate-800">Detalhes por Quantidade de Fatores</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Nº Fatores</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Hipertensos</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">% do Total</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {dados.map((row, i) => (
              <tr key={i} className="hover:bg-slate-50">
                <td className="px-4 py-2.5">
                  <span className="inline-flex items-center gap-1.5">
                    <span
                      className="w-3 h-3 rounded-full inline-block"
                      style={{ background: CORES_PIE[i % CORES_PIE.length] }}
                    />
                    {row.n_fatores === 0 ? 'Nenhum' : `${row.n_fatores} fator${row.n_fatores !== 1 ? 'es' : ''}`}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right text-slate-600">
                  {(row.total_hipertensos ?? 0).toLocaleString('pt-BR')}
                </td>
                <td className="px-4 py-2.5 text-right">
                  <span className="text-slate-700 font-medium">{row.pct_do_total}%</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
