const BASE = '/api/v1/diabetes'

async function get(path, params = {}) {
  const url = new URL(BASE + path, window.location.origin)
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '') url.searchParams.set(k, v)
  })
  const token = localStorage.getItem('token')
  const res = await fetch(url.toString(), {
    headers: { Authorization: token ? `Bearer ${token}` : undefined },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export const dmApi = {
  kpis:               ()        => get('/kpis'),
  individuos:         (p = {})  => get('/individuos', p),
  tendencia:          (p = {})  => get('/tendencia', p),
  hba1cFaixa:         (p = {})  => get('/hba1c/faixa', p),
  hba1cFaixaEtaria:   (p = {})  => get('/hba1c/faixa-etaria', p),
  hba1cSexo:          (p = {})  => get('/hba1c/sexo', p),
  controleGrupo:      (p = {})  => get('/controle/grupo', p),
  controleTendencia:  (p = {})  => get('/controle/tendencia', p),
  controleBairro:     (p = {})  => get('/controle/bairro', p),
  comorbidades:       ()        => get('/controle/comorbidades'),
  modeloInfo:         ()        => get('/modelo/info'),
  modeloStatusTreino: ()        => get('/modelo/status-treino'),
  modeloTreinar: () => fetch(
    new URL('/api/v1/diabetes/modelo/treinar', window.location.origin),
    { method: 'POST' }
  ).then(r => r.json()),
  predizer: (perfil) => fetch(
    new URL('/api/v1/diabetes/predizer-controle', window.location.origin),
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
