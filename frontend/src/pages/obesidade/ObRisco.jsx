import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { obApi } from '../../api/obesidade.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts'
import { Scale, Brain, AlertTriangle } from 'lucide-react'

const COR_CLASSE = {
  'Baixo Peso':    '#60a5fa',
  'Normal':        '#4ade80',
  'Sobrepeso':     '#facc15',
  'Obesidade I':   '#fb923c',
  'Obesidade II':  '#f87171',
  'Obesidade III': '#dc2626',
}

const ORDEM_CLASSES = ['Baixo Peso', 'Normal', 'Sobrepeso', 'Obesidade I', 'Obesidade II', 'Obesidade III']

const PROB_KEYS = {
  'Baixo Peso':   'baixo_peso',
  'Normal':       'normal',
  'Sobrepeso':    'sobrepeso',
  'Obesidade I':  'obesidade_i',
  'Obesidade II': 'obesidade_ii',
  'Obesidade III':'obesidade_iii',
}

const COMORBIDADES = [
  { key: 'st_hipertensao',       label: 'Hipertensão arterial' },
  { key: 'st_diabete',           label: 'Diabetes mellitus' },
  { key: 'st_fumante',           label: 'Tabagismo' },
  { key: 'st_alcool',            label: 'Consumo de álcool' },
  { key: 'st_doenca_cardiaca',   label: 'Doença cardíaca' },
  { key: 'st_doenca_respiratoria', label: 'Doença respiratória' },
]

