import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { CheckCircle, AlertCircle, Clock, Database } from 'lucide-react'
import { api } from '../../api/pressaoArterial.js'

function StatusBadge({ existe }) {
  return existe ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-green-100 text-green-700">
      <CheckCircle size={12} /> Ativa
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-700">
      <AlertCircle size={12} /> Ausente
    </span>
  )
}

function OutlierCard({ label, valor, cor, Icon }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4">
      <div className={`p-3 rounded-lg ${cor}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wide">{label}</p>
        <p className="text-2xl font-bold text-slate-800 mt-0.5">{(valor ?? 0).toLocaleString('pt-BR')}</p>
      </div>
    </div>
  )
}

export default function Qualidade() {
  const [limite, setLimite] = useState(50)

  const { data: resumoData, isLoading: resumoLoading } = useQuery({
    queryKey: ['qualidade-resumo'],
    queryFn: api.qualidadeResumo,
    retry: false,
  })

  const { data: viewsData, isLoading: viewsLoading } = useQuery({
    queryKey: ['qualidade-views'],
    queryFn: api.qualidadeViews,
    retry: false,
  })

  const { data: pendentesData, isLoading: pendentesLoading } = useQuery({
    queryKey: ['qualidade-pendentes', limite],
    queryFn: () => api.qualidadePendentes({ limite }),
    retry: false,
  })

  const porStatus = resumoData?.por_status ?? {}
  const views = viewsData?.views ?? []
  const pendentes = pendentesData?.registros ?? []

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Qualidade de Dados</h1>
        <p className="text-slate-500 text-sm mt-1">Auditoria de outliers e status das views materializadas</p>
      </div>

      {/* Cards de outliers */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <OutlierCard
          label="Total de Outliers"
          valor={resumoData?.total_outliers}
          cor="bg-slate-500"
          Icon={AlertCircle}
        />
        <OutlierCard
          label="Pendentes de Revisão"
          valor={porStatus.pendente}
          cor="bg-amber-500"
          Icon={Clock}
        />
        <OutlierCard
          label="Confirmados como Erro"
          valor={porStatus.confirmado_erro}
          cor="bg-red-500"
          Icon={AlertCircle}
        />
      </div>

      {/* Status das views */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center gap-2">
          <Database size={16} className="text-slate-500" />
          <h2 className="text-base font-semibold text-slate-800">Views Materializadas</h2>
        </div>
        {viewsLoading ? (
          <div className="p-6 text-slate-400 text-sm">Carregando...</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wide">View</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-slate-500 uppercase tracking-wide">Status</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase tracking-wide">Linhas</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {views.map((v, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">{v.name}</td>
                  <td className="px-4 py-3 text-center"><StatusBadge existe={v.exists} /></td>
                  <td className="px-4 py-3 text-right text-slate-600">
                    {v.row_count != null ? v.row_count.toLocaleString('pt-BR') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Outliers pendentes */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock size={16} className="text-amber-500" />
            <h2 className="text-base font-semibold text-slate-800">Outliers Pendentes de Revisão</h2>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <label className="text-slate-500">Mostrar</label>
            <select
              value={limite}
              onChange={e => setLimite(+e.target.value)}
              className="border border-slate-200 rounded-md px-2 py-1 text-slate-700 text-sm"
            >
              {[25, 50, 100, 200].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>

        {pendentesLoading ? (
          <div className="p-6 text-slate-400 text-sm">Carregando...</div>
        ) : pendentes.length === 0 ? (
          <div className="p-6 text-center text-slate-400 text-sm">
            Nenhum outlier pendente. Execute o pipeline via <code className="bg-slate-100 px-1 rounded">POST /qualidade/executar</code> para detectar outliers.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">ID Medição</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Valor PA</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">PAS</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">PAD</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Tipo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Motivo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Detectado em</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {pendentes.map((row, i) => (
                  <tr key={i} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 text-slate-500 font-mono text-xs">{row.co_seq_medicao ?? '—'}</td>
                    <td className="px-4 py-2.5 text-slate-700 font-mono">{row.nu_pa_original ?? '—'}</td>
                    <td className="px-4 py-2.5 text-right text-red-600 font-medium">{row.pas_valor ?? '—'}</td>
                    <td className="px-4 py-2.5 text-right text-orange-600 font-medium">{row.pad_valor ?? '—'}</td>
                    <td className="px-4 py-2.5">
                      <span className="inline-block px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
                        {row.tp_outlier ?? '—'}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 text-xs max-w-xs truncate">{row.ds_motivo ?? '—'}</td>
                    <td className="px-4 py-2.5 text-slate-400 text-xs">
                      {row.dt_deteccao ? new Date(row.dt_deteccao).toLocaleDateString('pt-BR') : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
