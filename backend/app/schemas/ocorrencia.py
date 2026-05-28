from datetime import date, datetime
from typing import Any, List, Optional

from pydantic import BaseModel, Field, model_validator

from app.utils.enums import (
    CausaRaizEnum,
    ItemRoleEnum,
    MotivoEnum,
    ResponsavelTipoEnum,
    SetorDestinoEnum,
    StatusOcorrenciaEnum,
    TipoOcorrenciaEnum,
)


# ---------- Itens ----------

class OcorrenciaItemCreate(BaseModel):
    codprod: Optional[str] = None
    descricao_produto: Optional[str] = None
    qtd_afetada: Optional[float] = None
    valor_unitario: Optional[float] = None
    valor_total: Optional[float] = None
    item_role: ItemRoleEnum = ItemRoleEnum.AFETADO


class OcorrenciaItemResponse(OcorrenciaItemCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Anexo ----------

class AnexoResponse(BaseModel):
    id: int
    nome_arquivo: str
    mime_type: Optional[str]
    tamanho: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Evento ----------

class EventoResponse(BaseModel):
    id: int
    tipo_evento: str
    status_anterior: Optional[str]
    status_novo: Optional[str]
    comentario: Optional[str]
    usuario_id: int
    usuario_nome: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Ocorrência ----------

class OcorrenciaCreate(BaseModel):
    numero_nota_fiscal: int

    tipo_ocorrencia: Optional[TipoOcorrenciaEnum] = None  # DEVOLUCAO_TOTAL, REENVIO, etc.
    motivo: Optional[MotivoEnum] = None                   # AVARIA, FALTA_MERCADORIA, etc.
    causa_raiz: Optional[CausaRaizEnum] = None
    responsavel_tipo: Optional[ResponsavelTipoEnum] = None
    responsavel_descricao: Optional[str] = Field(default=None, max_length=200)
    setor_destino: Optional[SetorDestinoEnum] = None

    descricao: Optional[str] = Field(default=None, max_length=2000)
    detalhes_especificos: Optional[dict[str, Any]] = None

    atribuido_a_id: Optional[int] = None  # default = current_user.id no service
    itens: List[OcorrenciaItemCreate] = []


class OcorrenciaUpdate(BaseModel):
    """Atualização parcial — só permitida em status EM_TRATAMENTO. Não altera status."""

    tipo_ocorrencia: Optional[TipoOcorrenciaEnum] = None  # DEVOLUCAO_TOTAL, REENVIO, etc.
    motivo: Optional[MotivoEnum] = None                   # AVARIA, FALTA_MERCADORIA, etc.
    causa_raiz: Optional[CausaRaizEnum] = None
    responsavel_tipo: Optional[ResponsavelTipoEnum] = None
    responsavel_descricao: Optional[str] = None
    setor_destino: Optional[SetorDestinoEnum] = None
    descricao: Optional[str] = None
    detalhes_especificos: Optional[dict[str, Any]] = None
    atribuido_a_id: Optional[int] = None


class OcorrenciaResponse(BaseModel):
    id: int
    numero_nota_fiscal: str
    id_carregamento: Optional[int]
    data_faturamento: Optional[date]
    data_saida_carregamento: Optional[date]
    cliente: Optional[str]
    motorista: Optional[str]
    vendedor: Optional[str]
    transportadora: Optional[str]
    valor_total: Optional[float]

    tipo_ocorrencia: Optional[str]  # DEVOLUCAO_TOTAL, REENVIO, etc.
    motivo: Optional[str]           # AVARIA, FALTA_MERCADORIA, etc.
    causa_raiz: Optional[str]
    responsavel_tipo: Optional[str]
    responsavel_descricao: Optional[str]
    setor_destino: Optional[str]

    descricao: Optional[str]
    motivo_pendencia: Optional[str]
    resolucao_encaminhamento: Optional[str]
    resolucao_final: Optional[str]
    detalhes_especificos: Optional[dict[str, Any]]

    status: str
    criado_por_id: int
    criado_por_nome: Optional[str]
    atribuido_a_id: int
    atribuido_a_nome: Optional[str]
    aprovado_por_id: Optional[int]
    aprovado_por_nome: Optional[str]
    aprovado_em: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    anexos: List[AnexoResponse] = []
    itens: List[OcorrenciaItemResponse] = []
    eventos: List[EventoResponse] = []

    class Config:
        from_attributes = True


# ---------- Transições de status ----------

class MarcarPendenteRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=1000)


class EncaminharRequest(BaseModel):
    setor_destino: SetorDestinoEnum
    resolucao: str = Field(..., min_length=3, max_length=2000)


class ConcluirRequest(BaseModel):
    comentario: Optional[str] = Field(default=None, max_length=2000)


class AprovarRequest(BaseModel):
    resolucao_final: Optional[str] = Field(default=None, max_length=2000)


class ReprovarRequest(BaseModel):
    motivo_reprovacao: str = Field(..., min_length=3, max_length=2000)


class AdicionarComentarioRequest(BaseModel):
    comentario: str = Field(..., min_length=1, max_length=2000)


class ReabrirRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=2000)