function BadgeConfianca({ nivel }) {
  const colors = {
    'Alta':       'bg-green-100 text-green-700',
    'Muito Alta': 'bg-green-200 text-green-800',
    'Media':      'bg-yellow-100 text-yellow-700',
    'Baixa':      'bg-red-100 text-red-700',
  }
  const key = Object.keys(colors).find(k => nivel?.includes(k)) || 'Baixa'
  return <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${colors[key]}`}>{nivel}</span>
}

export default function ObRisco() {
  const { data: modeloInfo } = useQuery({
    queryKey: ['ob-modelo-info'],
    queryFn: () => obApi.modeloInfo(),
    retry: false,
  })

  const [form, setForm] = useState({
    peso_kg: '',
    altura_cm: '',
    idade: '',
    sexo: 'F',
    st_hipertensao: 0,
    st_diabete: 0,
    st_fumante: 0,
    st_alcool: 0,
    st_doenca_cardiaca: 0,
    st_doenca_respiratoria: 0,
  })
  const [resultado, setResultado] = useState(null)
  const [loading, setLoading] = useState(false)
  const [erro, setErro] = useState(null)

  const modeloDisponivel = modeloInfo?.modelo_disponivel === true

  function handleChange(e) {
    const { name, value, type, checked } = e.target
    if (type === 'checkbox') {
      setForm(f => ({ ...f, [name]: checked ? 1 : 0 }))
    } else {
      setForm(f => ({ ...f, [name]: value }))
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErro(null)
    setResultado(null)
    setLoading(true)
    try {
      const perfil = {
        peso_kg: parseFloat(form.peso_kg),
        altura_m: parseFloat(form.altura_cm) / 100,
        idade: parseInt(form.idade),
        sexo: form.sexo,
        st_hipertensao: form.st_hipertensao,
        st_diabete: form.st_diabete,
        st_fumante: form.st_fumante,
        st_alcool: form.st_alcool,
        st_doenca_cardiaca: form.st_doenca_cardiaca,
        st_doenca_respiratoria: form.st_doenca_respiratoria,
      }
      const res = await obApi.predizer(perfil)
      setResultado(res)
    } catch (err) {
      setErro(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Monta dados do gráfico de probabilidades
  const chartData = resultado
    ? ORDEM_CLASSES.map(cls => ({
        name: cls,
        prob: Math.round((resultado.probabilidades[PROB_KEYS[cls]] ?? 0) * 100),
      }))
    : []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-slate-800">Predição Individual de IMC</h1>
        <p className="text-sm text-slate-500 mt-0.5">
          Classifica o estado nutricional com base no perfil antropométrico e comorbidades
        </p>
      </div>

      {/* Aviso se modelo não disponível */}
      {!modeloDisponivel && (
        <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm text-amber-700">
          <AlertTriangle size={16} className="flex-shrink-0" />
          <span>
            Modelo não treinado. Acesse <strong>Administração</strong> e treine o modelo de obesidade antes de usar esta função.
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Formulário */}
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5">
            <Scale size={15} className="text-orange-500" /> Dados antropométricos
          </h2>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-500 mb-1">Peso (kg)</label>
              <input
                type="number" name="peso_kg" value={form.peso_kg} onChange={handleChange}
                min={10} max={350} step={0.1} required
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
                placeholder="Ex: 75.5"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Altura (cm)</label>
              <input
                type="number" name="altura_cm" value={form.altura_cm} onChange={handleChange}
                min={100} max={250} step={1} required
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
                placeholder="Ex: 168"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Idade</label>
              <input
                type="number" name="idade" value={form.idade} onChange={handleChange}
                min={18} max={120} required
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
                placeholder="Ex: 45"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Sexo</label>
              <select
                name="sexo" value={form.sexo} onChange={handleChange}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-300"
              >
                <option value="F">Feminino</option>
                <option value="M">Masculino</option>
              </select>
            </div>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-1.5 mb-2">
              <Brain size={15} className="text-orange-500" /> Comorbidades
            </h2>
            <div className="grid grid-cols-2 gap-2">
              {COMORBIDADES.map(c => (
                <label key={c.key} className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
                  <input
                    type="checkbox"
                    name={c.key}
                    checked={form[c.key] === 1}
                    onChange={handleChange}
                    className="accent-orange-500"
                  />
                  {c.label}
                </label>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={loading || !modeloDisponivel}
            className="w-full bg-orange-500 hover:bg-orange-600 disabled:bg-slate-200 disabled:text-slate-400 text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
          >
            {loading ? 'Calculando...' : 'Calcular Predição'}
          </button>

          {erro && <p className="text-xs text-red-500 mt-1">{erro}</p>}
        </form>

        {/* Resultado */}
        <div className="space-y-4">
          {resultado ? (
            <>
              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="text-sm font-semibold text-slate-700">Resultado</h2>
                  <BadgeConfianca nivel={resultado.nivel_confianca} />
                </div>
                <div className="flex items-center gap-3">
                  <div
                    className="w-4 h-12 rounded-sm flex-shrink-0"
                    style={{ background: COR_CLASSE[resultado.classificacao_predita] || '#94a3b8' }}
                  />
                  <div>
                    <p className="text-2xl font-bold text-slate-800">{resultado.classificacao_predita}</p>
                    <p className="text-sm text-slate-500">
                      IMC calculado: <strong>{Number(resultado.imc_calculado).toFixed(1)} kg/m²</strong>
                      {' '}· confiança: <strong>{Math.round(resultado.confianca * 100)}%</strong>
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-xl border border-slate-200 p-5">
                <h2 className="text-sm font-semibold text-slate-700 mb-3">Probabilidades por classe</h2>
                <ResponsiveContainer width="100%" height={190}>
                  <BarChart data={chartData} layout="vertical" margin={{ top: 0, right: 40, left: 80, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                    <XAxis type="number" tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={80} />
                    <Tooltip formatter={v => [`${v}%`]} />
                    <Bar dataKey="prob" radius={[0, 4, 4, 0]}>
                      {chartData.map(entry => (
                        <Cell key={entry.name} fill={COR_CLASSE[entry.name] || '#94a3b8'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <div className="bg-slate-50 rounded-xl border border-dashed border-slate-200 p-10 flex flex-col items-center justify-center text-center">
              <Scale size={32} className="text-slate-300 mb-2" />
              <p className="text-sm text-slate-400">Preencha o formulário e clique em "Calcular Predição"</p>
            </div>
          )}

          {/* Info do modelo */}
          {modeloInfo?.modelo_disponivel && (
            <div className="bg-slate-50 rounded-xl border border-slate-100 px-4 py-3 text-xs text-slate-400 space-y-0.5">
              <p>Modelo: RandomForest · {modeloInfo.algoritmo || 'RandomForestClassifier'}</p>
              {modeloInfo.acuracia_cv && <p>Acurácia CV: {(modeloInfo.acuracia_cv * 100).toFixed(1)}%</p>}
              {modeloInfo.treinado_em && <p>Treinado em: {new Date(modeloInfo.treinado_em).toLocaleDateString('pt-BR')}</p>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
