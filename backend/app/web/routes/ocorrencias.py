import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.database import get_write_db, read_engine
from app.models.ocorrencia import Ocorrencia
from app.models.usuario import Usuario
from app.schemas.ocorrencia import (
    AdicionarComentarioRequest,
    AprovarRequest,
    ConcluirRequest,
    MarcarPendenteRequest,
    OcorrenciaCreate,
    OcorrenciaItemCreate,
    OcorrenciaUpdate,
    ReabrirRequest,
    ReprovarRequest,
)
from app.utils.enums import ItemRoleEnum
from app.services.anexo_service import anexo_service
from app.services.carregamento_service import carregamento_service
from app.services.ocorrencia_service import ocorrencia_service
from app.utils.enums import (
    CausaRaizEnum,
    MotivoEnum,
    ResponsavelTipoEnum,
    TipoOcorrenciaEnum,
    get_enum_context,
)
from app.web.dependencies import get_current_web_user
from app.web.templates_config import templates

router = APIRouter(prefix="/ocorrencias", tags=["web-ocorrencias"])


def _mensagem_erro(exc: Exception, contexto: str) -> str:
    """Extrai detail de HTTPException; senão, loga e devolve mensagem genérica."""
    if isinstance(exc, HTTPException):
        return exc.detail
    logger.exception("%s", contexto)
    return "Erro interno. Tente novamente."


@router.get("", response_class=HTMLResponse, include_in_schema=False)
async def list_ocorrencias(
    request: Request,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    status: Optional[str] = None,
    tipo_ocorrencia: Optional[str] = None,
    motivo: Optional[str] = None,
    causa_raiz: Optional[str] = None,
    responsavel_tipo: Optional[str] = None,
    numero_nota_fiscal: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    # "0" = todos; ausente = current_user; outro int = filtrar pelo ID
    atribuido_a_id: Optional[str] = None,
):
    from datetime import date
    from app.services.user_service import user_service

    di = date.fromisoformat(data_inicio) if data_inicio else None
    df = date.fromisoformat(data_fim) if data_fim else None

    atribuido_filter_id, atribuido_filter_str = ocorrencia_service.resolver_filtro_atribuido(
        atribuido_a_id,
        "atribuido_a_id" in request.query_params,
        current_user,
    )

    ocorrencias = ocorrencia_service.list(
        db, current_user,
        status_filter=status or None,
        tipo_ocorrencia=tipo_ocorrencia or None,
        motivo=motivo or None,
        causa_raiz=causa_raiz or None,
        responsavel_tipo=responsavel_tipo or None,
        numero_nota_fiscal=numero_nota_fiscal or None,
        atribuido_a_id=atribuido_filter_id,
        data_inicio=di,
        data_fim=df,
    )

    # KPI consistente com o filtro de atribuição vigente na tela
    kpi_query = db.query(Ocorrencia).filter(Ocorrencia.status == "CONCLUIDO")
    if atribuido_filter_id is not None:
        kpi_query = kpi_query.filter(Ocorrencia.atribuido_a_id == atribuido_filter_id)
    aguardando_aprovacao = kpi_query.count()
    usuarios = user_service.get_all_users(db)

    return templates.TemplateResponse(
        request,
        "pages/ocorrencias/list.html",
        {
            "current_user": current_user,
            "page_title": "Ocorrências",
            "ocorrencias": ocorrencias,
            "aguardando_aprovacao": aguardando_aprovacao,
            "usuarios": usuarios,
            # filtros ativos
            "status_filter": status or "",
            "tipo_filter": tipo_ocorrencia or "",
            "motivo_filter": motivo or "",
            "causa_filter": causa_raiz or "",
            "responsavel_filter": responsavel_tipo or "",
            "nota_filter": numero_nota_fiscal or "",
            "data_inicio_filter": data_inicio or "",
            "data_fim_filter": data_fim or "",
            "atribuido_filter": atribuido_filter_str,
            **get_enum_context(),
        },
    )


@router.get("/nova", response_class=HTMLResponse, include_in_schema=False)
async def create_ocorrencia_page(
    request: Request,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
):
    from app.services.user_service import user_service
    usuarios = user_service.get_all_users(db)
    nf_dup_id = request.query_params.get("nf_dup_id", "")
    ocorrencia_existente = None
    if nf_dup_id:
        try:
            ocorrencia_existente = ocorrencia_service.get(db, int(nf_dup_id), current_user)
        except Exception:
            logger.warning("Falha ao carregar ocorrência existente nf_dup_id=%s", nf_dup_id, exc_info=True)
    return templates.TemplateResponse(
        request,
        "pages/ocorrencias/create.html",
        {
            "current_user": current_user,
            "page_title": "Nova Ocorrência",
            "usuarios": usuarios,
            "erro": request.query_params.get("erro", ""),
            "nf_dup_id": nf_dup_id,
            "ocorrencia_existente": ocorrencia_existente,
            **get_enum_context(),
        },
    )


