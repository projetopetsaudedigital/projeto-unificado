import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { dmApi } from '../../api/diabetes.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend, Cell,
} from 'recharts'

const fmtN = v => v != null ? Number(v).toLocaleString('pt-BR') : '—'
const fmtPct = v => v != null ? `${Number(v).toFixed(1)}%` : '—'

const GRUPO_LABELS = {
  adulto:      'Adultos (18–64)',
  idoso_65_79: 'Idosos (65–79)',
  'idoso_80+': 'Idosos (≥80)',
}

// ── Gráfico controlados vs descontrolados por grupo ───────────────────────────

function GraficoGrupos({ data }) {
  if (!data?.length) return <p className="text-sm text-slate-400">Sem dados.</p>

  // Pivota: uma entrada por grupo_etario
  const grupos = [...new Set(data.map(d => d.grupo_etario))]
  const pivotado = grupos.map(grupo => {
    const ctrl = data.find(d => d.grupo_etario === grupo && d.controle_glicemico === 'Controlado')
    const desc = data.find(d => d.grupo_etario === grupo && d.controle_glicemico === 'Descontrolado')
    return {
      grupo,
      label: GRUPO_LABELS[grupo] ?? grupo,
      controlados: ctrl?.total ?? 0,
      descontrolados: desc?.total ?? 0,
      media_ctrl: ctrl?.media_hba1c,
      media_desc: desc?.media_hba1c,
    }
  })

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={pivotado} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="label" tick={{ fontSize: 11 }} />
        <YAxis tick={{ fontSize: 11 }} />
        <Tooltip formatter={v => fmtN(v)} />
        <Legend />
        <Bar dataKey="controlados" name="Controlados" fill="#10b981" radius={[3, 3, 0, 0]} />
        <Bar dataKey="descontrolados" name="Descontrolados" fill="#ef4444" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Comorbidades ──────────────────────────────────────────────────────────────

function GraficoComorbidades({ data }) {
  if (!data?.length) return <p className="text-sm text-slate-400">Sem dados.</p>

  const sorted = [...data].sort((a, b) => (b.pct_descontrolados ?? 0) - (a.pct_descontrolados ?? 0))

  return (
    <div className="space-y-2">
      {sorted.map(row => (
        <div key={row.fator}>
          <div className="flex justify-between text-xs mb-0.5">
            <span className="text-slate-700 font-medium">{row.fator}</span>
            <span className="text-slate-400">
              Ctrl: {fmtPct(row.pct_controlados)} · Desc: {fmtPct(row.pct_descontrolados)}
            </span>
          </div>
          <div className="flex gap-1 h-2">
            <div
              className="bg-emerald-500 rounded-l"
              style={{ width: `${row.pct_controlados ?? 0}%`, maxWidth: '50%' }}
              title={`Controlados: ${fmtPct(row.pct_controlados)}`}
            />
            <div
              className="bg-red-400 rounded-r"
              style={{ width: `${row.pct_descontrolados ?? 0}%`, maxWidth: '50%' }}
              title={`Descontrolados: ${fmtPct(row.pct_descontrolados)}`}
            />
          </div>
        </div>
      ))}
      <div className="flex gap-4 text-xs text-slate-400 pt-1">
        <span><span className="inline-block w-2 h-2 rounded-sm bg-emerald-500 mr-1" />Controlados</span>
        <span><span className="inline-block w-2 h-2 rounded-sm bg-red-400 mr-1" />Descontrolados</span>
      </div>
    </div>
  )
}

// ── Tabela por bairro ─────────────────────────────────────────────────────────

function TabelaBairros({ data, busca }) {
  if (!data?.length) return <p className="text-sm text-slate-400">Sem dados.</p>

  const filtrado = data.filter(d =>
    !busca || d.bairro?.toLowerCase().includes(busca.toLowerCase())
  )

  const corPct = pct => {
    if (pct == null) return 'text-slate-400'
    if (pct >= 50) return 'text-emerald-700 font-semibold'
    if (pct >= 35) return 'text-amber-700'
    return 'text-red-700 font-semibold'
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200">
            <th className="text-left py-2 pr-3 text-xs font-semibold text-slate-500">Bairro</th>
            <th className="text-right py-2 px-2 text-xs font-semibold text-slate-500">Pacientes</th>
            <th className="text-right py-2 px-2 text-xs font-semibold text-slate-500">Exames</th>
            <th className="text-right py-2 px-2 text-xs font-semibold text-slate-500">Controlados</th>
            <th className="text-right py-2 px-2 text-xs font-semibold text-slate-500">HbA1c média</th>
            <th className="text-right py-2 pl-2 text-xs font-semibold text-slate-500">% Ctrl</th>
          </tr>
        </thead>
        <tbody>
          {filtrado.slice(0, 50).map((d, i) => (
            <tr key={d.bairro} className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
              <td className="py-1.5 pr-3 text-slate-700 capitalize">{d.bairro?.toLowerCase()}</td>
              <td className="py-1.5 px-2 text-right text-slate-600">{fmtN(d.total_pacientes)}</td>
              <td className="py-1.5 px-2 text-right text-slate-600">{fmtN(d.total_exames)}</td>
              <td className="py-1.5 px-2 text-right text-slate-600">{fmtN(d.controlados)}</td>
              <td className="py-1.5 px-2 text-right text-slate-600">{d.media_hba1c != null ? `${Number(d.media_hba1c).toFixed(1)}%` : '—'}</td>
              <td className={`py-1.5 pl-2 text-right ${corPct(d.pct_controlados)}`}>{fmtPct(d.pct_controlados)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {filtrado.length > 50 && (
        <p className="text-xs text-slate-400 mt-2">{filtrado.length - 50} bairros omitidos. Use a busca para filtrar.</p>
      )}
    </div>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function DmControle() {
  const [busca, setBusca] = useState('')
  const [aba, setAba] = useState('grupos') // 'grupos' | 'bairros' | 'comorbidades'

  const { data: grupos, isLoading: loadGrupos } = useQuery({
    queryKey: ['dm-controle-grupo'],
    queryFn: () => dmApi.controleGrupo(),
  })

  const { data: bairros, isLoading: loadBairros } = useQuery({
    queryKey: ['dm-controle-bairro'],
    queryFn: () => dmApi.controleBairro(),
    enabled: aba === 'bairros',
  })

  const { data: comorbidades, isLoading: loadComorbidades } = useQuery({
    queryKey: ['dm-comorbidades'],
    queryFn: dmApi.comorbidades,
    enabled: aba === 'comorbidades',
  })

  const abas = [
    { key: 'grupos',      label: 'Grupos etários' },
    { key: 'bairros',     label: 'Por bairro' },
    { key: 'comorbidades', label: 'Comorbidades' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Controle Glicêmico</h1>
        <p className="text-sm text-slate-500 mt-1">
          Metas HbA1c: adultos &lt;7,0% · idosos 65-79 &lt;7,5% · idosos ≥80 &lt;8,0% (SBD 2024)
        </p>
      </div>

      {/* Abas */}
      <div className="flex gap-1 bg-slate-100 p-1 rounded-lg w-fit">
        {abas.map(a => (
          <button
            key={a.key}
            onClick={() => setAba(a.key)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              aba === a.key
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {a.label}
          </button>
        ))}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        {aba === 'grupos' && (
          <>
            <h2 className="font-semibold text-slate-800 mb-4">Controlados vs descontrolados por grupo etário</h2>
            {loadGrupos ? <p className="text-sm text-slate-400">Carregando...</p> : <GraficoGrupos data={grupos} />}

            {/* Tabela com média HbA1c */}
            {!loadGrupos && grupos?.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-slate-700 mb-2">Detalhes por grupo</h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-slate-200">
                        <th className="text-left py-2 pr-3 text-xs font-semibold text-slate-500">Grupo</th>
                        <th className="text-left py-2 px-2 text-xs font-semibold text-slate-500">Status</th>
                        <th className="text-right py-2 px-2 text-xs font-semibold text-slate-500">Total</th>
                        <th className="text-right py-2 px-2 text-xs font-semibold text-slate-500">HbA1c média</th>
                        <th className="text-right py-2 pl-2 text-xs font-semibold text-slate-500">HbA1c min/max</th>
                      </tr>
                    </thead>
                    <tbody>
                      {grupos.map((row, i) => (
                        <tr key={`${row.grupo_etario}-${row.controle_glicemico}`} className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50'}>
                          <td className="py-1.5 pr-3 text-slate-700">{row.grupo_etario}</td>
                          <td className="py-1.5 px-2">
                            <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                              row.controle_glicemico === 'Controlado'
                                ? 'bg-emerald-100 text-emerald-700'
                                : 'bg-red-100 text-red-700'
                            }`}>
                              {row.controle_glicemico}
                            </span>
                          </td>
                          <td className="py-1.5 px-2 text-right text-slate-600">{fmtN(row.total)}</td>
                          <td className="py-1.5 px-2 text-right text-slate-600">{row.media_hba1c != null ? `${Number(row.media_hba1c).toFixed(1)}%` : '—'}</td>
                          <td className="py-1.5 pl-2 text-right text-slate-400 text-xs">
                            {row.min_hba1c} – {row.max_hba1c}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}

        {aba === 'bairros' && (
          <>
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <h2 className="font-semibold text-slate-800">Controle glicêmico por bairro</h2>
              <input
                type="text"
                placeholder="Buscar bairro..."
                value={busca}
                onChange={e => setBusca(e.target.value)}
                className="border border-slate-200 rounded-lg px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-2 focus:ring-emerald-400"
              />
            </div>
            {loadBairros ? (
              <p className="text-sm text-slate-400">Carregando...</p>
            ) : (
              <TabelaBairros data={bairros} busca={busca} />
            )}
          </>
        )}

        {aba === 'comorbidades' && (
          <>
            <h2 className="font-semibold text-slate-800 mb-2">Comorbidades: controlados vs descontrolados</h2>
            <p className="text-xs text-slate-400 mb-4">
              Porcentagem de pacientes com cada condição, comparando o grupo controlado e descontrolado.
            </p>
            {loadComorbidades ? (
              <p className="text-sm text-slate-400">Carregando...</p>
            ) : (
              <GraficoComorbidades data={comorbidades} />
            )}
          </>
        )}
      </div>
    </div>
  )
}
