from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from database import Base
from datetime import datetime

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"))
    client_nom = Column(String)
    client_numero = Column(String)
    produit = Column(String)
    adresse = Column(String)
    ville = Column(String, nullable=True)
    statut = Column(String, default="En attente")  # En attente, En cours, Livrée
    date = Column(DateTime, default=datetime.now)
    seen = Column(Boolean, default=False)