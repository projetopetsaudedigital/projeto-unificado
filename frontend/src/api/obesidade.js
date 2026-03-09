const BASE = '/api/v1/obesidade'

async function get(path, params = {}) {
  const url = new URL(BASE + path, window.location.origin)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v)
  })
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const obApi = {
  kpis:          (p = {}) => get('/kpis', p),
  tendencia:     (p = {}) => get('/tendencia', p),
  distribuicao:  (p = {}) => get('/distribuicao', p),
  fatoresRisco:  (p = {}) => get('/fatores-risco', p),
  bairros:       (p = {}) => get('/bairros', p),
  modeloInfo: () => get('/modelo/info').then(r => ({
    ...r,
    // Normalize to common Admin.jsx field names
    disponivel:       r.modelo_treinado,
    modelo_disponivel: r.modelo_treinado,
    total_registros:  r.total_registros_treino,
  })),
  modeloStatus:  ()       => get('/modelo/status-treino'),
  modeloTreinar: () => fetch(
    new URL('/api/v1/obesidade/modelo/treinar', window.location.origin),
    { method: 'POST' }
  ).then(r => r.json()),
  predizer: (perfil) => fetch(
    new URL('/api/v1/obesidade/predizer-imc', window.location.origin),
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(perfil),
    }
  ).then(async r => {
    if (!r.ok) {
      const e = await r.json()
      throw new Error(e.detail || 'Erro na predição')
    }
    return r.json()
  }),
}
