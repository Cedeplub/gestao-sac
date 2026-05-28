import json
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import read_engine
from app.core.permissions import require_gerente
from app.models.ocorrencia import Ocorrencia
from app.models.ocorrencia_evento import OcorrenciaEvento
from app.models.ocorrencia_item import OcorrenciaItem
from app.schemas.ocorrencia import (
    AdicionarComentarioRequest,
    AprovarRequest,
    ConcluirRequest,
    EncaminharRequest,
    MarcarPendenteRequest,
    OcorrenciaCreate,
    OcorrenciaItemCreate,
    OcorrenciaUpdate,
    ReabrirRequest,
    ReprovarRequest,
)
from app.services.carregamento_service import carregamento_service
from app.services.evento_service import evento_service

# Diagrama de transições válidas:
# EM_TRATAMENTO -> PENDENTE | ENCAMINHADO | CONCLUIDO
# PENDENTE      -> EM_TRATAMENTO | ENCAMINHADO | CONCLUIDO
# ENCAMINHADO   -> EM_TRATAMENTO | PENDENTE | CONCLUIDO
# CONCLUIDO     -> FINALIZADO (aprovação gerente) | EM_TRATAMENTO (reprovação gerente)
# FINALIZADO    -> (terminal)
TRANSICOES_PERMITIDAS = {
    "EM_TRATAMENTO": {"PENDENTE", "ENCAMINHADO", "CONCLUIDO"},
    "PENDENTE":      {"EM_TRATAMENTO", "ENCAMINHADO", "CONCLUIDO"},
    "ENCAMINHADO":   {"EM_TRATAMENTO", "PENDENTE", "CONCLUIDO"},
    "CONCLUIDO":     {"FINALIZADO", "EM_TRATAMENTO"},
    "FINALIZADO":    {"EM_TRATAMENTO"},
}


def _validar_transicao(status_atual: str, novo_status: str) -> None:
    if novo_status not in TRANSICOES_PERMITIDAS.get(status_atual, set()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Transição inválida: {status_atual} → {novo_status}",
        )


