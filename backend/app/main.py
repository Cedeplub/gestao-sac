import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.core.database import Base, init_oracle_client, write_engine
from app.core.security import get_password_hash
from app.models import Ocorrencia, OcorrenciaItem, OcorrenciaEvento, Usuario, Anexo  # noqa: F401 — registra modelos no Base
from app.utils.enums import RoleEnum
from app.web.dependencies import RequiresGerente, RequiresLogin
from app.web.routes import auth as web_auth, dashboard, ocorrencias as web_ocor, usuarios as web_users

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_oracle_client()
    try:
        Base.metadata.create_all(bind=write_engine)
        _seed_admin()
    except Exception:
        logger.exception("Falha na inicialização do banco")
    yield


app = FastAPI(
    title="Gestão SAC",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Static files
app.mount("/static", StaticFiles(directory="../frontend/static"), name="static")

# Web routes (server-side rendered)
app.include_router(web_auth.router)
app.include_router(dashboard.router)
app.include_router(web_ocor.router)
app.include_router(web_users.router)


@app.exception_handler(RequiresLogin)
async def requires_login_handler(request: Request, exc: RequiresLogin):
    return RedirectResponse(url="/login", status_code=302)


@app.exception_handler(RequiresGerente)
async def requires_gerente_handler(request: Request, exc: RequiresGerente):
    return RedirectResponse(url="/", status_code=302)


def _seed_admin():
    import os
    from sqlalchemy.orm import Session
    from app.models.usuario import Usuario as UsuarioModel

    senha = os.environ.get("ADMIN_PASSWORD")
    if not senha:
        logger.warning("ADMIN_PASSWORD não definida — seed de admin ignorado.")
        return

    with Session(write_engine) as db:
        gerente = db.query(UsuarioModel).filter(UsuarioModel.papel == RoleEnum.GERENTE).first()
        if not gerente:
            admin = UsuarioModel(
                nome="Administrador",
                email="admin@cedep.com",
                senha_hash=get_password_hash(senha),
                papel=RoleEnum.GERENTE.value,
                ativo=1,
            )
            db.add(admin)
            db.commit()
