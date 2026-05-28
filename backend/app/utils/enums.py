from enum import Enum


class RoleEnum(str, Enum):
    OPERADOR = "OPERADOR"
    GERENTE = "GERENTE"


class StatusOcorrenciaEnum(str, Enum):
    EM_TRATAMENTO = "EM_TRATAMENTO"
    PENDENTE = "PENDENTE"
    CONCLUIDO = "CONCLUIDO"
    FINALIZADO = "FINALIZADO"


class MotivoEnum(str, Enum):
    AVARIA = "AVARIA"
    INVERSAO_MERCADORIA = "INVERSAO_MERCADORIA"
    FALTA_MERCADORIA = "FALTA_MERCADORIA"
    SOBRA_MERCADORIA = "SOBRA_MERCADORIA"
    DEVOLUCAO_SOLICITADA = "DEVOLUCAO_SOLICITADA"
    PEDIDO_TROCA = "PEDIDO_TROCA"
    EXTRAVIO = "EXTRAVIO"
    ATRASO_ENTREGA = "ATRASO_ENTREGA"
    PEDIDO_DUPLICADO = "PEDIDO_DUPLICADO"
    PEDIDO_DESACORDO = "PEDIDO_DESACORDO"
    RAZAO_SOCIAL_DESACORDO = "RAZAO_SOCIAL_DESACORDO"
    OUTRO = "OUTRO"


class TipoOcorrenciaEnum(str, Enum):
    DEVOLUCAO_TOTAL = "DEVOLUCAO_TOTAL"
    DEVOLUCAO_PARCIAL = "DEVOLUCAO_PARCIAL"
    REENVIO = "REENVIO"
    REPOSICAO = "REPOSICAO"
    REPOSICAO_CEDEP = "REPOSICAO_CEDEP"
    REPOSICAO_BONIFICADA = "REPOSICAO_BONIFICADA"


class CausaRaizEnum(str, Enum):
    ERRO_EXPEDICAO = "ERRO_EXPEDICAO"
    ERRO_VENDEDOR = "ERRO_VENDEDOR"
    ERRO_TRANSPORTADORA = "ERRO_TRANSPORTADORA"
    ERRO_MOTORISTA = "ERRO_MOTORISTA"
    DEFEITO_FABRICA = "DEFEITO_FABRICA"
    DESISTENCIA_CLIENTE = "DESISTENCIA_CLIENTE"
    ERRO_CLIENTE = "ERRO_CLIENTE"
    FORA_ROTA = "FORA_ROTA"
    OUTRO = "OUTRO"


class ResponsavelTipoEnum(str, Enum):
    CEDEP = "CEDEP"
    VENDEDOR = "VENDEDOR"
    TRANSPORTADORA = "TRANSPORTADORA"
    MOTORISTA = "MOTORISTA"
    CLIENTE = "CLIENTE"
    FABRICANTE = "FABRICANTE"
    NAO_APLICAVEL = "NAO_APLICAVEL"


class ItemRoleEnum(str, Enum):
    AFETADO = "AFETADO"
    ENVIADO_INCORRETAMENTE = "ENVIADO_INCORRETAMENTE"
    ITEM_CORRETO = "ITEM_CORRETO"


class TipoEventoEnum(str, Enum):
    CRIADA = "CRIADA"
    EDITADA = "EDITADA"
    COMENTARIO = "COMENTARIO"
    MUDANCA_STATUS = "MUDANCA_STATUS"
    ANEXO_ADICIONADO = "ANEXO_ADICIONADO"
    ANEXO_REMOVIDO = "ANEXO_REMOVIDO"
    ITEM_ADICIONADO = "ITEM_ADICIONADO"
    APROVADA = "APROVADA"
    REPROVADA = "REPROVADA"
    ATRIBUICAO_ALTERADA = "ATRIBUICAO_ALTERADA"
    REABERTA = "REABERTA"


# Labels em PT-BR para templates — evita duplicação.
STATUS_LABELS = {
    "EM_TRATAMENTO": "Em tratamento",
    "PENDENTE": "Pendente",
    "CONCLUIDO": "Aguardando aprovação",
    "FINALIZADO": "Finalizado",
}

TIPO_LABELS = {
    "DEVOLUCAO_TOTAL": "Devolução total",
    "DEVOLUCAO_PARCIAL": "Devolução parcial",
    "REENVIO": "Reenvio",
    "REPOSICAO": "Reposição (faturamento contra terceiro)",
    "REPOSICAO_CEDEP": "Reposição (CEDEP)",
    "REPOSICAO_BONIFICADA": "Reposição bonificada",
}

MOTIVO_LABELS = {
    "AVARIA": "Avaria",
    "INVERSAO_MERCADORIA": "Inversão de mercadoria",
    "FALTA_MERCADORIA": "Falta de mercadoria",
    "SOBRA_MERCADORIA": "Sobra de mercadoria",
    "DEVOLUCAO_SOLICITADA": "Devolução solicitada",
    "PEDIDO_TROCA": "Pedido de troca",
    "EXTRAVIO": "Extravio",
    "ATRASO_ENTREGA": "Atraso na entrega",
    "PEDIDO_DUPLICADO": "Pedido duplicado",
    "PEDIDO_DESACORDO": "Pedido em desacordo",
    "RAZAO_SOCIAL_DESACORDO": "Razão social em desacordo",
    "OUTRO": "Outro",
}

CAUSA_LABELS = {
    "ERRO_EXPEDICAO": "Erro na expedição",
    "ERRO_VENDEDOR": "Erro do vendedor",
    "ERRO_TRANSPORTADORA": "Erro da transportadora",
    "ERRO_MOTORISTA": "Erro do motorista",
    "DEFEITO_FABRICA": "Defeito de fábrica",
    "DESISTENCIA_CLIENTE": "Desistência do cliente",
    "ERRO_CLIENTE": "Erro do cliente",
    "FORA_ROTA": "Fora de rota",
    "OUTRO": "Outro",
}

RESPONSAVEL_LABELS = {
    "CEDEP": "Expedição",
    "VENDEDOR": "Vendedor",
    "TRANSPORTADORA": "Transportadora",
    "MOTORISTA": "Motorista",
    "CLIENTE": "Cliente",
    "FABRICANTE": "Fabricante",
    "NAO_APLICAVEL": "Não aplicável",
}


def get_enum_context() -> dict:
    """Contexto de enums e labels para templates de ocorrência."""
    return {
        "tipos": TipoOcorrenciaEnum,
        "motivos": MotivoEnum,
        "causas": CausaRaizEnum,
        "responsaveis": ResponsavelTipoEnum,
        "status_enum": StatusOcorrenciaEnum,
        "tipo_labels": TIPO_LABELS,
        "motivo_labels": MOTIVO_LABELS,
        "causa_labels": CAUSA_LABELS,
        "responsavel_labels": RESPONSAVEL_LABELS,
        "status_labels": STATUS_LABELS,
    }
