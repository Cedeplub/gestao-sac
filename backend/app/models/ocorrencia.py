import json

from sqlalchemy import Column, Identity, Integer, String, Numeric, Date, TIMESTAMP, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Ocorrencia(Base):
    __tablename__ = "ocorrencias"

    id = Column(Integer, Identity(always=False), primary_key=True)

    # Nota fiscal
    numero_nota_fiscal = Column(String(50), nullable=False, index=True)

    # Snapshot do CEDEP no momento da criação
    id_carregamento = Column(Integer)
    data_faturamento = Column(Date)
    data_saida_carregamento = Column(Date)
    cliente = Column(String(200))
    motorista = Column(String(200))
    vendedor = Column(String(200))
    transportadora = Column(String(200))
    valor_total = Column(Numeric(15, 2))

    # Classificação da ocorrência
    motivo = Column(String(50), nullable=False)
    tipo_ocorrencia = Column(String(50))
    causa_raiz = Column(String(50))
    responsavel_tipo = Column(String(50))

    # Coleta (retorno da mercadoria)
    gera_coleta = Column(Numeric(1), nullable=False, default=0)
    motorista_coleta = Column(String(200))

    # Textos
    observacoes = Column(String(2000))
    motivo_pendencia = Column(String(1000))
    resolucao_final = Column(String(2000))
    detalhes_especificos = Column(Text)  # JSON armazenado em CLOB

    # Status do fluxo
    status = Column(String(30), nullable=False, default="EM_TRATAMENTO")

    # Relacionamentos de usuários
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    atribuido_a_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    aprovado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    aprovado_em = Column(TIMESTAMP)

    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    criado_por = relationship("Usuario", foreign_keys=[criado_por_id])
    atribuido_a = relationship("Usuario", foreign_keys=[atribuido_a_id])
    aprovado_por = relationship("Usuario", foreign_keys=[aprovado_por_id])
    anexos = relationship("Anexo", back_populates="ocorrencia", cascade="all, delete-orphan")
    itens = relationship("OcorrenciaItem", back_populates="ocorrencia", cascade="all, delete-orphan")
    eventos = relationship(
        "OcorrenciaEvento",
        back_populates="ocorrencia",
        cascade="all, delete-orphan",
        order_by="OcorrenciaEvento.created_at",
    )

    @property
    def detalhes_dict(self) -> dict | None:
        """Deserializa detalhes_especificos de JSON para dict."""
        if self.detalhes_especificos:
            try:
                return json.loads(self.detalhes_especificos)
            except (ValueError, TypeError):
                return None
        return None

    @property
    def gera_coleta_bool(self) -> bool:
        return bool(self.gera_coleta)