def _validar_pode_editar(ocorrencia: Ocorrencia, current_user) -> None:
    """Operador só pode editar ocorrências onde é criador ou atribuído. Gerente pode tudo."""
    if ocorrencia.status == "FINALIZADO":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Ocorrência finalizada não pode ser alterada.",
        )
    if current_user.papel == "OPERADOR":
        if (
            ocorrencia.atribuido_a_id != current_user.id
            and ocorrencia.criado_por_id != current_user.id
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado.")


def _load(db: Session, ocorrencia_id: int) -> Ocorrencia:
    o = (
        db.query(Ocorrencia)
        .options(
            joinedload(Ocorrencia.criado_por),
            joinedload(Ocorrencia.atribuido_a),
            joinedload(Ocorrencia.aprovado_por),
            joinedload(Ocorrencia.anexos),
            joinedload(Ocorrencia.itens),
            joinedload(Ocorrencia.eventos).joinedload(OcorrenciaEvento.usuario),
        )
        .filter(Ocorrencia.id == ocorrencia_id)
        .first()
    )
    if not o:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ocorrência não encontrada.")
    return o


def _to_response(o: Ocorrencia) -> dict:
    return {
        "id": o.id,
        "numero_nota_fiscal": o.numero_nota_fiscal,
        "id_carregamento": o.id_carregamento,
        "data_faturamento": o.data_faturamento,
        "data_saida_carregamento": o.data_saida_carregamento,
        "cliente": o.cliente,
        "motorista": o.motorista,
        "vendedor": o.vendedor,
        "transportadora": o.transportadora,
        "valor_total": float(o.valor_total) if o.valor_total is not None else None,
        "tipo_ocorrencia": o.tipo_ocorrencia,
        "motivo": o.motivo,
        "causa_raiz": o.causa_raiz,
        "responsavel_tipo": o.responsavel_tipo,
        "observacoes": o.observacoes,
        "motivo_pendencia": o.motivo_pendencia,
        "resolucao_final": o.resolucao_final,
        "detalhes_especificos": o.detalhes_dict,
        "status": o.status,
        "criado_por_id": o.criado_por_id,
        "criado_por_nome": o.criado_por.nome if o.criado_por else None,
        "atribuido_a_id": o.atribuido_a_id,
        "atribuido_a_nome": o.atribuido_a.nome if o.atribuido_a else None,
        "aprovado_por_id": o.aprovado_por_id,
        "aprovado_por_nome": o.aprovado_por.nome if o.aprovado_por else None,
        "aprovado_em": o.aprovado_em,
        "created_at": o.created_at,
        "updated_at": o.updated_at,
        "anexos": [
            {
                "id": a.id,
                "nome_arquivo": a.nome_arquivo,
                "mime_type": a.mime_type,
                "tamanho": a.tamanho,
                "created_at": a.created_at,
            }
            for a in (o.anexos or [])
        ],
        "itens": [
            {
                "id": i.id,
                "codprod": i.codprod,
                "descricao_produto": i.descricao_produto,
                "qtd_afetada": float(i.qtd_afetada) if i.qtd_afetada is not None else None,
                "valor_unitario": float(i.valor_unitario) if i.valor_unitario is not None else None,
                "valor_total": float(i.valor_total) if i.valor_total is not None else None,
                "item_role": i.item_role,
                "created_at": i.created_at,
            }
            for i in (o.itens or [])
        ],
        "eventos": [
            {
                "id": e.id,
                "tipo_evento": e.tipo_evento,
                "status_anterior": e.status_anterior,
                "status_novo": e.status_novo,
                "comentario": e.comentario,
                "usuario_id": e.usuario_id,
                "usuario_nome": e.usuario.nome if e.usuario else None,
                "created_at": e.created_at,
            }
            for e in (o.eventos or [])
        ],
    }


def _criar_itens(db: Session, ocorrencia_id: int, itens: list[OcorrenciaItemCreate]) -> None:
    for item in itens:
        db.add(OcorrenciaItem(
            ocorrencia_id=ocorrencia_id,
            codprod=item.codprod,
            descricao_produto=item.descricao_produto,
            qtd_afetada=item.qtd_afetada,
            valor_unitario=item.valor_unitario,
            valor_total=item.valor_total,
            item_role=item.item_role.value,
        ))


class OcorrenciaService:

    @staticmethod
    def create(db: Session, data: OcorrenciaCreate, current_user) -> dict:
        # 1. Busca NF no CEDEP
        nota = carregamento_service.get_por_nota(read_engine, data.numero_nota_fiscal)
        if nota is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nota fiscal não encontrada no CEDEP.",
            )

        nf = nota["nota_fiscal"]

        # 2. Cria ocorrência com status EM_TRATAMENTO
        o = Ocorrencia(
            numero_nota_fiscal=str(data.numero_nota_fiscal),
            id_carregamento=nf.get("id_carregamento"),
            data_faturamento=nf.get("data_faturamento"),
            data_saida_carregamento=nf.get("data_saida_carregamento"),
            cliente=nf.get("cliente"),
            motorista=nf.get("motorista"),
            vendedor=nf.get("vendedor"),
            transportadora=nf.get("transportadora"),
            valor_total=nf.get("valor_total"),
            tipo_ocorrencia=data.tipo_ocorrencia.value if data.tipo_ocorrencia else None,
            motivo=data.motivo.value if data.motivo else None,
            causa_raiz=data.causa_raiz.value if data.causa_raiz else None,
            responsavel_tipo=data.responsavel_tipo.value if data.responsavel_tipo else None,
            observacoes=data.observacoes,
            detalhes_especificos=json.dumps(data.detalhes_especificos) if data.detalhes_especificos else None,
            status="EM_TRATAMENTO",
            criado_por_id=current_user.id,
            # 3. atribuído_a = informado ou o próprio criador
            atribuido_a_id=data.atribuido_a_id or current_user.id,
        )
        db.add(o)
        db.flush()  # obtém o.id sem commit

        # 4. Cria itens afetados
        _criar_itens(db, o.id, data.itens)

        # 5. Evento de criação
        evento_service.registrar_evento(
            db, o.id, "CRIADA", None, "EM_TRATAMENTO", None, current_user.id
        )

        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def list(
        db: Session,
        current_user,
        status_filter: Optional[str] = None,
        tipo_ocorrencia: Optional[str] = None,
        motivo: Optional[str] = None,
        causa_raiz: Optional[str] = None,
        responsavel_tipo: Optional[str] = None,
        atribuido_a_id: Optional[int] = None,
        numero_nota_fiscal: Optional[str] = None,
        data_inicio=None,
        data_fim=None,
    ) -> List[dict]:
        query = db.query(Ocorrencia).options(
            joinedload(Ocorrencia.criado_por),
            joinedload(Ocorrencia.atribuido_a),
            joinedload(Ocorrencia.aprovado_por),
            joinedload(Ocorrencia.anexos),
            joinedload(Ocorrencia.itens),
            joinedload(Ocorrencia.eventos).joinedload(OcorrenciaEvento.usuario),
        )

        # Todos os usuários autenticados veem todas as ocorrências
        if status_filter:
            query = query.filter(Ocorrencia.status == status_filter)
        if tipo_ocorrencia:
            query = query.filter(Ocorrencia.tipo_ocorrencia == tipo_ocorrencia)
        if motivo:
            query = query.filter(Ocorrencia.motivo == motivo)
        if causa_raiz:
            query = query.filter(Ocorrencia.causa_raiz == causa_raiz)
        if responsavel_tipo:
            query = query.filter(Ocorrencia.responsavel_tipo == responsavel_tipo)
        if atribuido_a_id:
            query = query.filter(Ocorrencia.atribuido_a_id == atribuido_a_id)
        if numero_nota_fiscal:
            query = query.filter(Ocorrencia.numero_nota_fiscal == numero_nota_fiscal)
        if data_inicio:
            query = query.filter(Ocorrencia.created_at >= data_inicio)
        if data_fim:
            query = query.filter(Ocorrencia.created_at <= data_fim)

        return [_to_response(o) for o in query.order_by(Ocorrencia.created_at.desc()).all()]

    @staticmethod
    def get(db: Session, ocorrencia_id: int, current_user) -> dict:
        return _to_response(_load(db, ocorrencia_id))

    @staticmethod
    def update(db: Session, ocorrencia_id: int, data: OcorrenciaUpdate, current_user) -> dict:
        """Edição de campos — só permitida em EM_TRATAMENTO."""
        o = _load(db, ocorrencia_id)
        _validar_pode_editar(o, current_user)

        if o.status != "EM_TRATAMENTO":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Edição de campos só é permitida no status EM_TRATAMENTO.",
            )

        atribuido_anterior = o.atribuido_a_id

        if data.tipo_ocorrencia is not None:
            o.tipo_ocorrencia = data.tipo_ocorrencia.value
        if data.motivo is not None:
            o.motivo = data.motivo.value
        if data.causa_raiz is not None:
            o.causa_raiz = data.causa_raiz.value
        if data.responsavel_tipo is not None:
            o.responsavel_tipo = data.responsavel_tipo.value
        if data.observacoes is not None:
            o.observacoes = data.observacoes
        if data.detalhes_especificos is not None:
            o.detalhes_especificos = json.dumps(data.detalhes_especificos)
        if data.atribuido_a_id is not None:
            # Operadores só podem reatribuir para si mesmos
            if current_user.papel == "OPERADOR" and data.atribuido_a_id != current_user.id:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                    detail="Operadores só podem reatribuir para si mesmos.")
            o.atribuido_a_id = data.atribuido_a_id

        evento_service.registrar_evento(db, o.id, "EDITADA", None, None, None, current_user.id)

        if data.atribuido_a_id is not None and data.atribuido_a_id != atribuido_anterior:
            evento_service.registrar_evento(db, o.id, "ATRIBUICAO_ALTERADA", None, None, None, current_user.id)

        db.commit()
        return _to_response(_load(db, o.id))

    # ---------- Transições de status ----------

    @staticmethod
    def marcar_pendente(db: Session, ocorrencia_id: int, payload: MarcarPendenteRequest, current_user) -> dict:
        """EM_TRATAMENTO | ENCAMINHADO -> PENDENTE"""
        o = _load(db, ocorrencia_id)
        _validar_pode_editar(o, current_user)
        _validar_transicao(o.status, "PENDENTE")

        anterior = o.status
        o.status = "PENDENTE"
        o.motivo_pendencia = payload.motivo
        evento_service.registrar_mudanca_status(db, o.id, anterior, "PENDENTE", payload.motivo, current_user.id)
        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def encaminhar(db: Session, ocorrencia_id: int, payload: EncaminharRequest, current_user) -> dict:
        """EM_TRATAMENTO | PENDENTE -> ENCAMINHADO"""
        o = _load(db, ocorrencia_id)
        _validar_pode_editar(o, current_user)
        _validar_transicao(o.status, "ENCAMINHADO")

        anterior = o.status
        o.status = "ENCAMINHADO"
        evento_service.registrar_mudanca_status(db, o.id, anterior, "ENCAMINHADO", payload.resolucao, current_user.id)
        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def concluir(db: Session, ocorrencia_id: int, payload: ConcluirRequest, current_user) -> dict:
        """EM_TRATAMENTO | PENDENTE | ENCAMINHADO -> CONCLUIDO"""
        o = _load(db, ocorrencia_id)
        _validar_pode_editar(o, current_user)
        _validar_transicao(o.status, "CONCLUIDO")

        anterior = o.status
        o.status = "CONCLUIDO"
        evento_service.registrar_mudanca_status(db, o.id, anterior, "CONCLUIDO", payload.comentario, current_user.id)
        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def aprovar(db: Session, ocorrencia_id: int, payload: AprovarRequest, current_user) -> dict:
        """CONCLUIDO -> FINALIZADO. Apenas GERENTE."""
        require_gerente(current_user)
        o = _load(db, ocorrencia_id)
        _validar_transicao(o.status, "FINALIZADO")

        anterior = o.status
        o.status = "FINALIZADO"
        o.resolucao_final = payload.resolucao_final
        o.aprovado_por_id = current_user.id
        o.aprovado_em = datetime.utcnow()
        evento_service.registrar_evento(
            db, o.id, "APROVADA", anterior, "FINALIZADO", payload.resolucao_final, current_user.id
        )
        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def reprovar(db: Session, ocorrencia_id: int, payload: ReprovarRequest, current_user) -> dict:
        """CONCLUIDO -> EM_TRATAMENTO. Apenas GERENTE."""
        require_gerente(current_user)
        o = _load(db, ocorrencia_id)
        _validar_transicao(o.status, "EM_TRATAMENTO")

        anterior = o.status
        o.status = "EM_TRATAMENTO"
        evento_service.registrar_evento(
            db, o.id, "REPROVADA", anterior, "EM_TRATAMENTO", payload.motivo_reprovacao, current_user.id
        )
        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def reabrir(db: Session, ocorrencia_id: int, payload: ReabrirRequest, current_user) -> dict:
        """FINALIZADO -> EM_TRATAMENTO. Apenas GERENTE. Motivo obrigatório."""
        require_gerente(current_user)
        o = _load(db, ocorrencia_id)
        _validar_transicao(o.status, "EM_TRATAMENTO")
        o.status = "EM_TRATAMENTO"
        evento_service.registrar_evento(
            db, o.id, "REABERTA", "FINALIZADO", "EM_TRATAMENTO", payload.motivo, current_user.id
        )
        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def voltar_para_tratamento(db: Session, ocorrencia_id: int, current_user) -> dict:
        """Qualquer status não-finalizado -> EM_TRATAMENTO (reabrir)."""
        o = _load(db, ocorrencia_id)
        _validar_pode_editar(o, current_user)
        _validar_transicao(o.status, "EM_TRATAMENTO")

        anterior = o.status
        o.status = "EM_TRATAMENTO"
        evento_service.registrar_mudanca_status(db, o.id, anterior, "EM_TRATAMENTO", None, current_user.id)
        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def adicionar_comentario(db: Session, ocorrencia_id: int, payload: AdicionarComentarioRequest, current_user) -> dict:
        """Gera evento COMENTARIO sem alterar status. Disponível enquanto não for FINALIZADO."""
        o = _load(db, ocorrencia_id)
        if o.status == "FINALIZADO":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Não é possível comentar em ocorrência finalizada.",
            )
        evento_service.registrar_evento(db, o.id, "COMENTARIO", None, None, payload.comentario, current_user.id)
        db.commit()
        return _to_response(_load(db, o.id))

    @staticmethod
    def adicionar_item(db: Session, ocorrencia_id: int, payload: OcorrenciaItemCreate, current_user) -> dict:
        o = _load(db, ocorrencia_id)
        _validar_pode_editar(o, current_user)

        item = OcorrenciaItem(
            ocorrencia_id=o.id,
            codprod=payload.codprod,
            descricao_produto=payload.descricao_produto,
            qtd_afetada=payload.qtd_afetada,
            valor_unitario=payload.valor_unitario,
            valor_total=payload.valor_total,
            item_role=payload.item_role.value,
        )
        db.add(item)
        evento_service.registrar_evento(db, o.id, "ITEM_ADICIONADO", None, None, payload.codprod, current_user.id)
        db.commit()
        db.refresh(item)
        return {
            "id": item.id,
            "codprod": item.codprod,
            "descricao_produto": item.descricao_produto,
            "qtd_afetada": float(item.qtd_afetada) if item.qtd_afetada is not None else None,
            "valor_unitario": float(item.valor_unitario) if item.valor_unitario is not None else None,
            "valor_total": float(item.valor_total) if item.valor_total is not None else None,
            "item_role": item.item_role,
            "created_at": item.created_at,
        }

    @staticmethod
    def remover_item(db: Session, ocorrencia_id: int, item_id: int, current_user) -> None:
        o = _load(db, ocorrencia_id)
        _validar_pode_editar(o, current_user)

        item = db.query(OcorrenciaItem).filter(
            OcorrenciaItem.id == item_id,
            OcorrenciaItem.ocorrencia_id == ocorrencia_id,
        ).first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item não encontrado.")
        db.delete(item)
        db.commit()


ocorrencia_service = OcorrenciaService()
