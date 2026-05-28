from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_write_db
from app.models.usuario import Usuario
from app.schemas.ocorrencia import (
    AdicionarComentarioRequest,
    AnexoResponse,
    AprovarRequest,
    ConcluirRequest,
    EncaminharRequest,
    EventoResponse,
    MarcarPendenteRequest,
    OcorrenciaCreate,
    OcorrenciaItemCreate,
    OcorrenciaItemResponse,
    OcorrenciaResponse,
    OcorrenciaUpdate,
    ReprovarRequest,
)
from app.services.anexo_service import anexo_service
from app.services.evento_service import evento_service
from app.services.ocorrencia_service import ocorrencia_service

router = APIRouter(prefix="/ocorrencias", tags=["Ocorrências"])


@router.post("/", response_model=OcorrenciaResponse, status_code=status.HTTP_201_CREATED)
def create_ocorrencia(
    data: OcorrenciaCreate,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.create(db, data, current_user)


@router.get("/", response_model=List[OcorrenciaResponse])
def list_ocorrencias(
    status_filter: Optional[str] = None,
    tipo_ocorrencia: Optional[str] = None,
    motivo: Optional[str] = None,
    causa_raiz: Optional[str] = None,
    responsavel_tipo: Optional[str] = None,
    atribuido_a_id: Optional[int] = None,
    numero_nota_fiscal: Optional[str] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.list(
        db, current_user,
        status_filter=status_filter,
        tipo_ocorrencia=tipo_ocorrencia,
        motivo=motivo,
        causa_raiz=causa_raiz,
        responsavel_tipo=responsavel_tipo,
        atribuido_a_id=atribuido_a_id,
        numero_nota_fiscal=numero_nota_fiscal,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@router.get("/{ocorrencia_id}", response_model=OcorrenciaResponse)
def get_ocorrencia(
    ocorrencia_id: int,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.get(db, ocorrencia_id, current_user)


@router.put("/{ocorrencia_id}", response_model=OcorrenciaResponse)
def update_ocorrencia(
    ocorrencia_id: int,
    data: OcorrenciaUpdate,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.update(db, ocorrencia_id, data, current_user)


# ---------- Transições de status ----------

@router.post("/{ocorrencia_id}/pendente", response_model=OcorrenciaResponse)
def marcar_pendente(
    ocorrencia_id: int,
    payload: MarcarPendenteRequest,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.marcar_pendente(db, ocorrencia_id, payload, current_user)


@router.post("/{ocorrencia_id}/encaminhar", response_model=OcorrenciaResponse)
def encaminhar(
    ocorrencia_id: int,
    payload: EncaminharRequest,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.encaminhar(db, ocorrencia_id, payload, current_user)


@router.post("/{ocorrencia_id}/concluir", response_model=OcorrenciaResponse)
def concluir(
    ocorrencia_id: int,
    payload: ConcluirRequest,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.concluir(db, ocorrencia_id, payload, current_user)


@router.post("/{ocorrencia_id}/aprovar", response_model=OcorrenciaResponse)
def aprovar(
    ocorrencia_id: int,
    payload: AprovarRequest,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.aprovar(db, ocorrencia_id, payload, current_user)


@router.post("/{ocorrencia_id}/reprovar", response_model=OcorrenciaResponse)
def reprovar(
    ocorrencia_id: int,
    payload: ReprovarRequest,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.reprovar(db, ocorrencia_id, payload, current_user)


@router.post("/{ocorrencia_id}/voltar", response_model=OcorrenciaResponse)
def voltar_para_tratamento(
    ocorrencia_id: int,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.voltar_para_tratamento(db, ocorrencia_id, current_user)


@router.post("/{ocorrencia_id}/comentarios", response_model=OcorrenciaResponse)
def adicionar_comentario(
    ocorrencia_id: int,
    payload: AdicionarComentarioRequest,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.adicionar_comentario(db, ocorrencia_id, payload, current_user)


@router.get("/{ocorrencia_id}/eventos", response_model=List[EventoResponse])
def listar_eventos(
    ocorrencia_id: int,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    ocorrencia_service.get(db, ocorrencia_id, current_user)  # valida acesso
    evts = evento_service.listar(db, ocorrencia_id)
    return [
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
        for e in evts
    ]


# ---------- Itens ----------

@router.post("/{ocorrencia_id}/itens", response_model=OcorrenciaItemResponse, status_code=status.HTTP_201_CREATED)
def adicionar_item(
    ocorrencia_id: int,
    payload: OcorrenciaItemCreate,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    return ocorrencia_service.adicionar_item(db, ocorrencia_id, payload, current_user)


@router.delete("/{ocorrencia_id}/itens/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_item(
    ocorrencia_id: int,
    item_id: int,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    ocorrencia_service.remover_item(db, ocorrencia_id, item_id, current_user)


# ---------- Anexos ----------

@router.post("/{ocorrencia_id}/anexos", response_model=AnexoResponse, status_code=status.HTTP_201_CREATED)
async def upload_anexo(
    ocorrencia_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    ocorrencia_service.get(db, ocorrencia_id, current_user)
    anexo = await anexo_service.save(db, ocorrencia_id, file, current_user)
    evento_service.registrar_evento(db, ocorrencia_id, "ANEXO_ADICIONADO", None, None, anexo.nome_arquivo, current_user.id)
    db.commit()
    return {
        "id": anexo.id,
        "nome_arquivo": anexo.nome_arquivo,
        "mime_type": anexo.mime_type,
        "tamanho": anexo.tamanho,
        "created_at": anexo.created_at,
    }


@router.get("/{ocorrencia_id}/anexos/{anexo_id}/download")
def download_anexo(
    ocorrencia_id: int,
    anexo_id: int,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    caminho, nome = anexo_service.get_file_path(db, anexo_id, current_user)
    return FileResponse(path=caminho, filename=nome)


@router.delete("/{ocorrencia_id}/anexos/{anexo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_anexo(
    ocorrencia_id: int,
    anexo_id: int,
    db: Session = Depends(get_write_db),
    current_user: Usuario = Depends(get_current_user),
):
    anexo_service.delete(db, anexo_id, current_user)
