-- Migration 16: Adiciona tipo_evento ANEXO_REMOVIDO ao audit log
-- Executar como gestao_sac_dev no Oracle (192.168.0.98:1521/WINT)
--
-- Necessário a partir da abertura de acesso a anexos para todos os operadores:
-- a remoção passa a registrar evento ANEXO_REMOVIDO na timeline da ocorrência.

ALTER TABLE ocorrencia_eventos DROP CONSTRAINT ck_oevt_tipo;

ALTER TABLE ocorrencia_eventos ADD CONSTRAINT ck_oevt_tipo CHECK (tipo_evento IN (
    'CRIADA', 'EDITADA', 'COMENTARIO', 'MUDANCA_STATUS', 'ANEXO_ADICIONADO',
    'ANEXO_REMOVIDO', 'ITEM_ADICIONADO', 'APROVADA', 'REPROVADA',
    'ATRIBUICAO_ALTERADA', 'REABERTA'
));

COMMIT;
