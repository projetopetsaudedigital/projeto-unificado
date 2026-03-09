import { useQuery } from '@tanstack/react-query'
import { obApi } from '../../api/obesidade.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts'

// Mapeamento dos campos do backend → label curto para o gráfico
const CLASSES_IMC = [
  { key: 'pct_baixo_peso',    label: 'Baixo Peso',    fill: '#60a5fa' },
  { key: 'pct_normal',        label: 'Normal',         fill: '#4ade80' },
  { key: 'pct_sobrepeso',     label: 'Sobrepeso',      fill: '#facc15' },
  { key: 'pct_obesidade_i',   label: 'Ob. I',          fill: '#fb923c' },
  { key: 'pct_obesidade_ii',  label: 'Ob. II',         fill: '#f87171' },
  { key: 'pct_obesidade_iii', label: 'Ob. III',        fill: '#dc2626' },
]

// Labels curtos para o eixo X (evitar texto muito longo)
const LABEL_CURTO = {
  'Hipertensão Arterial': 'Hipert.',
  'Diabetes':             'Diabetes',
  'Doença Cardíaca':      'Cardíaca',
  'Doença Respiratória':  'Respirat.',
  'AVC':                  'AVC',
  'Problema nos Rins':    'Rins',
  'Fumante':              'Fumante',
  'Uso de Álcool':        'Álcool',
}

export default function ObFatoresRisco() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ob-fatores-risco'],
    queryFn: () => obApi.fatoresRisco(),
  })

  if (error) return <p className="text-sm text-red-500 p-4">Erro: {error.message}</p>

  // Cada ponto do gráfico = uma comorbidade; barras = % por classe de IMC
  const chartData = (data?.comorbidades || []).map(item => ({
    name: LABEL_CURTO[item.comorbidade] ?? item.comorbidade,
    fullName: item.comorbidade,
    ...Object.fromEntries(CLASSES_IMC.map(c => [c.label, item[c.key] ?? 0])),
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Fatores de Risco por Classe de IMC</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Prevalência de comorbidades em cada grupo de IMC (% dos pacientes daquela classe)
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        {isLoading ? (
          <div className="h-72 bg-slate-50 rounded-lg animate-pulse" />
        ) : chartData.length === 0 ? (
          <p className="text-sm text-slate-400 py-8 text-center">Sem dados disponíveis.</p>
        ) : (
          <ResponsiveContainer width="100%" height={340}>
            <BarChart data={chartData} margin={{ top: 4, right: 16, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} interval={0} />
              <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
              <Tooltip
                formatter={(v, name) => [`${v}%`, name]}
                labelFormatter={(label, payload) => payload?.[0]?.payload?.fullName ?? label}
              />
              <Legend wrapperStyle={{ paddingTop: '12px' }} />
              {CLASSES_IMC.map(c => (
                <Bar key={c.key} dataKey={c.label} fill={c.fill} radius={[2, 2, 0, 0]} maxBarSize={14} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Tabela resumo */}
      {!isLoading && data?.comorbidades?.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-2.5 font-semibold text-slate-600">Comorbidade</th>
                {CLASSES_IMC.map(c => (
                  <th key={c.key} className="text-right px-3 py-2.5 font-semibold text-slate-600">{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.comorbidades.map((item, i) => (
                <tr key={i} className="hover:bg-slate-50">
                  <td className="px-4 py-2 text-slate-700 font-medium">{item.comorbidade}</td>
                  {CLASSES_IMC.map(c => (
                    <td key={c.key} className="px-3 py-2 text-right text-slate-600">
                      {item[c.key] != null ? `${item[c.key]}%` : '—'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
