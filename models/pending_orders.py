from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from database import Base
from datetime import datetime

class PendingOrder(Base):
    __tablename__ = "pending_orders"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer)
    client_numero = Column(String)
    produit = Column(String)
    status = Column(String, default="waiting_confirmation")
    date = Column(DateTime, default=datetime.utcnow)