import { useState } from 'react'
import { BrowserRouter, Routes, Route, NavLink, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  Activity, Map, BarChart2, Shield, ClipboardList, Building2,
  Settings, Stethoscope, ChevronDown, ChevronRight, Droplets,
  TrendingUp, FlaskConical, Brain, Menu, X, LogOut, Home
} from 'lucide-react'
import { AuthProvider, useAuth } from './contexts/AuthContext.jsx'
import Login from './pages/Login.jsx'

import Geral from './pages/Geral.jsx'

import Painel           from './pages/hipertensao/Painel.jsx'
import DmPainel         from './pages/diabetes/DmPainel.jsx'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 5 * 60 * 1000, retry: 1 },
  },
})

const MODULES = [
  {
    key: 'geral',
    label: 'Visão Geral',
    Icon: Home,
    color: 'text-purple-600',
    bgActive: 'bg-purple-50',
    pages: [
      { to: '/', label: 'Início', Icon: BarChart2 }
    ],
  },
  {
    key: 'hipertensao',
    label: 'Hipertensão',
    Icon: Activity,
    color: 'text-blue-600',
    bgActive: 'bg-blue-50',
    pages: [
      { to: '/hipertensao',               label: 'Painel',           Icon: BarChart2    },
    ],
  },
  {
    key: 'diabetes',
    label: 'Diabetes',
    Icon: Droplets,
    color: 'text-emerald-600',
    bgActive: 'bg-emerald-50',
    pages: [
      { to: '/diabetes',            label: 'Painel',             Icon: BarChart2    },
    ],
  },
]

function SidebarModule({ mod, defaultOpen }) {
  const location = useLocation()
  const isModuleActive = mod.pages.some(p =>
    p.to === '/' ? location.pathname === '/' : location.pathname.startsWith(p.to)
  )
  const [open, setOpen] = useState(defaultOpen || isModuleActive)

  return (
    <div>
      <button
        onClick={() => setOpen(o => !o)}
        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-semibold transition-colors ${
          isModuleActive ? `${mod.bgActive} ${mod.color}` : 'text-slate-700 hover:bg-slate-100'
        }`}
      >
        <mod.Icon size={16} className={isModuleActive ? mod.color : 'text-slate-500'} />
        <span className="flex-1 text-left">{mod.label}</span>
        {open
          ? <ChevronDown  size={14} className="text-slate-400" />
          : <ChevronRight size={14} className="text-slate-400" />
        }
      </button>

      {open && (
        <div className="mt-0.5 ml-3 pl-3 border-l border-slate-200 space-y-0.5">
          {mod.pages.map(({ to, label, Icon: PageIcon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/' || to === '/diabetes' || to === '/hipertensao'}
              className={({ isActive }) =>
                `flex items-center gap-2 px-2 py-1.5 rounded-md text-sm transition-colors ${
                  isActive
                    ? `${mod.bgActive} ${mod.color} font-medium`
                    : 'text-slate-600 hover:bg-slate-50'
                }`
              }
            >
              <PageIcon size={13} />
              {label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

function SidebarContent({ onClose }) {
  const { usuario, logout } = useAuth()
  return (
    <div className="bg-white border-r border-slate-200 flex flex-col h-screen w-60 flex-shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-4 border-b border-slate-100">
        <Activity size={20} className="text-blue-600 flex-shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-slate-800 text-sm leading-tight">Plataforma de Saúde</p>
          <p className="text-xs text-slate-400">Atenção Básica — PEC</p>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-slate-600">
            <X size={16} />
          </button>
        )}
      </div>

      {/* Módulos */}
      <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
        {MODULES.map((mod, i) => (
          <SidebarModule key={mod.key} mod={mod} defaultOpen={i === 0} />
        ))}
      </nav>

      {/* Admin + Logout */}
      <div className="p-3 border-t border-slate-100 space-y-1">
        <NavLink
          to="/admin"
          className={({ isActive }) =>
            `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
              isActive
                ? 'bg-slate-100 text-slate-800 font-medium'
                : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
            }`
          }
        >
        </NavLink>

        {/* Usuário + USF (quando equipe) + Logout */}
        <div className="flex items-center gap-2 px-3 py-2 text-xs text-slate-400">
          <div className="flex-1 min-w-0">
            <span className="block truncate" title={usuario?.email}>
              {usuario?.nome || usuario?.email}
            </span>
            {usuario?.co_unidade_saude != null && (
              <span className="block truncate text-slate-400 mt-0.5" title="Unidade de saúde">
                {usuario?.no_unidade_saude ?? `USF ${usuario.co_unidade_saude}`}
              </span>
            )}
          </div>
          <button
            onClick={logout}
            className="p-1 text-slate-400 hover:text-red-500 transition-colors shrink-0"
            title="Sair"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </div>
  )
}

function Layout() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <div className="flex min-h-screen bg-slate-50">
      {/* Sidebar desktop (sticky) */}
      <div className="hidden lg:block sticky top-0 h-screen">
        <SidebarContent />
      </div>

      {/* Overlay + sidebar mobile */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 flex lg:hidden">
          <div className="fixed inset-0 bg-black/30" onClick={() => setMobileOpen(false)} />
          <div className="relative z-10">
            <SidebarContent onClose={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      {/* Conteúdo principal */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header mobile */}
        <header className="lg:hidden bg-white border-b border-slate-200 px-4 py-3 flex items-center gap-3 sticky top-0 z-40">
          <button onClick={() => setMobileOpen(true)} className="text-slate-600">
            <Menu size={20} />
          </button>
          <Activity size={18} className="text-blue-600" />
          <span className="font-semibold text-slate-800 text-sm">Plataforma de Saúde</span>
        </header>

        <main className="flex-1 p-6 max-w-7xl mx-auto w-full">
          <Routes>
            {/* --- Geral --- */}
            <Route path="/" element={<Geral />} />

            {/* --- Hipertensão --- */}
            <Route path="/hipertensao"               element={<Painel />}          />
            
            {/* Diabetes */}
            <Route path="/diabetes"              element={<DmPainel />}     />
          
          </Routes>
        </main>
      </div>
    </div>
  )
}

function AuthGate() {
  const { autenticado, carregando } = useAuth()

  if (carregando) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
      </div>
    )
  }

  return autenticado ? <Layout /> : <Login />
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AuthGate />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
