-- Migration 13: Adiciona tipos REPOSICAO_CEDEP e REPOSICAO_BONIFICADA
-- Executar como gestao_sac_dev no Oracle (192.168.0.98:1521/WINT)

ALTER TABLE ocorrencias DROP CONSTRAINT ck_ocor_tipo;

ALTER TABLE ocorrencias ADD CONSTRAINT ck_ocor_tipo CHECK (tipo_ocorrencia IN (
    'DEVOLUCAO_TOTAL', 'DEVOLUCAO_PARCIAL', 'REENVIO', 'REPOSICAO',
    'REPOSICAO_CEDEP', 'REPOSICAO_BONIFICADA'
));

COMMIT;
