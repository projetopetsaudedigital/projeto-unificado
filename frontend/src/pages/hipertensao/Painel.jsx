import { useState, useMemo, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet'
import { kml } from '@tmcw/togeojson'
import 'leaflet/dist/leaflet.css'
import { api } from '../../api/pressaoArterial'

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
    queryKey: ['individuos', buscaPaciente, filtroFaixa, filtroArea, filtroMicroarea, offset],
    queryFn: () => {
      const params = {
        faixa_etaria: filtroFaixa || undefined,
        nu_area: filtroArea || undefined,
        nu_micro_area: filtroMicroarea || undefined,
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

  const estatisticas = useMemo(() => {
    if (!individuosFiltrados.length) return { controlados: 0, descontrolados: 0 }
    return individuosFiltrados.reduce((acc, curr) => {
      if (curr.status_atual === 'Controlado') acc.controlados++
      else if (curr.status_atual === 'Descontrolado') acc.descontrolados++
      return acc
    }, { controlados: 0, descontrolados: 0 })
  }, [individuosFiltrados])

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

  return (
    <div className="p-6 space-y-6 bg-slate-50 min-h-screen font-sans text-slate-900">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">Painel - Pressão Arterial</h1>
        <p className="text-sm text-slate-500 mt-1">Controle pressórico · Critérios DBHA 2025</p>
      </div>


      {/* KPIs */}
      <div className="flex flex-row gap-3">
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm flex-1 flex flex-col justify-center">
          <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Total Monitorado</p>
          <p className="text-3xl font-extrabold text-slate-800 mt-2">{totalGeral.toLocaleString('pt-BR')}</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-xl p-5 shadow-sm flex-1 flex flex-col justify-center">
          <p className="text-xs font-bold text-green-700 uppercase tracking-wide">Sob Controle</p>
          <p className="text-3xl font-extrabold text-green-800 mt-2">{estatisticas.controlados}</p>
          <p className="text-xs text-green-600 mt-1">Meta: PA &lt; 140/90 mmHg</p>
        </div>
        <div className="bg-red-50 border border-red-200 rounded-xl p-5 shadow-sm flex-1 flex flex-col justify-center">
          <p className="text-xs font-bold text-red-700 uppercase tracking-wide">Em Descontrole</p>
          <p className="text-3xl font-extrabold text-red-800 mt-2">{estatisticas.descontrolados}</p>
          <p className="text-xs text-red-600 mt-1">Risco cardiovascular elevado</p>
        </div>
      </div>


      {/* Filtros da Tabela */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-wrap gap-4 items-end shadow-sm mt-6">
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
