import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'
import { Link } from 'react-router-dom'
import 'leaflet/dist/leaflet.css'
import { api } from '../../api/pressaoArterial.js'

const VDC_CENTER = [-14.866, -40.844]
const VDC_ZOOM = 13

// Escala de cor: verde → amarelo → vermelho (prevalência 0–50%)
function corPrevalencia(pct) {
  const t = Math.min(pct / 40, 1)
  const r = Math.round(34 + t * (239 - 34))
  const g = Math.round(197 - t * (197 - 68))
  const b = Math.round(94 - t * 94)
  return `rgb(${r},${g},${b})`
}

function raioCirculo(total) {
  return Math.max(7, Math.min(40, Math.sqrt(total / 50)))
}

function Legenda() {
  const steps = [0, 10, 20, 30, 40]
  return (
    <div className="absolute bottom-8 right-3 z-[1000] bg-white rounded-lg border border-slate-200 shadow p-3 text-xs">
      <p className="font-semibold text-slate-700 mb-2">Prevalência HAS</p>
      {steps.map((v, i) => (
        <div key={v} className="flex items-center gap-2 mb-1">
          <span
            className="inline-block w-4 h-4 rounded-full border border-white"
            style={{ background: corPrevalencia(v) }}
          />
          <span className="text-slate-600">{i === steps.length - 1 ? `≥${v}%` : `${v}–${steps[i + 1]}%`}</span>
        </div>
      ))}
      <div className="border-t border-slate-100 mt-2 pt-2">
        <p className="text-slate-500">Tamanho = total cadastros</p>
      </div>
    </div>
  )
}

function CardCobertura({ cobertura }) {
  if (!cobertura) return null
  const { vdc_identificados, vdc_pct, nao_identificados, nao_id_pct, total_cadastros } = cobertura
  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <p className="text-xs font-medium text-blue-600 uppercase tracking-wide">Total cidadãos</p>
        <p className="text-2xl font-bold text-blue-800 mt-1">{total_cadastros?.toLocaleString('pt-BR')}</p>
        <p className="text-xs text-blue-500 mt-1">cadastros individuais únicos</p>
      </div>
      <div className="bg-green-50 border border-green-200 rounded-xl p-4">
        <p className="text-xs font-medium text-green-600 uppercase tracking-wide">Residentes VDC identificados</p>
        <p className="text-2xl font-bold text-green-800 mt-1">{vdc_identificados?.toLocaleString('pt-BR')}</p>
        <p className="text-xs text-green-500 mt-1">{vdc_pct}% do total · exibidos no mapa</p>
      </div>
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
        <p className="text-xs font-medium text-amber-700 uppercase tracking-wide">Endereço não identificado</p>
        <p className="text-2xl font-bold text-amber-800 mt-1">{nao_identificados?.toLocaleString('pt-BR')}</p>
        <p className="text-xs text-amber-600 mt-1">{nao_id_pct}% · rural, outros municípios</p>
      </div>
    </div>
  )
}

