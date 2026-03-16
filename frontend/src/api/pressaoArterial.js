const BASE = '/api/v1/pressao-arterial'

async function get(path, params = {}) {
  const url = new URL(BASE + path, window.location.origin)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') {
      url.searchParams.set(k, v)
    }
  })
  const token = localStorage.getItem("token")
  const res = await fetch(url.toString(), {
    headers: {
      Authorization: token ? `Bearer ${token}` : undefined
    }
  })

  if (!res.ok) throw new Error(`HTTP ${res.status}`)

  return res.json()
}

export const api = {
  kpis: ()                          => get('/kpis'),
  tendencia: (p = {})               => get('/tendencia', p),
  prevalencia: (p = {})             => get('/prevalencia', p),
  fatoresRisco: (p = {})            => get('/fatores-risco', p),
  mapa: (p = {})                    => get('/mapa', p),
  mapaLoteamentos: (p = {})         => get('/mapa-loteamentos', p),
  individuos: (p = {}) => get('/individuos', p),
  gestorControle: (p = {})          => get('/gestor/controle', p),
  bairros: ()                       => get('/bairros'),
  coberturaBairros: ()              => get('/cobertura-bairros'),
  ubs: (p = {})                     => get('/ubs', p),
  qualidadeResumo: ()               => get('/qualidade/resumo'),
  qualidadePendentes: (p = {})      => get('/qualidade/pendentes', p),
  qualidadeViews: ()                => get('/qualidade/views'),
  adminStatus: ()                   => get('/admin/status'),
  adminRefresh: (view)              => fetch(
    new URL(`/api/v1/pressao-arterial/admin/refresh/${view}`, window.location.origin),
    { method: 'POST' }
  ).then(r => { if (!r.ok) return r.json().then(e => Promise.reject(new Error(e.detail))); return r.json() }),
  adminProcessamentos: (tipo, limite = 20) => get('/admin/processamentos', { tipo, limite }),
  adminTreinar: (modulo) => fetch(
    new URL(`/api/v1/pressao-arterial/admin/treinar/${modulo}`, window.location.origin),
    { method: 'POST' }
  ).then(r => { if (!r.ok) return r.json().then(e => Promise.reject(new Error(e.detail))); return r.json() }),
  modeloInfo: ()                    => get('/modelo/info'),
  modeloStatusTreino: ()            => get('/modelo/status-treino'),
  adminSincronizarBaseGeo: (threshold) => fetch(
    new URL(`/api/v1/pressao-arterial/admin/sincronizar-base-geografica${threshold ? `?threshold=${threshold}` : ''}`, window.location.origin),
    { method: 'POST' }
  ).then(r => { if (!r.ok) return r.json().then(e => Promise.reject(new Error(e.detail))); return r.json() }),
  adminSincronizarBaseGeoStatus: () => get('/admin/sincronizar-base-geografica/status'),
  adminGeocodificar: (bairros) => fetch(
    new URL(`/api/v1/pressao-arterial/admin/geocodificar`, window.location.origin),
    { 
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bairros })
    }
  ).then(r => { if (!r.ok) return r.json().then(e => Promise.reject(new Error(e.detail))); return r.json() }),
  adminGeocodificarStatus: ()       => get('/admin/geocodificar/status'),
  adminListarOrfaos: ()             => get('/admin/geocodificacao/orfaos'),
  exportarGeocode: () => window.open(new URL(`/api/v1/pressao-arterial/admin/geocodificacao/exportar`, window.location.origin), '_blank')
}

