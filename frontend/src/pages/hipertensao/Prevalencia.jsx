import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Cell,
} from 'recharts'
import { api } from '../../api/pressaoArterial.js'

const AGRUPAMENTOS = [
  { value: 'bairro',       label: 'Por Bairro (VDC)'  },
  { value: 'sexo',         label: 'Por Sexo'          },
  { value: 'faixa_etaria', label: 'Por Faixa Etária'  },
]

function TabButton({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
        active ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
      }`}
    >
      {children}
    </button>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-white border border-slate-200 rounded-lg p-3 shadow text-sm">
      <p className="font-medium text-slate-700 mb-1">{label}</p>
      {payload.map(p => (
        <p key={p.name} style={{ color: p.fill }}>
          {p.name}: {typeof p.value === 'number' && p.name.includes('%')
            ? `${p.value}%`
            : p.value?.toLocaleString('pt-BR')}
        </p>
      ))}
    </div>
  )
}

function NaoIdentificadosCard({ dados }) {
  const [expandido, setExpandido] = useState(false)
  if (!dados || dados.total === 0) return null
  const top = expandido ? dados.top_categorias : dados.top_categorias?.slice(0, 8)

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-xl overflow-hidden">
      <div className="px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-amber-800">
            Endereços não identificados como VDC
          </h2>
          <p className="text-sm text-amber-700 mt-0.5">
            {dados.total?.toLocaleString('pt-BR')} cidadãos com endereço fora de Vitória da Conquista,
            zona rural ou dados incompletos — {dados.prevalencia_pct}% de prevalência de HAS neste grupo
          </p>
        </div>
        <div className="text-right shrink-0">
          <p className="text-2xl font-bold text-amber-800">{dados.total?.toLocaleString('pt-BR')}</p>
          <p className="text-xs text-amber-600">registros</p>
        </div>
      </div>
      <div className="bg-white border-t border-amber-100 px-6 py-4">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-3">Top categorias de endereço</p>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {top?.map(cat => (
            <div key={cat.categoria} className="bg-slate-50 rounded-lg p-3 border border-slate-100">
              <p className="text-xs text-slate-500 truncate" title={cat.categoria}>{cat.categoria}</p>
              <p className="text-sm font-bold text-slate-700">{cat.n?.toLocaleString('pt-BR')}</p>
              <p className="text-xs text-red-500">{cat.hipertensos} HAS</p>
            </div>
          ))}
        </div>
        {dados.top_categorias?.length > 8 && (
          <button
            onClick={() => setExpandido(!expandido)}
            className="mt-3 text-sm text-amber-700 hover:text-amber-800 font-medium"
          >
            {expandido ? '▲ Ver menos' : `▼ Ver mais ${dados.top_categorias.length - 8} categorias`}
          </button>
        )}
      </div>
    </div>
  )
}

export default function Prevalencia() {
  const [agrupamento, setAgrupamento] = useState('bairro')
  const [bairro, setBairro] = useState('')
  const [anoInicio, setAnoInicio] = useState('')
  const [anoFim, setAnoFim] = useState('')

  const { data, isLoading } = useQuery({
    queryKey: ['prevalencia', agrupamento, bairro, anoInicio, anoFim],
    queryFn: () => api.prevalencia({
      agrupamento,
      bairro: bairro || null,
      ano_inicio: anoInicio || null,
      ano_fim: anoFim || null,
    }),
  })

  const { data: bairrosData } = useQuery({
    queryKey: ['bairros'],
    queryFn: api.bairros,
  })

  const dados = data?.dados ?? []
  const naoIdentificados = data?.nao_identificados ?? null
  const top20 = agrupamento === 'bairro'
    ? dados.slice(0, 20)
    : dados

  const dataKey = agrupamento === 'bairro' ? 'bairro' : agrupamento === 'sexo' ? 'sexo' : 'faixa_etaria'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Prevalência de Hipertensão</h1>
        <p className="text-slate-500 text-sm mt-1">
          Distribuição por perfil demográfico — {agrupamento === 'bairro' ? 'apenas bairros de Vitória da Conquista' : 'todos os residentes VDC'}
        </p>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <p className="text-xs text-slate-500 mb-2 font-medium uppercase tracking-wide">Agrupamento</p>
            <div className="flex gap-2">
              {AGRUPAMENTOS.map(a => (
                <TabButton key={a.value} active={agrupamento === a.value} onClick={() => setAgrupamento(a.value)}>
                  {a.label}
                </TabButton>
              ))}
            </div>
          </div>

          {agrupamento !== 'bairro' && (
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
          )}

          <div className="flex items-center gap-2 text-sm">
            <div>
              <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Ano início</p>
              <input
                type="number" value={anoInicio} onChange={e => setAnoInicio(e.target.value)}
                placeholder="2020" className="w-24 border border-slate-200 rounded-md px-2 py-2 text-slate-700"
              />
            </div>
            <div>
              <p className="text-xs text-slate-500 mb-1 font-medium uppercase tracking-wide">Ano fim</p>
              <input
                type="number" value={anoFim} onChange={e => setAnoFim(e.target.value)}
                placeholder="2025" className="w-24 border border-slate-200 rounded-md px-2 py-2 text-slate-700"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Gráfico */}
      <div className="bg-white rounded-xl border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-slate-800">
            {agrupamento === 'bairro' ? 'Top 20 Bairros VDC — Hipertensos' : `Hipertensão ${AGRUPAMENTOS.find(a => a.value === agrupamento)?.label}`}
          </h2>
          <span className="text-sm text-slate-500">{dados.length} {agrupamento === 'bairro' ? 'bairros VDC' : 'grupos'}</span>
        </div>

        {isLoading ? (
          <div className="h-80 flex items-center justify-center text-slate-400">Carregando...</div>
        ) : top20.length === 0 ? (
          <div className="h-80 flex items-center justify-center text-slate-400">Nenhum dado</div>
        ) : (
          <ResponsiveContainer width="100%" height={380}>
            <BarChart
              data={top20}
              layout={agrupamento === 'bairro' ? 'vertical' : 'horizontal'}
              margin={{ top: 5, right: 30, left: agrupamento === 'bairro' ? 160 : 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              {agrupamento === 'bairro' ? (
                <>
                  <XAxis type="number" tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey={dataKey} tick={{ fontSize: 10 }} width={155} />
                </>
              ) : (
                <>
                  <XAxis dataKey={dataKey} tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                </>
              )}
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar dataKey="hipertensos" name="Hipertensos" fill="#ef4444" radius={[2, 2, 0, 0]} />
              <Bar dataKey="total_cadastros" name="Total" fill="#bfdbfe" radius={[2, 2, 0, 0]}
                   hide={agrupamento === 'sexo' || agrupamento === 'faixa_etaria'}
              />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Seção não-identificados (apenas para bairro) */}
      {agrupamento === 'bairro' && !isLoading && (
        <NaoIdentificadosCard dados={naoIdentificados} />
      )}

      {/* Tabela */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800">Dados detalhados</h2>
          <span className="text-sm text-slate-500">{dados.length} registros</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">
                  {dataKey === 'bairro' ? 'Bairro (VDC)' : dataKey === 'sexo' ? 'Sexo' : 'Faixa Etária'}
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wide">Total</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wide">Hipertensos</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wide">Prevalência</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {dados.map((row, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-slate-700 font-medium">{row[dataKey] ?? row.bairro ?? '—'}</td>
                  <td className="px-4 py-2.5 text-right text-slate-600">{(row.total_cadastros ?? row.total ?? 0).toLocaleString('pt-BR')}</td>
                  <td className="px-4 py-2.5 text-right text-red-600 font-medium">{(row.hipertensos ?? 0).toLocaleString('pt-BR')}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      (row.prevalencia_pct ?? 0) >= 30 ? 'bg-red-100 text-red-700'
                      : (row.prevalencia_pct ?? 0) >= 20 ? 'bg-amber-100 text-amber-700'
                      : 'bg-green-100 text-green-700'
                    }`}>
                      {row.prevalencia_pct ?? 0}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
