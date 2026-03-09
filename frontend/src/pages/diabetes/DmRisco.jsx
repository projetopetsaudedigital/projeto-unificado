import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { dmApi } from '../../api/diabetes.js'
import { Activity, Brain, RefreshCw, AlertTriangle } from 'lucide-react'

// ── Gauge SVG ─────────────────────────────────────────────────────────────────

function ControlGauge({ pct }) {
  const r = 70, cx = 90, cy = 90
  const cor =
    pct >= 65 ? '#10b981'
    : pct >= 40 ? '#f59e0b'
    : '#ef4444'

  function polarToCartesian(cx, cy, r, angleDeg) {
    const rad = ((angleDeg - 90) * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) }
  }

  const describeArc = (startAngle, endAngle) => {
    const s = polarToCartesian(cx, cy, r, startAngle)
    const e = polarToCartesian(cx, cy, r, endAngle)
    const largeArc = endAngle - startAngle > 180 ? 1 : 0
    return `M ${s.x} ${s.y} A ${r} ${r} 0 ${largeArc} 1 ${e.x} ${e.y}`
  }

  const fillAngle = 180 + (pct / 100) * 180

  return (
    <svg viewBox="0 0 180 100" className="w-full max-w-xs mx-auto">
      <path d={describeArc(180, 360)} fill="none" stroke="#e2e8f0" strokeWidth="14" strokeLinecap="round" />
      <path d={describeArc(180, fillAngle)} fill="none" stroke={cor} strokeWidth="14" strokeLinecap="round" />
      <text x={cx} y={cy - 4} textAnchor="middle" fontSize="26" fontWeight="bold" fill={cor}>{pct}%</text>
      <text x="12" y="98" fontSize="10" fill="#94a3b8">0%</text>
      <text x="144" y="98" fontSize="10" fill="#94a3b8">100%</text>
    </svg>
  )
}

// ── Badge de nível ────────────────────────────────────────────────────────────