@router.get("/buscar-nota", response_class=HTMLResponse, include_in_schema=False)
async def buscar_nota(
    request: Request,
    current_user: Usuario = Depends(get_current_web_user),
    numero_nota_fiscal: Optional[str] = None,
):
    nota = None
    erro = None
    if numero_nota_fiscal:
        try:
            resultado = carregamento_service.get_por_nota(read_engine, int(numero_nota_fiscal))
            if resultado:
                nota = resultado["nota_fiscal"]
            else:
                erro = "Nota fiscal não encontrada no CEDEP."
        except ValueError:
            erro = "Número de nota inválido."
        except Exception:
            logger.exception("Erro ao consultar nota %s no CEDEP", numero_nota_fiscal)
            erro = "Erro ao consultar nota fiscal no CEDEP."
    else:
        erro = "Informe o número da nota fiscal."

    return templates.TemplateResponse(
        request,
        "partials/nota_info.html",
        {"nota": nota, "erro": erro},
    )



@router.post("", include_in_schema=False)
async def create_ocorrencia(
    request: Request,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    numero_nota_fiscal: Optional[str] = Form(None),
    tipo_ocorrencia: Optional[str] = Form(None),
    motivo: Optional[str] = Form(None),
    causa_raiz: Optional[str] = Form(None),
    responsavel_tipo: Optional[str] = Form(None),
    observacoes: Optional[str] = Form(None),
    motivo_outro: Optional[str] = Form(None),
    causa_outro: Optional[str] = Form(None),
    atribuido_a_id: Optional[int] = Form(None),
    itens_json: str = Form("[]"),
    acao: Optional[str] = Form(None),
    arquivos: Optional[List[UploadFile]] = File(None),
):
    import json as _json

    if not numero_nota_fiscal:
        return RedirectResponse(url="/ocorrencias/nova?erro=Informe+a+nota+fiscal", status_code=302)

    # "Enviar para aprovação" requires all classification fields
    if acao == "concluir":
        faltando = []
        if not tipo_ocorrencia:
            faltando.append("Tipo de Ocorrência")
        if not motivo:
            faltando.append("Motivo")
        if not causa_raiz:
            faltando.append("Causa")
        if not responsavel_tipo:
            faltando.append("Responsável")
        if faltando:
            campos = ", ".join(faltando)
            return RedirectResponse(
                url=f"/ocorrencias/nova?erro=Preencha+os+campos+obrigatórios:+{campos}",
                status_code=302,
            )

    try:
        # Build detalhes_especificos from "Outros" free-text fields
        detalhes: dict = {}
        if motivo == "OUTRO" and motivo_outro:
            detalhes["motivo_outro"] = motivo_outro
        if causa_raiz == "OUTRO" and causa_outro:
            detalhes["causa_outro"] = causa_outro

        itens = []
        if itens_json:
            try:
                for raw in _json.loads(itens_json):
                    itens.append(OcorrenciaItemCreate(
                        codprod=str(raw.get("codprod", "")),
                        descricao_produto=raw.get("descricao_produto"),
                        qtd_afetada=raw.get("qtd_afetada"),
                        valor_unitario=raw.get("valor_unitario"),
                        valor_total=raw.get("valor_total"),
                        item_role=ItemRoleEnum(raw.get("item_role", "AFETADO")),
                    ))
            except Exception:
                logger.warning("Erro ao parsear itens_json", exc_info=True)

        data = OcorrenciaCreate(
            numero_nota_fiscal=int(numero_nota_fiscal),
            tipo_ocorrencia=TipoOcorrenciaEnum(tipo_ocorrencia) if tipo_ocorrencia else None,
            motivo=MotivoEnum(motivo) if motivo else None,
            causa_raiz=CausaRaizEnum(causa_raiz) if causa_raiz else None,
            responsavel_tipo=ResponsavelTipoEnum(responsavel_tipo) if responsavel_tipo else None,
            observacoes=observacoes or None,
            detalhes_especificos=detalhes or None,
            atribuido_a_id=atribuido_a_id or None,
            itens=itens,
        )
        result = ocorrencia_service.create(db, data, current_user)

        # Salva arquivos anexados no momento da criação (anexo_service.save já registra o evento)
        if arquivos:
            for file in arquivos:
                if file and file.filename:
                    await anexo_service.save(db, result["id"], file, current_user)

        if acao == "concluir":
            ocorrencia_service.concluir(
                db, result["id"], ConcluirRequest(comentario=None), current_user
            )
            return RedirectResponse(
                url=f"/ocorrencias/{result['id']}?sucesso=Ocorrência+enviada+para+aprovação",
                status_code=302,
            )

        return RedirectResponse(url=f"/ocorrencias/{result['id']}", status_code=302)
    except Exception as e:
        if isinstance(e, HTTPException) and str(e.detail or "").startswith("NF_DUPLICADA:"):
            nf_dup_id = str(e.detail).split(":")[1]
            return RedirectResponse(
                url=f"/ocorrencias/nova?nf_dup_id={nf_dup_id}",
                status_code=302,
            )
        elif isinstance(e, HTTPException) and "não encontrada" in (e.detail or "").lower():
            erro = "Nota fiscal não encontrada no CEDEP."
        else:
            erro = _mensagem_erro(e, "Erro ao criar ocorrência")
        return RedirectResponse(url=f"/ocorrencias/nova?erro={erro}", status_code=302)


