import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import { kml } from '@tmcw/togeojson'
import 'leaflet/dist/leaflet.css'
import { api } from '../../api/pressaoArterial'
import { useAuth } from '../../contexts/AuthContext.jsx'
import { Activity, Users, CheckCircle, XCircle, MapPin } from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
} from 'recharts'

const VDC_CENTER = [-14.866, -40.844]
const VDC_ZOOM = 11

function statusBadge(status) {
  const isControlado = status === 'Controlado'
  return (
    <span className={`px-2.5 py-1 rounded-full text-xs font-semibold border flex items-center inline-flex gap-1.5 w-max ${isControlado ? 'bg-green-100 text-green-800 border-green-200' : 'bg-red-100 text-red-800 border-red-200'
      }`}>
      <span className={`w-1.5 h-1.5 rounded-full ${isControlado ? 'bg-green-500' : 'bg-red-500'}`}></span>
      {status || 'Indefinido'}
    </span>
  )
}

function definirFaixaEtaria(idade) {
  if (!idade && idade !== 0) return '—'
  if (idade < 18) return 'Criança/Adol.'
  if (idade <= 59) return 'Adulto'
  return 'Idoso'
}

function KpiCard({ label, value, sub, icon: Icon, color = 'blue' }) {
  const colors = {
    emerald: 'text-emerald-600 bg-emerald-50',
    blue:    'text-blue-600 bg-blue-50',
    amber:   'text-amber-600 bg-amber-50',
    red:     'text-red-600 bg-red-50',
  }
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-start gap-3">
      <div className={`p-2 rounded-lg ${colors[color]}`}>
        <Icon size={18} />
      </div>
      <div>
        <p className="text-xs text-slate-500">{label}</p>
        <p className="text-xl font-bold text-slate-800">{value ?? '—'}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
    </div>
  )
}

// --- Helpers do Mapa ---
function descobrirNome(properties, fallbackId) {
  if (!properties) return `Área ${fallbackId}`;

  try {
    if (properties.name && typeof properties.name === 'string' && properties.name !== 'Polígono' && properties.name !== 'Point') {
      return properties.name;
    }
    if (properties.Name && typeof properties.Name === 'string') {
      return properties.Name;
    }

    const chaves = Object.keys(properties);
    for (let key of chaves) {
      const keyLower = key.toLowerCase();
      if (keyLower.includes('nome') || keyLower.includes('unidade') || keyLower.includes('usf') || keyLower.includes('ubs')) {
        if (properties[key] && typeof properties[key] === 'string') {
          return properties[key];
        }
      }
    }

    if (properties.description && typeof properties.description === 'string') {
      const textoLimpo = properties.description.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
      if (textoLimpo.length > 0 && textoLimpo.length < 80) {
        return textoLimpo;
      }
    }
  } catch (erro) {
    console.warn("Erro ao ler propriedades da área:", erro);
  }

  return `Área Indefinida #${fallbackId}`;
}

