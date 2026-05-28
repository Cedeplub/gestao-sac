-- ============================================================
-- MIGRATION 10: Permite reabertura de ocorrência FINALIZADA
-- Execução: conectado como gestao_sac
-- ============================================================

-- Adiciona 'REABERTA' ao CHECK constraint de tipo_evento
-- (Oracle não suporta ALTER ... MODIFY CONSTRAINT — precisa dropar e recriar)

ALTER TABLE ocorrencia_eventos DROP CONSTRAINT ck_oevt_tipo;

ALTER TABLE ocorrencia_eventos ADD CONSTRAINT ck_oevt_tipo CHECK (tipo_evento IN (
    'CRIADA', 'EDITADA', 'COMENTARIO', 'MUDANCA_STATUS', 'ANEXO_ADICIONADO',
    'ITEM_ADICIONADO', 'APROVADA', 'REPROVADA', 'ATRIBUICAO_ALTERADA', 'REABERTA'
));

COMMIT;