@router.get("/{ocorrencia_id}", response_class=HTMLResponse, include_in_schema=False)
async def view_ocorrencia(
    ocorrencia_id: int,
    request: Request,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
):
    try:
        ocorrencia = ocorrencia_service.get(db, ocorrencia_id, current_user)
    except Exception:
        logger.warning("Falha ao carregar ocorrência %s para visualização", ocorrencia_id, exc_info=True)
        return RedirectResponse(url="/ocorrencias", status_code=302)

    return templates.TemplateResponse(
        request,
        "pages/ocorrencias/view.html",
        {
            "current_user": current_user,
            "page_title": f"Ocorrência #{ocorrencia_id}",
            "ocorrencia": ocorrencia,
            "sucesso": request.query_params.get("sucesso", ""),
            "erro": request.query_params.get("erro", ""),
            **get_enum_context(),
        },
    )


@router.get("/{ocorrencia_id}/editar", response_class=HTMLResponse, include_in_schema=False)
async def edit_ocorrencia_page(
    ocorrencia_id: int,
    request: Request,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
):
    try:
        ocorrencia = ocorrencia_service.get(db, ocorrencia_id, current_user)
    except Exception:
        logger.warning("Falha ao carregar ocorrência %s para edição", ocorrencia_id, exc_info=True)
        return RedirectResponse(url="/ocorrencias", status_code=302)

    if ocorrencia["status"] == "FINALIZADO":
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro=Ocorrência+finalizada", status_code=302)

    if ocorrencia["status"] != "EM_TRATAMENTO":
        return RedirectResponse(
            url=f"/ocorrencias/{ocorrencia_id}?erro=Edição+disponível+apenas+em+EM_TRATAMENTO",
            status_code=302,
        )

    from app.services.user_service import user_service
    usuarios = user_service.get_all_users(db)

    return templates.TemplateResponse(
        request,
        "pages/ocorrencias/edit.html",
        {
            "current_user": current_user,
            "page_title": f"Editar Ocorrência #{ocorrencia_id}",
            "ocorrencia": ocorrencia,
            "usuarios": usuarios,
            "erro": request.query_params.get("erro", ""),
            **get_enum_context(),
        },
    )


@router.post("/{ocorrencia_id}/atualizar", include_in_schema=False)
async def update_ocorrencia(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    tipo_ocorrencia: Optional[str] = Form(None),
    motivo: Optional[str] = Form(None),
    causa_raiz: Optional[str] = Form(None),
    responsavel_tipo: Optional[str] = Form(None),
    observacoes: Optional[str] = Form(None),
    atribuido_a_id: Optional[int] = Form(None),
    detalhes_especificos: Optional[str] = Form(None),
):
    import json as _json
    try:
        detalhes = None
        if detalhes_especificos:
            try:
                detalhes = _json.loads(detalhes_especificos)
            except Exception:
                logger.warning("detalhes_especificos inválido na atualização da ocorrência %s", ocorrencia_id, exc_info=True)
                detalhes = None

        data = OcorrenciaUpdate(
            tipo_ocorrencia=TipoOcorrenciaEnum(tipo_ocorrencia) if tipo_ocorrencia else None,
            motivo=MotivoEnum(motivo) if motivo else None,
            causa_raiz=CausaRaizEnum(causa_raiz) if causa_raiz else None,
            responsavel_tipo=ResponsavelTipoEnum(responsavel_tipo) if responsavel_tipo else None,
            observacoes=observacoes or None,
            detalhes_especificos=detalhes,
            atribuido_a_id=atribuido_a_id or None,
        )
        ocorrencia_service.update(db, ocorrencia_id, data, current_user)
        return RedirectResponse(
            url=f"/ocorrencias/{ocorrencia_id}?sucesso=Ocorrência+atualizada",
            status_code=302,
        )
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro ao atualizar ocorrência {ocorrencia_id}")
        return RedirectResponse(
            url=f"/ocorrencias/{ocorrencia_id}/editar?erro={erro}",
            status_code=302,
        )


