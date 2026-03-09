-- =====================================================================
-- SETUP do postgres_fdw no banco admin-esus
--
-- Cria a extensão, servidor remoto e foreign tables que espelham
-- as tabelas necessárias do banco pet_saude (e-SUS PEC).
--
-- EXECUTAR NO BANCO: admin-esus
-- REQUER: superuser ou permissão de CREATE EXTENSION
--
-- Após executar, as views materializadas em dashboard.* referenciam
-- as foreign tables em pec.* e o REFRESH puxa dados frescos do PEC.
-- =====================================================================

-- 1) Extensão
CREATE EXTENSION IF NOT EXISTS postgres_fdw;

-- 2) Servidor remoto apontando para pet_saude
-- (mesmo host, ajuste se necessário)
DROP SERVER IF EXISTS pec_server CASCADE;
CREATE SERVER pec_server
    FOREIGN DATA WRAPPER postgres_fdw
    OPTIONS (
        host 'localhost',
        port '5432',
        dbname 'pet_saude'
    );

-- 3) User mapping (ajuste a senha)
CREATE USER MAPPING IF NOT EXISTS FOR postgres
    SERVER pec_server
    OPTIONS (
        user 'postgres',
        password 'root'
    );

-- 4) Schema para foreign tables
CREATE SCHEMA IF NOT EXISTS pec;

-- 5) Importa TODAS as tabelas do schema public do pet_saude
-- Isso cria automaticamente foreign tables para cada tabela
IMPORT FOREIGN SCHEMA public
    FROM SERVER pec_server
    INTO pec;

-- 6) Schema para as views materializadas
CREATE SCHEMA IF NOT EXISTS dashboard;

-- 7) Schema para autenticação
CREATE SCHEMA IF NOT EXISTS auth;

-- =====================================================================
-- VERIFICAÇÃO — rode após o import para confirmar:
-- =====================================================================
-- SELECT count(*) FROM pec.tb_fat_cad_individual;  -- deve retornar > 0
-- SELECT count(*) FROM pec.tb_cidadao;              -- deve retornar > 0
-- SELECT count(*) FROM pec.tb_medicao;              -- deve retornar > 0
