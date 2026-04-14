from sqlalchemy import Column, Integer, String, Boolean
from database import Base
from sqlalchemy import DateTime
from datetime import datetime

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer)
    client_numero = Column(String)
    message = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    seen = Column(Boolean, default=False)
