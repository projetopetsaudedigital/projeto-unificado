import { useQuery } from '@tanstack/react-query'
import { obApi } from '../../api/obesidade.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell,
} from 'recharts'

const COR_CLASSE = {
  'Baixo Peso':    '#60a5fa',
  'Normal':        '#4ade80',
  'Sobrepeso':     '#facc15',
  'Obesidade I':   '#fb923c',
  'Obesidade II':  '#f87171',
  'Obesidade III': '#dc2626',
}

const ORDEM_CLASSES = ['Baixo Peso', 'Normal', 'Sobrepeso', 'Obesidade I', 'Obesidade II', 'Obesidade III']

function SectionTitle({ children }) {
  return <h2 className="text-sm font-semibold text-slate-700 mb-3">{children}</h2>
}

// ── Distribuição total (horizontal) ──────────────────────────────────────────

function GraficoDistribuicaoTotal({ data }) {
  if (!data?.length) return <p className="text-sm text-slate-400 py-6 text-center">Sem dados.</p>
  const sorted = ORDEM_CLASSES.map(cls => data.find(d => d.classificacao === cls)).filter(Boolean)
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={sorted} layout="vertical" margin={{ top: 4, right: 50, left: 80, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
        <XAxis type="number" tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
        <YAxis type="category" dataKey="classificacao" tick={{ fontSize: 11 }} width={80} />
        <Tooltip formatter={(v) => [`${v}%`, 'Percentual']} />
        <Bar dataKey="percentual" radius={[0, 4, 4, 0]} label={{ position: 'right', fontSize: 11, formatter: v => `${v}%` }}>
          {sorted.map(entry => (
            <Cell key={entry.classificacao} fill={COR_CLASSE[entry.classificacao] || '#94a3b8'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── IMC médio por sexo ────────────────────────────────────────────────────────

function GraficoPorSexo({ data }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="sexo" tick={{ fontSize: 12 }} />
        <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
        <Tooltip formatter={(v, name) => [Number(v).toFixed(1), name]} />
        <Bar dataKey="imc_medio" name="IMC médio" fill="#f97316" radius={[4, 4, 0, 0]} maxBarSize={60} />
        <Bar dataKey="pct_obesidade" name="% Obesidade" fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={60} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── IMC médio por faixa etária ────────────────────────────────────────────────

function GraficoPorFaixaEtaria({ data }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 50 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis dataKey="faixa_etaria" tick={{ fontSize: 10 }} angle={-35} textAnchor="end" interval={0} />
        <YAxis tick={{ fontSize: 11 }} domain={[0, 'auto']} />
        <Tooltip formatter={(v, name) => [Number(v).toFixed(1), name]} />
        <Bar dataKey="imc_medio" name="IMC médio" fill="#f97316" radius={[4, 4, 0, 0]} maxBarSize={30} />
        <Bar dataKey="pct_obesidade" name="% Obesidade" fill="#ef4444" radius={[4, 4, 0, 0]} maxBarSize={30} />
      </BarChart>
    </ResponsiveContainer>
  )
}

// ── Componente principal ───────────────────────────────────────────────────────

export default function ObDistribuicao() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['ob-distribuicao'],
    queryFn: () => obApi.distribuicao(),
  })

  if (error) return <p className="text-sm text-red-500 p-4">Erro: {error.message}</p>

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Distribuição de IMC</h1>
        <p className="text-sm text-slate-500 mt-0.5">Percentual de adultos em cada classificação da OMS</p>
      </div>

      {isLoading ? (
        <div className="space-y-4 animate-pulse">
          {[...Array(3)].map((_, i) => <div key={i} className="h-56 bg-slate-100 rounded-xl" />)}
        </div>
      ) : (
        <>
          {/* Total */}
          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <SectionTitle>Distribuição geral por classe de IMC</SectionTitle>
            <GraficoDistribuicaoTotal data={data?.por_classificacao} />
            {data?.por_classificacao && (
              <div className="mt-3 grid grid-cols-3 gap-2">
                {ORDEM_CLASSES.map(cls => {
                  const item = data.por_classificacao.find(d => d.classificacao === cls)
                  return item ? (
                    <div key={cls} className="flex items-center gap-2 text-xs text-slate-600">
                      <span className="w-3 h-3 rounded-sm flex-shrink-0" style={{ background: COR_CLASSE[cls] }} />
                      <span>{cls}: <strong>{item.percentual}%</strong> ({Number(item.total).toLocaleString('pt-BR')})</span>
                    </div>
                  ) : null
                })}
              </div>
            )}
          </div>

          {/* Por sexo */}
          {data?.por_sexo?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <SectionTitle>IMC médio e % obesidade por sexo</SectionTitle>
              <GraficoPorSexo data={data.por_sexo} />
            </div>
          )}

          {/* Por faixa etária */}
          {data?.por_faixa_etaria?.length > 0 && (
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <SectionTitle>IMC médio e % obesidade por faixa etária</SectionTitle>
              <GraficoPorFaixaEtaria data={data.por_faixa_etaria} />
            </div>
          )}
        </>
      )}
    </div>
  )
}
