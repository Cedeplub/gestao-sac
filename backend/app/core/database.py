import logging

import oracledb
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

_oracle_initialized = False


def init_oracle_client():
    global _oracle_initialized
    if _oracle_initialized:
        return
    lib_dir = r"C:\oracle\instantclient_21_17"
    try:
        oracledb.init_oracle_client(lib_dir=lib_dir)
    except Exception:
        # Já inicializado por outro processo ou cliente em thin mode — segue o jogo.
        logger.debug("init_oracle_client falhou (provavelmente já inicializado)", exc_info=True)
    _oracle_initialized = True


def _make_dsn(host: str, port: int, service: str) -> str:
    return f"oracle+oracledb://@{host}:{port}/?service_name={service}"


read_engine = create_engine(
    _make_dsn(settings.ORACLE_READ_HOST, settings.ORACLE_READ_PORT, settings.ORACLE_READ_SERVICE),
    connect_args={"user": settings.ORACLE_READ_USER, "password": settings.ORACLE_READ_PASSWORD},
    pool_pre_ping=True,
    pool_recycle=3600,
)

write_engine = create_engine(
    _make_dsn(settings.ORACLE_WRITE_HOST, settings.ORACLE_WRITE_PORT, settings.ORACLE_WRITE_SERVICE),
    connect_args={"user": settings.ORACLE_WRITE_USER, "password": settings.ORACLE_WRITE_PASSWORD},
    pool_pre_ping=True,
    pool_recycle=3600,
)

ReadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)
WriteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=write_engine)

Base = declarative_base()


def get_read_db():
    db = ReadSessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_write_db():
    db = WriteSessionLocal()
    try:
        yield db
    finally:
        db.close()