function NivelBadge({ nivel, cor }) {
  const classes = {
    green: 'bg-emerald-100 text-emerald-800',
    amber: 'bg-amber-100 text-amber-800',
    red:   'bg-red-100 text-red-800',
  }
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-semibold ${classes[cor] ?? 'bg-slate-100 text-slate-700'}`}>
      {nivel}
    </span>
  )
}

// ── Checkbox ──────────────────────────────────────────────────────────────────

function Checkbox({ label, checked, onChange }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer select-none group">
      <input
        type="checkbox" checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="w-4 h-4 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500"
      />
      <span className="text-sm text-slate-700 group-hover:text-slate-900">{label}</span>
    </label>
  )
}

// ── Constantes ────────────────────────────────────────────────────────────────

const CONDICOES = [
  { key: 'st_hipertensao',        label: 'Hipertensão'             },
  { key: 'st_doenca_cardiaca',    label: 'Doença cardíaca'         },
  { key: 'st_insuf_cardiaca',     label: 'Insuf. cardíaca'         },
  { key: 'st_infarto',            label: 'Infarto'                 },
  { key: 'st_problema_rins',      label: 'Problema nos rins'       },
  { key: 'st_avc',                label: 'AVC / Derrame'           },
  { key: 'st_fumante',            label: 'Fumante'                 },
  { key: 'st_alcool',             label: 'Uso de álcool'           },
  { key: 'st_doenca_respiratoria',label: 'Doença respiratória'     },
  { key: 'st_cancer',             label: 'Câncer'                  },
]

const PERFIL_VAZIO = {
  idade: 55, co_dim_sexo: 3, hba1c: 7.5,
  st_hipertensao: 0, st_doenca_cardiaca: 0, st_insuf_cardiaca: 0,
  st_infarto: 0, st_problema_rins: 0, st_avc: 0,
  st_fumante: 0, st_alcool: 0, st_doenca_respiratoria: 0, st_cancer: 0,
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function DmRisco() {
  const [perfil, setPerfil] = useState(PERFIL_VAZIO)
  const [resultado, setResultado] = useState(null)

  const { data: modeloInfo, isLoading: loadingInfo, refetch: refetchInfo } = useQuery({
    queryKey: ['dm-modelo-info'],
    queryFn: dmApi.modeloInfo,
    refetchInterval: resultado === null ? false : 10000,
  })

  const { mutate: treinar, isPending: treinando } = useMutation({
    mutationFn: dmApi.modeloTreinar,
    onSuccess: () => setTimeout(() => refetchInfo(), 3000),
  })

  const { mutate: predizer, isPending: predizendo } = useMutation({
    mutationFn: () => dmApi.predizer(perfil),
    onSuccess: data => setResultado(data),
  })

  function setCondicao(key, value) {
    setPerfil(p => ({ ...p, [key]: value ? 1 : 0 }))
  }

  const modeloDisponivel = modeloInfo?.disponivel === true

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Predição de Controle Glicêmico</h1>
        <p className="text-sm text-slate-500 mt-1">
          Modelo preditivo de controle glicêmico em diabéticos — RandomForest com validação temporal
        </p>
      </div>

      {/* Status do modelo */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <Brain size={18} className={modeloDisponivel ? 'text-emerald-600' : 'text-slate-400'} />
            <div>
              <p className="text-sm font-medium text-slate-800">
                Modelo: {loadingInfo ? '...' : modeloDisponivel ? 'Disponível' : 'Não treinado'}
              </p>
              {modeloDisponivel && (
                <p className="text-xs text-slate-500">
                  Treinado em {new Date(modeloInfo.treinado_em).toLocaleString('pt-BR')} ·{' '}
                  {modeloInfo.total_registros?.toLocaleString('pt-BR')} exames ·{' '}
                  AUC {modeloInfo.metricas?.roc_auc?.media?.toFixed(3)}
                </p>
              )}
            </div>
          </div>
          <button
            onClick={() => treinar()}
            disabled={treinando}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border border-emerald-300 text-emerald-700 hover:bg-emerald-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <RefreshCw size={13} className={treinando ? 'animate-spin' : ''} />
            {treinando ? 'Iniciando...' : modeloDisponivel ? 'Re-treinar' : 'Treinar modelo'}
          </button>
        </div>
        {treinando && (
          <p className="text-xs text-amber-700 bg-amber-50 rounded-lg px-3 py-2 mt-3">
            Treinamento iniciado em background. Demora ~2–5 minutos. A página atualizará automaticamente.
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Formulário */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-5">
          <h2 className="font-semibold text-slate-800">Perfil do paciente diabético</h2>

          {/* Idade */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Idade: <span className="text-emerald-600 font-semibold">{perfil.idade} anos</span>
            </label>
            <input
              type="range" min={18} max={110} step={1}
              value={perfil.idade}
              onChange={e => setPerfil(p => ({ ...p, idade: +e.target.value }))}
              className="w-full accent-emerald-600"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>18</span><span>110</span>
            </div>
          </div>

          {/* HbA1c */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              HbA1c: <span className="text-emerald-600 font-semibold">{perfil.hba1c.toFixed(1)}%</span>
            </label>
            <input
              type="range" min={3} max={20} step={0.1}
              value={perfil.hba1c}
              onChange={e => setPerfil(p => ({ ...p, hba1c: parseFloat(e.target.value) }))}
              className="w-full accent-emerald-600"
            />
            <div className="flex justify-between text-xs text-slate-400 mt-1">
              <span>3%</span>
              <span className="text-emerald-600">Meta: &lt;7–8%</span>
              <span>20%</span>
            </div>
          </div>

          {/* Sexo */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Sexo</label>
            <div className="flex gap-3">
              {[{ label: 'Feminino', val: 3 }, { label: 'Masculino', val: 1 }].map(({ label, val }) => (
                <label key={val} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="radio" name="sexo-dm"
                    checked={perfil.co_dim_sexo === val}
                    onChange={() => setPerfil(p => ({ ...p, co_dim_sexo: val }))}
                    className="accent-emerald-600"
                  />
                  <span className="text-sm text-slate-700">{label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Condições */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">Comorbidades</label>
            <div className="grid grid-cols-2 gap-2">
              {CONDICOES.map(({ key, label }) => (
                <Checkbox
                  key={key} label={label}
                  checked={perfil[key] === 1}
                  onChange={v => setCondicao(key, v)}
                />
              ))}
            </div>
          </div>

          <button
            onClick={() => predizer()}
            disabled={!modeloDisponivel || predizendo}
            className="w-full py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {predizendo ? 'Calculando...' : 'Calcular probabilidade de controle'}
          </button>
        </div>

        {/* Resultado */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-5">
          <h2 className="font-semibold text-slate-800">Resultado</h2>

          {!resultado && (
            <div className="flex flex-col items-center justify-center py-12 text-slate-400 space-y-2">
              <Activity size={40} strokeWidth={1} />
              <p className="text-sm">Preencha o perfil e clique em "Calcular"</p>
            </div>
          )}

          {resultado && (
            <div className="space-y-5">
              <ControlGauge pct={resultado.probabilidade_pct} />

              <div className="flex justify-center">
                <NivelBadge nivel={resultado.nivel_controle} cor={resultado.cor_controle} />
              </div>

              <div>
                <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide mb-2">
                  Principais fatores
                </p>
                <div className="space-y-2">
                  {resultado.fatores.map(f => (
                    <div key={f.feature} className="flex items-center gap-2">
                      <div className="flex-1">
                        <div className="flex justify-between text-xs mb-0.5">
                          <span className={`font-medium ${f.valor ? 'text-slate-800' : 'text-slate-400'}`}>
                            {f.label}{f.valor ? '' : ' (ausente)'}
                          </span>
                          <span className="text-slate-500">{(f.importancia * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${f.valor ? 'bg-emerald-500' : 'bg-slate-300'}`}
                            style={{ width: `${f.importancia * 100 * 5}%`, maxWidth: '100%' }}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex items-start gap-2 bg-amber-50 border border-amber-200 rounded-lg p-3">
                <AlertTriangle size={14} className="text-amber-600 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-amber-800">{resultado.aviso}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Métricas */}
      {modeloDisponivel && modeloInfo.metricas && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h2 className="font-semibold text-slate-800 mb-4">
            Métricas de validação ({modeloInfo.n_splits_cv ?? 5}-fold TimeSeriesSplit)
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            {Object.entries(modeloInfo.metricas).map(([nome, vals]) => (
              <div key={nome} className="text-center bg-slate-50 rounded-lg p-3">
                <p className="text-lg font-bold text-emerald-700">{(vals.media * 100).toFixed(1)}%</p>
                <p className="text-xs text-slate-500 mt-0.5 capitalize">{nome.replace('_', ' ')}</p>
                <p className="text-xs text-slate-400">±{(vals.std * 100).toFixed(1)}%</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-3">
            Treina em dados mais antigos e valida nos mais recentes —
            sem vazamento temporal. Prevalência de controle na base: {modeloInfo.prevalencia_treino}%.
          </p>
        </div>
      )}
    </div>
  )
}