export default function Mapa() {
  const [granularidade, setGranularidade] = useState('bairro')

  const { data, isLoading } = useQuery({
    queryKey: ['mapa', granularidade],
    queryFn: () => granularidade === 'loteamento' ? api.mapaLoteamentos() : api.mapa(),
  })

  const { data: coberturaData } = useQuery({
    queryKey: ['coberturaBairros'],
    queryFn: api.coberturaBairros,
  })

  const dadosMapa = data?.dados ?? []

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">Mapa de Hipertensão</h1>
          <p className="text-slate-500 text-sm mt-1">
            Distribuição geográfica por bairros e loteamentos — Vitória da Conquista, BA
          </p>
        </div>
        
        {/* Toggle Granularidade */}
        <div className="bg-white border border-slate-200 rounded-lg p-1 inline-flex shrink-0">
          <button
            onClick={() => setGranularidade('bairro')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              granularidade === 'bairro' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Por Bairro (Agrupado)
          </button>
          <button
            onClick={() => setGranularidade('loteamento')}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
              granularidade === 'loteamento' ? 'bg-blue-600 text-white shadow-sm' : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Por Loteamento (Detalhado)
          </button>
        </div>
      </div>

      {granularidade === 'loteamento' && (
        <div className="bg-blue-50/50 border border-blue-100 rounded-lg p-4 text-sm text-blue-800 flex items-start gap-3">
          <span className="text-blue-500 text-lg leading-none mt-0.5">ℹ️</span>
          <div>
            <strong>Aviso sobre coleta de dados:</strong> Muitos cadastros no e-SUS possuem apenas o nome do bairro genérico preenchido pelo ACS (ex: "Zabelê"), sem especificar o loteamento. 
            Estes cadastros genéricos aparecerão agrupados no mapa como <em>"Nome do Bairro (não espec. ou todo bairro)"</em>. Recomendamos orientar os ACS para maior precisão no preenchimento futuro.
          </div>
        </div>
      )}

      {/* Cards de cobertura */}
      {!isLoading && <CardCobertura cobertura={coberturaData} />}

      {/* Mapa */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800">Mapa por bairros VDC</h2>
          <span className="text-sm text-slate-500">
            {isLoading ? 'Carregando...' : `${dadosMapa.length} bairros com coordenadas`}
          </span>
        </div>
        {isLoading ? (
          <div className="h-[520px] flex items-center justify-center text-slate-400">Carregando dados...</div>
        ) : dadosMapa.length === 0 ? (
          <div className="h-[520px] flex flex-col items-center justify-center text-slate-400 gap-3">
            <p className="text-base">Nenhum bairro com coordenadas encontrado.</p>
            <Link to="/admin" className="px-4 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700">
              Configurar Geocodificação →
            </Link>
          </div>
        ) : (
          <div className="relative h-[520px]">
            <MapContainer
              center={VDC_CENTER}
              zoom={VDC_ZOOM}
              style={{ height: '100%', width: '100%' }}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />
              {dadosMapa.map(d => (
                <CircleMarker
                  key={d.bairro}
                  center={[d.lat, d.lng]}
                  radius={raioCirculo(d.total_cadastros)}
                  pathOptions={{
                    fillColor: corPrevalencia(d.prevalencia_pct ?? 0),
                    fillOpacity: 0.78,
                    color: '#fff',
                    weight: 1.5,
                  }}
                >
                  <Tooltip>
                    <div className="text-sm min-w-[160px]">
                      <p className="font-semibold text-slate-800 mb-0.5">{d.bairro}</p>
                      {d.geo_tipo === 'loteamento' && (
                        <p className="text-[11px] font-medium text-blue-600 uppercase tracking-wide mb-1.5 border-b border-slate-100 pb-1.5">LOTEAMENTO ESPECÍFICO</p>
                      )}
                      <div className="space-y-0.5 text-slate-600 mt-1">
                        <p>Cadastros: <strong>{(d.total_cadastros ?? 0).toLocaleString('pt-BR')}</strong></p>
                        <p>Hipertensos: <strong className="text-red-600">{(d.hipertensos ?? 0).toLocaleString('pt-BR')}</strong></p>
                        <p>Prevalência HAS: <strong className="text-red-600">{d.prevalencia_pct ?? 0}%</strong></p>
                        {d.n_diabetes > 0 && <p>Diabéticos: {d.n_diabetes.toLocaleString('pt-BR')}</p>}
                        {d.n_idosos > 0 && <p>Idosos (65+): {d.n_idosos.toLocaleString('pt-BR')} ({d.pct_idosos}%)</p>}
                      </div>
                    </div>
                  </Tooltip>
                </CircleMarker>
              ))}
            </MapContainer>
            <Legenda />
          </div>
        )}
      </div>

      {/* Tabela ranking */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-800">Ranking por Bairro (VDC)</h2>
          <span className="text-sm text-slate-500">{dadosMapa.length} bairros</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">#</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-slate-500 uppercase">Bairro</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Cadastros</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Hipertensos</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Prevalência</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Diabéticos</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-slate-500 uppercase">Idosos</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {dadosMapa.slice(0, 50).map((d, i) => (
                <tr key={d.bairro} className="hover:bg-slate-50">
                  <td className="px-4 py-2.5 text-slate-400 text-xs">{i + 1}</td>
                  <td className="px-4 py-2.5 font-medium text-slate-700 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full inline-block flex-shrink-0"
                      style={{ background: corPrevalencia(d.prevalencia_pct ?? 0) }}
                    />
                    {d.bairro}
                  </td>
                  <td className="px-4 py-2.5 text-right text-slate-600">{(d.total_cadastros ?? 0).toLocaleString('pt-BR')}</td>
                  <td className="px-4 py-2.5 text-right text-red-600 font-medium">{(d.hipertensos ?? 0).toLocaleString('pt-BR')}</td>
                  <td className="px-4 py-2.5 text-right">
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                      (d.prevalencia_pct ?? 0) >= 30 ? 'bg-red-100 text-red-700'
                      : (d.prevalencia_pct ?? 0) >= 20 ? 'bg-amber-100 text-amber-700'
                      : 'bg-green-100 text-green-700'
                    }`}>
                      {d.prevalencia_pct ?? 0}%
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{(d.n_diabetes ?? 0).toLocaleString('pt-BR')}</td>
                  <td className="px-4 py-2.5 text-right text-slate-500">{(d.n_idosos ?? 0).toLocaleString('pt-BR')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