export default function PainelHipertensao() {
  // --- Estados do Painel ---
  const { usuario } = useAuth()
  const isGestor = usuario?.nome?.toLowerCase() === 'gestor' || usuario?.perfil?.toLowerCase() === 'admin'

  // Se for equipe/leitor: por regra, filtra pela USF do usuário (se existir).
  // Se for gestor: pode filtrar por USF no dropdown.
  const [filtroUbsGestor, setFiltroUbsGestor] = useState('')
  const coUnidadeSaudeAtiva = isGestor
    ? (filtroUbsGestor ? Number(filtroUbsGestor) : undefined)
    : (usuario?.co_unidade_saude ? Number(usuario.co_unidade_saude) : undefined)

  const [buscaPaciente, setBuscaPaciente] = useState('')
  const [filtroStatus, setFiltroStatus] = useState('')
  const [filtroFaixa, setFiltroFaixa] = useState('')
  const [filtroArea, setFiltroArea] = useState('')
  const [filtroMicroarea, setFiltroMicroarea] = useState('')
  const [offset, setOffset] = useState(0)
  const limite = 50

  const [geoJsonData, setGeoJsonData] = useState(null)
  const [isMapLoading, setIsMapLoading] = useState(true)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['individuos', buscaPaciente, filtroFaixa, filtroArea, filtroMicroarea, coUnidadeSaudeAtiva, offset],
    queryFn: () => {
      const params = {
        faixa_etaria: filtroFaixa || undefined,
        nu_area: filtroArea || undefined,
        nu_micro_area: filtroMicroarea || undefined,
        co_unidade_saude: coUnidadeSaudeAtiva || undefined,
        limite,
        offset,
      }

      const termo = buscaPaciente.trim()
      if (termo) {
        const cod = Number(termo)
        if (Number.isInteger(cod) && !Number.isNaN(cod)) {
          params.co_cidadao = cod
        } else {
          params.no_cidadao = termo
        }
      }

      return api.individuos(params)
    },
    keepPreviousData: true
  })

  const individuosDaAPI = data?.dados || []
  const totalGeral = data?.total || 0

  const individuosFiltrados = useMemo(() => {
    if (!filtroStatus) return individuosDaAPI
    return individuosDaAPI.filter(i => i.status_atual === filtroStatus)
  }, [individuosDaAPI, filtroStatus])

  // Totais de Controlado/Descontrolado vêm da API (todos os registros), não só da página atual
  const totalControlados = data?.total_controlados ?? 0
  const totalDescontrolados = data?.total_descontrolados ?? 0

  // Dropdown de USF/UBS (apenas para gestor)
  const { data: ubsData } = useQuery({
    queryKey: ['pa-ubs-lista'],
    queryFn: () => api.ubs({}),
    enabled: isGestor,
    staleTime: 60_000,
  })
  const listaUbs = ubsData?.dados ?? []

  // Painel do gestor (agregações para gráficos)
  const { data: gestorData, isLoading: gestorLoading } = useQuery({
    queryKey: ['pa-gestor-controle', coUnidadeSaudeAtiva],
    queryFn: () => api.gestorControle({ co_unidade_saude: coUnidadeSaudeAtiva }),
    enabled: isGestor,
    staleTime: 30_000,
  })

  const [areaSelecionada, setAreaSelecionada] = useState('')

  const areasDisponiveis = useMemo(() => {
    const rows = gestorData?.por_area_microarea ?? []
    const set = new Set(rows.map(r => r.nu_area).filter(v => v !== null && v !== undefined && `${v}` !== ''))
    return Array.from(set).sort((a, b) => `${a}`.localeCompare(`${b}`))
  }, [gestorData])

  const dadosPorUSF = useMemo(() => {
    const rows = gestorData?.por_usf ?? []
    return rows.map(r => ({
      usf: (r.no_unidade_saude ?? `USF ${r.co_unidade_saude ?? '—'}`).toString().replace(/^(UBS|PSF|ESF|CS)\s*/i, ''),
      controlados: Number(r.controlados ?? 0),
      descontrolados: Number(r.descontrolados ?? 0),
      total: Number(r.total ?? 0),
    }))
  }, [gestorData])

  const dadosMedianaMedicoesUSF = useMemo(() => {
    const rows = gestorData?.mediana_medicoes_usf ?? []
    return rows.map(r => ({
      usf: (r.no_unidade_saude ?? `USF ${r.co_unidade_saude ?? '—'}`).toString().replace(/^(UBS|PSF|ESF|CS)\s*/i, ''),
      total_medicoes: Number(r.total_medicoes ?? 0),
    }))
  }, [gestorData])

  const medianaTotalMedicoesUltimoAno = useMemo(() => {
    if (!dadosMedianaMedicoesUSF.length) return null
    const valores = dadosMedianaMedicoesUSF
      .map(r => r.total_medicoes)
      .filter(v => Number.isFinite(v))
      .sort((a, b) => a - b)
    if (!valores.length) return null
    const meio = Math.floor(valores.length / 2)
    if (valores.length % 2 === 0) {
      return Math.round((valores[meio - 1] + valores[meio]) / 2)
    }
    return valores[meio]
  }, [dadosMedianaMedicoesUSF])

  const dadosArea = useMemo(() => {
    const rows = gestorData?.por_area_microarea ?? []
    const agg = new Map()
    for (const r of rows) {
      const k = `${r.nu_area ?? '—'}`
      const prev = agg.get(k) || { area: k, controlados: 0, descontrolados: 0 }
      const n = Number(r.total ?? 0)
      if (r.status_atual === 'Controlado') prev.controlados += n
      else if (r.status_atual === 'Descontrolado') prev.descontrolados += n
      agg.set(k, prev)
    }
    return Array.from(agg.values()).sort((a, b) => a.area.localeCompare(b.area))
  }, [gestorData])

  const dadosMicroarea = useMemo(() => {
    const rows = gestorData?.por_area_microarea ?? []
    const area = areaSelecionada || (areasDisponiveis[0] ?? '')
    if (!area) return []
    const agg = new Map()
    for (const r of rows) {
      if (`${r.nu_area ?? ''}` !== `${area}`) continue
      const k = `${r.nu_micro_area ?? '—'}`
      const prev = agg.get(k) || { microarea: k, controlados: 0, descontrolados: 0 }
      const n = Number(r.total ?? 0)
      if (r.status_atual === 'Controlado') prev.controlados += n
      else if (r.status_atual === 'Descontrolado') prev.descontrolados += n
      agg.set(k, prev)
    }
    return Array.from(agg.values()).sort((a, b) => a.microarea.localeCompare(b.microarea))
  }, [gestorData, areaSelecionada, areasDisponiveis])

  const dadosSexo = useMemo(() => {
    const rows = gestorData?.sexo_por_status ?? []
    const base = {
      Controlado: { status: 'Controlado', M: 0, F: 0 },
      Descontrolado: { status: 'Descontrolado', M: 0, F: 0 },
    }
    for (const r of rows) {
      const st = r.status_atual
      const sx = r.sg_sexo
      if (!base[st] || (sx !== 'M' && sx !== 'F')) continue
      base[st][sx] = Number(r.total ?? 0)
    }
    return [base.Controlado, base.Descontrolado]
  }, [gestorData])

  const dadosFaixa = useMemo(() => {
    const rows = gestorData?.faixa_etaria_por_status ?? []
    const mk = (status) => {
      const agg = new Map()
      for (const r of rows) {
        if (r.status_atual !== status) continue
        const k = `${r.faixa_etaria}`
        agg.set(k, Number(r.total ?? 0))
      }
      return Array.from(agg.entries())
        .map(([faixa_etaria, total]) => ({ faixa_etaria, total }))
        .sort((a, b) => a.faixa_etaria.localeCompare(b.faixa_etaria))
    }
    return {
      controlados: mk('Controlado'),
      descontrolados: mk('Descontrolado'),
    }
  }, [gestorData])

  useEffect(() => {
    async function carregarKML() {
      try {
        const res = await fetch('/mapa-unidades.kml')
        if (!res.ok) throw new Error('Arquivo KML não encontrado na pasta public.') 

        const kmlText = await res.text()
        const parser = new DOMParser()
        const kmlDom = parser.parseFromString(kmlText, 'text/xml')
        const convertido = kml(kmlDom)

        const dadosSeguros = JSON.parse(JSON.stringify(convertido))
        setGeoJsonData(dadosSeguros)
      } catch (err) {
        console.error('Erro ao carregar mapa:', err)
      } finally {
        setIsMapLoading(false)
      }
    }

    carregarKML()
  }, [])

  const estiloArea = (feature) => {
    return {
      fillColor: feature?.properties?.fill || '#3b82f6',
      color: feature?.properties?.stroke || feature?.properties?.fill || '#ffffff',
      weight: 1.5,
      fillOpacity: feature?.properties?.['fill-opacity'] || 0.4,
    }
  }

  if (isError) return <div className="p-6 text-red-600 bg-red-50 rounded-lg m-6">Erro ao carregar dados da API.</div>

  const nomeUSF =
    usuario?.no_unidade_saude ??
    (usuario?.co_unidade_saude != null ? `USF ${usuario.co_unidade_saude}` : null) ??
    'USF Não Identificada'
  const isEquipe = usuario?.co_unidade_saude != null

  return (
    <div className="p-6 space-y-6 bg-slate-50 min-h-screen font-sans text-slate-900">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-800">Painel - Pressão Arterial</h1>
          <p className="text-sm text-slate-500 mt-1">Controle pressórico · Critérios DBHA 2025</p>
        </div>
        {isEquipe && (
          <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 border border-blue-100 rounded-lg self-start sm:self-center">
            <MapPin size={18} className="text-blue-600" />
            <span className="text-sm font-semibold text-blue-700">{nomeUSF}</span>
          </div>
        )}
      </div>


      {/* KPIs */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-4 gap-3">
        <KpiCard
          label="Total monitorado"
          value={totalGeral.toLocaleString('pt-BR')}
          icon={Users}
          color="blue"
        />
        <KpiCard
          label="Sob controle"
          value={totalControlados?.toLocaleString?.('pt-BR') ?? totalControlados}
          sub="Meta: PA < 140/90 mmHg"
          icon={CheckCircle}
          color="emerald"
        />
        <KpiCard
          label="Em descontrole"
          value={totalDescontrolados?.toLocaleString?.('pt-BR') ?? totalDescontrolados}
          sub="Risco cardiovascular elevado"
          icon={XCircle}
          color="red"
        />
        {medianaTotalMedicoesUltimoAno != null && (
                  <div className="shrink-0">
                    <KpiCard
                      label="Mediana de medições/USF (últ. ano)"
                      value={medianaTotalMedicoesUltimoAno.toLocaleString('pt-BR')}
                      sub="Total de registros de PA por unidade"
                      icon={Activity}
                      color="blue"
                    />
                  </div>
                )}
      </div>

      {/* Painel do Gestor (gráficos e KPIs adicionais) */}
      {isGestor && (
        <div className="space-y-6">

          <div className="grid gap-6">
            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div>
                  <h2 className="font-semibold text-slate-800">
                    Controle vs descontrole por USF
                  </h2>
                  <p className="text-xs text-slate-400 mt-1">
                    Situação atual dos cidadãos acompanhados por unidade de saúde.
                  </p>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={320}>
                <BarChart data={dadosPorUSF} margin={{ top: 10, right: 16, left: 0, bottom: 40 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="usf" interval={0} angle={-25} textAnchor="middle" height={60} tick={false} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="controlados" name="Controlados" stackId="a" fill="#10b981" />
                  <Bar dataKey="descontrolados" name="Descontrolados" stackId="a" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>


          {/* SEXO + MICROÁREA */}

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-800 mb-4">
                Sexo por status
              </h2>

              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={dadosSexo}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="status" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="M" name="Homens" fill="#60a5fa" />
                  <Bar dataKey="F" name="Mulheres" fill="#f472b6" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <div className="flex items-end justify-between gap-3 mb-3">
                <h2 className="font-semibold text-slate-800">
                  Distribuição por Microárea
                </h2>

                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1">
                    Área
                  </label>

                  <select
                    value={areaSelecionada || (areasDisponiveis[0] ?? '')}
                    onChange={(e) => setAreaSelecionada(e.target.value)}
                    className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-28 outline-none bg-white"
                  >
                    {areasDisponiveis.map(a => (
                      <option key={a} value={a}>{a}</option>
                    ))}
                  </select>
                </div>
              </div>

              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={dadosMicroarea}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="microarea" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="controlados" name="Controlados" stackId="a" fill="#10b981" />
                  <Bar dataKey="descontrolados" name="Descontrolados" stackId="a" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>

          </div>


          {/* FAIXA ETÁRIA LADO A LADO */}

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-800 mb-4">
                Faixa etária (Controlados)
              </h2>

              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={dadosFaixa.controlados}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="faixa_etaria" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="total" name="Controlados" fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-white rounded-xl border border-slate-200 p-5">
              <h2 className="font-semibold text-slate-800 mb-4">
                Faixa etária (Descontrolados)
              </h2>

              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={dadosFaixa.descontrolados}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                  <XAxis dataKey="faixa_etaria" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="total" name="Descontrolados" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>

          </div>


          {/* ÁREA APS */}

          <div className="bg-white rounded-xl border border-slate-200 p-5">
            <h2 className="font-semibold text-slate-800 mb-4">
              Distribuição por Área (APS)
            </h2>

            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={dadosArea}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                <XAxis dataKey="area" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Bar dataKey="controlados" name="Controlados" stackId="a" fill="#10b981" />
                <Bar dataKey="descontrolados" name="Descontrolados" stackId="a" fill="#ef4444" />
              </BarChart>
            </ResponsiveContainer>
          </div>

        </div>
      )}

      {/* Filtros da Tabela */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap gap-4 items-end shadow-sm mt-6">
      {isGestor && (
        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">USF/UBS</label>
          <select
            value={filtroUbsGestor}
            onChange={(e) => { setFiltroUbsGestor(e.target.value); setOffset(0) }}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-60 outline-none bg-white"
          >
            <option value="">Todas as USFs/UBSs</option>
            {listaUbs.map(u => (
              <option key={u.co_seq_unidade_saude} value={u.co_seq_unidade_saude}>
                {u.no_unidade_saude}
              </option>
            ))}
          </select>
        </div>
      )}
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs font-medium text-slate-600 mb-1">Paciente (nome ou código)</label>
          <input
            type="text"
            value={buscaPaciente}
            onChange={e => { setBuscaPaciente(e.target.value); setOffset(0); }}
            placeholder="Digite o nome ou o código do paciente"
            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Faixa Etária</label>
          <select
            value={filtroFaixa}
            onChange={e => { setFiltroFaixa(e.target.value); setOffset(0); }}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-44 outline-none bg-white"
          >
            <option value="">Todas as Faixas</option>
            <option value="18-29">18-29 anos</option>
            <option value="30-39">30-39 anos</option>
            <option value="40-49">40-49 anos</option>
            <option value="50-59">50-59 anos</option>
            <option value="60-64">60-64 anos</option>
            <option value="65+">65+ anos</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Área</label>
          <input
            type="text"
            value={filtroArea}
            onChange={e => { setFiltroArea(e.target.value); setOffset(0); }}
            placeholder="Ex: 2"
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-24 outline-none bg-white"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Microárea</label>
          <input
            type="text"
            value={filtroMicroarea}
            onChange={e => { setFiltroMicroarea(e.target.value); setOffset(0); }}
            placeholder="Ex: 03"
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-24 outline-none bg-white"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-600 mb-1">Status</label>
          <select
            value={filtroStatus}
            onChange={e => setFiltroStatus(e.target.value)}
            className="border border-slate-300 rounded-lg px-3 py-1.5 text-sm w-40 outline-none bg-white"
          >
            <option value="">Todos Status</option>
            <option value="Controlado">Controlado</option>
            <option value="Descontrolado">Descontrolado</option>
          </select>
        </div>
      </div>

      {/* Tabela de Pacientes */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="px-5 py-4 border-b border-slate-100 bg-slate-50/50">
          <h2 className="text-sm font-semibold text-slate-800">Prontuário Consolidado</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="bg-white text-slate-500 text-xs uppercase tracking-wide border-b border-slate-200">
              <tr>
                <th className="px-5 py-3 font-medium">Paciente / Perfil</th>
                <th className="px-5 py-3 font-medium">Território</th>
                <th className="px-5 py-3 font-medium text-center">Mediana Anual</th>
                <th className="px-5 py-3 font-medium">Outras Condições</th>
                <th className="px-5 py-3 font-medium text-right">Status Atual</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading ? (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-400 font-medium">Carregando dados...</td></tr>
              ) : individuosFiltrados.length === 0 ? (
                <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-400 font-medium">Nenhum registro encontrado.</td></tr>
              ) : (
                individuosFiltrados.map(i => {
                  const perfil = i.paciente_perfil || {}
                  const mediana = i.mediana_anual || {}
                  const terr = i.territorio || {}

                  return (
                    <tr key={i.co_cidadao} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-5 py-4">
                        <div className="font-medium text-slate-800">{perfil.nome || i.co_cidadao}</div>
                        <div className="text-xs text-slate-500 mt-0.5">
                          {perfil.idade} anos ({definirFaixaEtaria(perfil.idade)}) • Sexo: {perfil.sexo}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <div className="text-slate-700 font-medium">Área {terr.area || '—'}</div>
                        <div className="text-xs text-slate-500">Microárea {terr.microarea || '—'}</div>
                      </td>
                      <td className="px-5 py-4 text-center">
                        <div className={`inline-block px-3 py-1 rounded-md text-xs font-bold border ${i.status_atual === 'Descontrolado' ? 'bg-amber-50 text-amber-800 border-amber-200' : 'bg-slate-50 text-slate-700 border-slate-200'
                          }`}>
                          {mediana.pas} x {mediana.pad} <span className="text-[10px] font-normal ml-1">mmHg</span>
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        {i.outras_condicoes?.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5">
                            {i.outras_condicoes.map((c, idx) => (
                              <span key={idx} className="text-[11px] px-2 py-0.5 bg-blue-50 text-blue-700 border border-blue-100 rounded-md font-medium">
                                {c}
                              </span>
                            ))}
                          </div>
                        ) : <span className="text-slate-400 text-xs italic">Nenhuma informada</span>}
                      </td>
                      <td className="px-5 py-4 text-right">
                        {statusBadge(i.status_atual)}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Paginação */}
        <div className="px-5 py-4 border-t border-slate-100 bg-slate-50/50 flex items-center justify-between text-sm">
          <span className="text-slate-500 font-medium">
            Mostrando <b>{individuosFiltrados.length}</b> de <b>{totalGeral}</b> registros
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setOffset(Math.max(0, offset - limite))}
              disabled={offset === 0}
              className="px-4 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-600 font-medium disabled:opacity-50 hover:bg-slate-50 transition-colors"
            >
              Anterior
            </button>
            <button
              onClick={() => setOffset(offset + limite)}
              disabled={offset + limite >= totalGeral}
              className="px-4 py-1.5 bg-white border border-slate-200 rounded-lg text-slate-600 font-medium disabled:opacity-50 hover:bg-slate-50 transition-colors"
            >
              Próxima
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
