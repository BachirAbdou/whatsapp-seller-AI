from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)

    seller_id = Column(Integer, ForeignKey("sellers.id"))

    plan = Column(String)  # starter / pro / business

    status = Column(String, default="active")  # active / expired / cancelled

    start_date = Column(DateTime, default=datetime.utcnow)

    end_date = Column(DateTime)

    seller = relationship("Seller")