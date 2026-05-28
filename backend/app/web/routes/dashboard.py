from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_write_db
from app.models.ocorrencia import Ocorrencia
from app.models.usuario import Usuario
from app.utils.enums import RoleEnum
from app.web.dependencies import get_current_web_user
from app.web.templates_config import templates

router = APIRouter(tags=["web-dashboard"])


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard_home(
    request: Request,
    current_user: Usuario = Depends(get_current_web_user),
    db: Session = Depends(get_write_db),
):
    counts_query = db.query(Ocorrencia.status, func.count(Ocorrencia.id))
    recentes_query = db.query(Ocorrencia)
    if current_user.papel == RoleEnum.OPERADOR:
        counts_query = counts_query.filter(Ocorrencia.atribuido_a_id == current_user.id)
        recentes_query = recentes_query.filter(Ocorrencia.atribuido_a_id == current_user.id)

    counts = dict(counts_query.group_by(Ocorrencia.status).all())
    recentes = recentes_query.order_by(Ocorrencia.created_at.desc()).limit(5).all()

    return templates.TemplateResponse(
        request,
        "pages/dashboard/home.html",
        {
            "current_user": current_user,
            "page_title": "Dashboard",
            "total": sum(counts.values()),
            "em_tratamento": counts.get("EM_TRATAMENTO", 0),
            "finalizado": counts.get("FINALIZADO", 0),
            "concluido": counts.get("CONCLUIDO", 0),
            "recentes": recentes,
        },
    )