# ---------- Transições de status via web ----------

@router.post("/{ocorrencia_id}/pendente", include_in_schema=False)
async def web_marcar_pendente(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    motivo: str = Form(...),
):
    try:
        ocorrencia_service.marcar_pendente(db, ocorrencia_id, MarcarPendenteRequest(motivo=motivo), current_user)
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?sucesso=Marcada+como+pendente", status_code=302)
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)


@router.post("/{ocorrencia_id}/concluir", include_in_schema=False)
async def web_concluir(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    comentario: Optional[str] = Form(None),
):
    try:
        ocorrencia_service.concluir(db, ocorrencia_id, ConcluirRequest(comentario=comentario or None), current_user)
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?sucesso=Ocorrência+concluída", status_code=302)
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)


@router.post("/{ocorrencia_id}/aprovar", include_in_schema=False)
async def web_aprovar(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    resolucao_final: Optional[str] = Form(None),
):
    try:
        ocorrencia_service.aprovar(db, ocorrencia_id, AprovarRequest(resolucao_final=resolucao_final), current_user)
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?sucesso=Ocorrência+finalizada", status_code=302)
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)


@router.post("/{ocorrencia_id}/reprovar", include_in_schema=False)
async def web_reprovar(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    motivo_reprovacao: str = Form(...),
):
    try:
        ocorrencia_service.reprovar(
            db, ocorrencia_id,
            ReprovarRequest(motivo_reprovacao=motivo_reprovacao),
            current_user,
        )
        return RedirectResponse(
            url=f"/ocorrencias/{ocorrencia_id}?sucesso=Ocorrência+reprovada+e+reaberta",
            status_code=302,
        )
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)


@router.post("/{ocorrencia_id}/reabrir", include_in_schema=False)
async def web_reabrir(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    motivo: str = Form(...),
):
    try:
        ocorrencia_service.reabrir(db, ocorrencia_id, ReabrirRequest(motivo=motivo), current_user)
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?sucesso=Ocorrência+reaberta", status_code=302)
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)


@router.post("/{ocorrencia_id}/voltar", include_in_schema=False)
async def web_voltar(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
):
    try:
        ocorrencia_service.voltar_para_tratamento(db, ocorrencia_id, current_user)
        return RedirectResponse(
            url=f"/ocorrencias/{ocorrencia_id}?sucesso=Voltou+para+tratamento",
            status_code=302,
        )
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)


@router.post("/{ocorrencia_id}/comentar", include_in_schema=False)
async def web_comentar(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    comentario: str = Form(...),
):
    try:
        ocorrencia_service.adicionar_comentario(
            db, ocorrencia_id,
            AdicionarComentarioRequest(comentario=comentario),
            current_user,
        )
        return RedirectResponse(
            url=f"/ocorrencias/{ocorrencia_id}?sucesso=Comentário+adicionado",
            status_code=302,
        )
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)


# ---------- Anexos ----------

@router.post("/{ocorrencia_id}/anexos", include_in_schema=False)
async def upload_anexo(
    ocorrencia_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
    file: UploadFile = File(...),
):
    try:
        ocorrencia_service.get(db, ocorrencia_id, current_user)
        await anexo_service.save(db, ocorrencia_id, file, current_user)
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?sucesso=Anexo+adicionado", status_code=302)
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)


@router.get("/{ocorrencia_id}/anexos/{anexo_id}/download", include_in_schema=False)
async def download_anexo_web(
    ocorrencia_id: int,
    anexo_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
):
    from fastapi.responses import FileResponse
    caminho, nome = anexo_service.get_file_path(db, anexo_id, current_user)
    return FileResponse(path=caminho, filename=nome, media_type="application/octet-stream")


@router.post("/{ocorrencia_id}/anexos/{anexo_id}/deletar", include_in_schema=False)
async def delete_anexo(
    ocorrencia_id: int,
    anexo_id: int,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
):
    try:
        anexo_service.delete(db, anexo_id, current_user)
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?sucesso=Anexo+removido", status_code=302)
    except Exception as e:
        erro = _mensagem_erro(e, f"Erro em ação web sobre ocorrência {ocorrencia_id}")
        return RedirectResponse(url=f"/ocorrencias/{ocorrencia_id}?erro={erro}", status_code=302)
