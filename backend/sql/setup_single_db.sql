-- =====================================================================
-- SETUP MODO BANCO ÚNICO — pet_saude
--
-- Usado quando DB_MODE=single no .env.
-- Cria os schemas necessários e views no schema 'pec' apontando para
-- as tabelas do e-SUS PEC já existentes no schema 'public' de pet_saude.
--
-- EXECUTAR NO BANCO: pet_saude
--
-- Após executar, as views materializadas em dashboard.* referenciam
-- pec.* que resolve para public.* localmente (sem FDW).
-- =====================================================================

-- Schemas
CREATE SCHEMA IF NOT EXISTS dashboard;
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS pec;

-- Views no schema pec apontando para public (tabelas nativas do e-SUS PEC)
-- Permite que todos os arquivos SQL de views materializadas funcionem
-- sem modificação em ambos os modos (FDW e single).

CREATE OR REPLACE VIEW pec.tb_medicao
    AS SELECT * FROM public.tb_medicao;

CREATE OR REPLACE VIEW pec.tb_atend_prof
    AS SELECT * FROM public.tb_atend_prof;

CREATE OR REPLACE VIEW pec.tb_lotacao
    AS SELECT * FROM public.tb_lotacao;

CREATE OR REPLACE VIEW pec.tb_exame_requisitado
    AS SELECT * FROM public.tb_exame_requisitado;

CREATE OR REPLACE VIEW pec.tb_prontuario
    AS SELECT * FROM public.tb_prontuario;

CREATE OR REPLACE VIEW pec.tb_cidadao
    AS SELECT * FROM public.tb_cidadao;

CREATE OR REPLACE VIEW pec.tb_fat_cidadao_pec
    AS SELECT * FROM public.tb_fat_cidadao_pec;

CREATE OR REPLACE VIEW pec.tb_fat_cad_individual
    AS SELECT * FROM public.tb_fat_cad_individual;

CREATE OR REPLACE VIEW pec.tb_dim_sexo
    AS SELECT * FROM public.tb_dim_sexo;

CREATE OR REPLACE VIEW pec.tb_dim_raca_cor
    AS SELECT * FROM public.tb_dim_raca_cor;

CREATE OR REPLACE VIEW pec.tb_dim_tipo_escolaridade
    AS SELECT * FROM public.tb_dim_tipo_escolaridade;

CREATE OR REPLACE VIEW pec.tb_exame_hemoglobina_glicada
    AS SELECT * FROM public.tb_exame_hemoglobina_glicada;

-- =====================================================================
-- VERIFICAÇÃO — rode após o setup para confirmar:
-- =====================================================================
-- SELECT count(*) FROM pec.tb_fat_cad_individual;  -- deve retornar > 0
-- SELECT count(*) FROM pec.tb_cidadao;              -- deve retornar > 0
-- SELECT count(*) FROM pec.tb_medicao;              -- deve retornar > 0
