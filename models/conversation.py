# models/conversation.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from database import Base
from datetime import datetime

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"))
    client_numero = Column(String)
    produit_pending = Column(String, nullable=True)
    etat = Column(String, default="waiting")  # waiting, pending_confirmation
    last_message = Column(String, nullable=True)
    date = Column(DateTime, default=datetime.now)