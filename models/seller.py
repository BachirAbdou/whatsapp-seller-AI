from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base
from datetime import datetime
from sqlalchemy.orm import relationship

class Seller(Base):
    __tablename__ = "sellers"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    assistant_name = Column(String)   # nouveau champ
    slug = Column(String, unique=True)
    phone = Column(String)
    whatsapp_number = Column(String)
    email = Column(String, unique=True, nullable=False)       # <-- ajouté
    password_hash = Column(String, nullable=False) 
    ai_enabled = Column(Boolean, default=True)
    role = Column(String, default="seller")
    bot_status = Column(String, default="offline")

    # 🔹 validation admin
    admin_approved = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    products = relationship("Product", back_populates="seller")
    is_deleted = Column(Boolean, default=False)

    email_verified = Column(Boolean, default=False)
    email_token = Column(String, nullable=True)

    mynita_name = Column(String, nullable=True)
    payment_status = Column(String, default="none")

    is_approved = Column(Boolean, default=False)

    reset_token = Column(String, nullable=True)
    reset_token_expiry = Column(DateTime, nullable=True)

    context_note = Column(String, nullable=True)