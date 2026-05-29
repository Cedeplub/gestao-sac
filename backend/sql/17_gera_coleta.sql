-- Migration 17: Adiciona campos de coleta à ocorrência
-- Executar como gestao_sac_dev no Oracle (192.168.0.98:1521/WINT)
--
-- gera_coleta       — boolean (0/1) indicando se a ocorrência demanda coleta
-- motorista_coleta  — nome do motorista responsável pela coleta (texto livre)

ALTER TABLE ocorrencias ADD (
    gera_coleta       NUMBER(1)     DEFAULT 0 NOT NULL,
    motorista_coleta  VARCHAR2(200)
);

ALTER TABLE ocorrencias ADD CONSTRAINT ck_ocor_gera_coleta CHECK (gera_coleta IN (0, 1));

COMMIT;
