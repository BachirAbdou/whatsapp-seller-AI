from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base
from sqlalchemy.orm import relationship

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    seller_id = Column(Integer, ForeignKey("sellers.id"))  # <-- ligne à ajouter
    name = Column(String)
    price = Column(String)
    image = Column(String)
    description = Column(String)
    seller = relationship("Seller", back_populates="products")