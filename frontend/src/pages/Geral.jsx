import React from 'react'
import { Activity, Building2, BarChart2, CalendarRange, Users, UserCheck } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext.jsx'

function KPICard({ icon: Icon, label, value, cor, subtitle }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center gap-4 shadow-sm transition-all hover:shadow-md">
      <div className={`p-3 rounded-lg ${cor} shrink-0`}>
        <Icon size={22} className="text-white" />
      </div>
      <div>
        <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">{label}</p>
        <p className="text-2xl font-bold text-slate-800 mt-0.5">
          {value !== undefined ? value : '—'}
        </p>
        {subtitle && (
          <p className="text-xs text-slate-400 mt-1 font-medium">{subtitle}</p>
        )}
      </div>
    </div>
  )
}

export default function Geral() {

  const { usuario, carregando } = useAuth()

  if (carregando) {
    return (
      <div className="h-96 flex items-center justify-center text-slate-500 font-medium">
        Carregando visão geral...
      </div>
    )
  }

  const perfil = usuario?.nome

  const isGestor = perfil === 'Gestor'
  const isEquipe = perfil === 'Equipe'

  const mockGestor = {
    ano_referencia: 2023,
    mediana_atendimentos_usf: 4520,
    total_atendimentos_ano: 245800,
    total_usfs_ativas: 54,
    media_atendimentos_usf: 4551 
  }

  const mockEquipe = {
    ano_referencia: 2023,
    mediana_atendimentos_individuo: 2,
    media_atendimentos_individuo: 2.6,
    total_individuos_atendidos: 45320,
    total_atendimentos_ano: 117832,
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">

      <div>
        <h1 className="text-2xl font-bold text-slate-800">Visão Geral do Sistema</h1>
        <p className="text-slate-500 text-sm mt-1">
          {isGestor
            ? "Resumo executivo e indicadores chave de desempenho da rede de saúde."
            : "Resumo de engajamento e utilização da rede de saúde pelos cidadãos."}
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

        {isGestor && (
          <>
            <KPICard
              icon={BarChart2}
              label="Mediana Atendimentos/USF"
              value={mockGestor.mediana_atendimentos_usf.toLocaleString('pt-BR')}
              cor="bg-purple-600"
              subtitle={`Referência: ${mockGestor.ano_referencia}`}
            />

            <KPICard
              icon={Activity}
              label="Total de Atendimentos"
              value={mockGestor.total_atendimentos_ano.toLocaleString('pt-BR')}
              cor="bg-blue-600"
              subtitle={`Acumulado ${mockGestor.ano_referencia}`}
            />

            <KPICard
              icon={Building2}
              label="USFs Ativas"
              value={mockGestor.total_usfs_ativas}
              cor="bg-emerald-600"
              subtitle="Unidades reportando dados"
            />

            <KPICard
              icon={CalendarRange}
              label="Média Atendimentos/USF"
              value={mockGestor.media_atendimentos_usf.toLocaleString('pt-BR')}
              cor="bg-slate-600"
              subtitle="Para comparação c/ mediana"
            />
          </>
        )}

        {isEquipe && (
          <>
            <KPICard
              icon={UserCheck}
              label="Mediana Atendimentos/Cidadão"
              value={mockEquipe.mediana_atendimentos_individuo}
              cor="bg-purple-600"
              subtitle={`No último ano (${mockEquipe.ano_referencia})`}
            />

            <KPICard
              icon={Users}
              label="Cidadãos Atendidos"
              value={mockEquipe.total_individuos_atendidos.toLocaleString('pt-BR')}
              cor="bg-blue-600"
              subtitle="Pacientes únicos na rede"
            />

            <KPICard
              icon={Activity}
              label="Total de Atendimentos"
              value={mockEquipe.total_atendimentos_ano.toLocaleString('pt-BR')}
              cor="bg-emerald-600"
              subtitle={`Volume total em ${mockEquipe.ano_referencia}`}
            />

            <KPICard
              icon={BarChart2}
              label="Média de Atendimentos"
              value={mockEquipe.media_atendimentos_individuo.toLocaleString('pt-BR', { minimumFractionDigits: 1 })}
              cor="bg-slate-600"
              subtitle="Para comparação c/ a mediana"
            />
          </>
        )}

      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-8 flex flex-col items-center justify-center text-center space-y-4">
        <div className="p-4 bg-slate-50 rounded-full">
          <Activity size={32} className="text-slate-400" />
        </div>

        <div>
          <h3 className="text-lg font-semibold text-slate-800">
            Visualizações Detalhadas
          </h3>

          <p className="text-sm text-slate-500 max-w-md mt-2">
            Selecione um módulo específico no menu lateral para visualizar gráficos e análises detalhadas.
          </p>
        </div>
      </div>

    </div>
  )
}