-- Migration 11: Limpeza de colunas obsoletas da tabela ocorrencias
-- Executar como gestao_sac_dev no Oracle (192.168.0.98:1521/WINT)

-- Remove colunas órfãs (nunca usadas no código atual)
ALTER TABLE ocorrencias DROP COLUMN encaminhamento;
ALTER TABLE ocorrencias DROP COLUMN observacoes;

-- Remove colunas descontinuadas
ALTER TABLE ocorrencias DROP COLUMN responsavel_descricao;
ALTER TABLE ocorrencias DROP COLUMN setor_destino;
ALTER TABLE ocorrencias DROP COLUMN resolucao_encaminhamento;

-- Renomeia descricao -> observacoes (novo nome canônico)
ALTER TABLE ocorrencias RENAME COLUMN descricao TO observacoes;

COMMIT;
