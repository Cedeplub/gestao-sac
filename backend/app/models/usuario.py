from sqlalchemy import Column, Identity, Integer, String, Numeric, TIMESTAMP
from sqlalchemy.sql import func

from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, Identity(always=False), primary_key=True)
    nome = Column(String(200), nullable=False)
    email = Column(String(200), nullable=False, unique=True, index=True)
    senha_hash = Column(String(255), nullable=False)
    papel = Column(String(20), nullable=False)
    # Oracle < 23ai não tem tipo BOOLEAN — mantém Numeric(1). Use a property `is_ativo` no código.
    ativo = Column(Numeric(1), nullable=False, default=1)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    @property
    def is_ativo(self) -> bool:
        return bool(self.ativo)
