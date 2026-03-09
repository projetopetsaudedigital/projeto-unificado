import { CheckCircle, XCircle, AlertCircle } from 'lucide-react'

// ── Card ─────────────────────────────────────────────────────────────────────

export function Card({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 ${className}`}>
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }) {
  return (
    <div className={`px-5 py-4 border-b border-slate-100 ${className}`}>
      {children}
    </div>
  )
}

export function CardBody({ children, className = '' }) {
  return (
    <div className={`px-5 py-4 ${className}`}>
      {children}
    </div>
  )
}

// ── PageHeader ───────────────────────────────────────────────────────────────

export function PageHeader({ title, description, children }) {
  return (
    <div className="flex items-start justify-between gap-4 mb-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-800">{title}</h1>
        {description && (
          <p className="text-sm text-slate-500 mt-1">{description}</p>
        )}
      </div>
      {children && <div className="flex items-center gap-2 flex-shrink-0">{children}</div>}
    </div>
  )
}

// ── MetricCard (KPI) ─────────────────────────────────────────────────────────

export function MetricCard({ label, value, subtitle, icon: Icon, color = 'blue' }) {
  const colorMap = {
    blue:    'bg-blue-50 text-blue-600',
    green:   'bg-green-50 text-green-600',
    amber:   'bg-amber-50 text-amber-600',
    red:     'bg-red-50 text-red-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    purple:  'bg-purple-50 text-purple-600',
    slate:   'bg-slate-50 text-slate-600',
  }

  return (
    <Card>
      <CardBody className="flex items-start gap-3">
        {Icon && (
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${colorMap[color] || colorMap.blue}`}>
            <Icon size={20} />
          </div>
        )}
        <div className="min-w-0">
          <p className="text-xs text-slate-500 font-medium">{label}</p>
          <p className="text-xl font-bold text-slate-800 mt-0.5">{value}</p>
          {subtitle && <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>}
        </div>
      </CardBody>
    </Card>
  )
}

// ── StatusBadge ──────────────────────────────────────────────────────────────

export function StatusBadge({ ok, pending, labels = ['Concluído', 'Pendente', 'Ausente'] }) {
  if (pending) return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">{labels[1]}</span>
  if (ok)      return <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">{labels[0]}</span>
  return              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700">{labels[2]}</span>
}

// ── StatusIcon ───────────────────────────────────────────────────────────────

export function StatusIcon({ ok, pending }) {
  if (pending) return <AlertCircle size={18} className="text-amber-500" />
  if (ok)      return <CheckCircle  size={18} className="text-green-600" />
  return             <XCircle       size={18} className="text-red-500"   />
}

// ── LoadingState ─────────────────────────────────────────────────────────────

export function LoadingState({ message = 'Carregando dados...' }) {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto" />
        <p className="text-sm text-slate-500 mt-3">{message}</p>
      </div>
    </div>
  )
}

// ── ErrorState ───────────────────────────────────────────────────────────────

export function ErrorState({ message = 'Erro ao carregar dados.', onRetry }) {
  return (
    <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 text-sm">
      <p>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-2 text-xs font-medium text-red-800 underline hover:no-underline"
        >
          Tentar novamente
        </button>
      )}
    </div>
  )
}

// ── EmptyState ───────────────────────────────────────────────────────────────

export function EmptyState({ message = 'Nenhum dado encontrado.', icon: Icon }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      {Icon && <Icon size={40} className="text-slate-300 mb-3" />}
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  )
}

// ── CopyButton ───────────────────────────────────────────────────────────────

import { useState } from 'react'
import { Copy, Check } from 'lucide-react'

export function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)
  const copy = () => {
    navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button
      onClick={copy}
      className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors"
      title="Copiar"
    >
      {copied ? <Check size={13} className="text-green-600" /> : <Copy size={13} />}
      {copied ? 'Copiado!' : 'Copiar'}
    </button>
  )
}

// ── CommandBlock ─────────────────────────────────────────────────────────────

export function CommandBlock({ cmd, description }) {
  return (
    <div className="mt-3">
      {description && <p className="text-xs text-slate-500 mb-1">{description}</p>}
      <div className="bg-slate-900 rounded-lg px-4 py-3 flex items-center justify-between gap-3">
        <code className="text-green-400 text-sm font-mono break-all">{cmd}</code>
        <CopyButton text={cmd} />
      </div>
    </div>
  )
}

// ── StepHeader (passos numerados do Admin) ───────────────────────────────────

export function StepHeader({ number, title, description, badge, color = 'bg-blue-600' }) {
  return (
    <div className="px-5 py-4 border-b border-slate-100 flex items-center gap-3">
      <span className={`w-7 h-7 rounded-full ${color} text-white text-xs font-bold flex items-center justify-center flex-shrink-0`}>
        {number}
      </span>
      <div className="flex-1">
        <h2 className="font-semibold text-slate-800">{title}</h2>
        {description && <p className="text-xs text-slate-500">{description}</p>}
      </div>
      {badge}
    </div>
  )
}
