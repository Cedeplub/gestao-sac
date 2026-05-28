from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_write_db
from app.services.user_service import user_service
from app.web.session import create_token, load_token
from app.web.templates_config import templates

router = APIRouter(tags=["web-auth"])


@router.get("/login", response_class=HTMLResponse, include_in_schema=False)
async def login_page(request: Request):
    token = request.cookies.get("gsac_session")
    if token and load_token(token):
        return RedirectResponse(url="/", status_code=302)
    erro = request.query_params.get("erro", "")
    return templates.TemplateResponse(request, "pages/auth/login.html", {"erro": erro})


@router.post("/login", include_in_schema=False)
async def login_submit(
    request: Request,
    email: str = Form(...),
    senha: str = Form(...),
    db: Session = Depends(get_write_db),
):
    user = user_service.authenticate(db, email, senha)
    if not user:
        return RedirectResponse(url="/login?erro=Credenciais+inválidas", status_code=302)
    if not user.is_ativo:
        return RedirectResponse(url="/login?erro=Usuário+inativo", status_code=302)

    token = create_token(user.id, user.nome, user.papel)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="gsac_session", value=token, httponly=True, max_age=28800, samesite="lax")
    return response


@router.post("/logout", include_in_schema=False)
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("gsac_session")
    return response
