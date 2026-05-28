from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.utils.enums import (
    CausaRaizEnum,
    ItemRoleEnum,
    MotivoEnum,
    ResponsavelTipoEnum,
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


# ---------- Ocorrência ----------

class OcorrenciaCreate(BaseModel):
    numero_nota_fiscal: int

    tipo_ocorrencia: Optional[TipoOcorrenciaEnum] = None
    motivo: Optional[MotivoEnum] = None
    causa_raiz: Optional[CausaRaizEnum] = None
    responsavel_tipo: Optional[ResponsavelTipoEnum] = None

    observacoes: Optional[str] = Field(default=None, max_length=2000)
    detalhes_especificos: Optional[dict[str, Any]] = None

    atribuido_a_id: Optional[int] = None  # default = current_user.id no service
    itens: List[OcorrenciaItemCreate] = []


class OcorrenciaUpdate(BaseModel):
    """Atualização parcial — só permitida em status EM_TRATAMENTO. Não altera status."""

    tipo_ocorrencia: Optional[TipoOcorrenciaEnum] = None
    motivo: Optional[MotivoEnum] = None
    causa_raiz: Optional[CausaRaizEnum] = None
    responsavel_tipo: Optional[ResponsavelTipoEnum] = None
    observacoes: Optional[str] = None
    detalhes_especificos: Optional[dict[str, Any]] = None
    atribuido_a_id: Optional[int] = None


# ---------- Transições de status ----------

class MarcarPendenteRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=1000)


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
