-- Migration 15: Remove status ENCAMINHADO do fluxo de ocorrências
-- Executar como gestao_sac_dev no Oracle (192.168.0.98:1521/WINT)
--
-- ATENÇÃO: antes de aplicar, verifique se há registros existentes com este status:
--
--   SELECT COUNT(*) FROM ocorrencias WHERE status = 'ENCAMINHADO';
--
-- Se houver, decida qual destino dar a eles antes de rodar o ALTER:
--
--   UPDATE ocorrencias SET status = 'EM_TRATAMENTO' WHERE status = 'ENCAMINHADO';
--   COMMIT;
--
-- (EM_TRATAMENTO é o destino mais conservador — alternativas: PENDENTE)

ALTER TABLE ocorrencias DROP CONSTRAINT ck_ocor_status;

ALTER TABLE ocorrencias ADD CONSTRAINT ck_ocor_status CHECK (status IN (
    'EM_TRATAMENTO', 'PENDENTE', 'CONCLUIDO', 'FINALIZADO'
));

COMMIT;
