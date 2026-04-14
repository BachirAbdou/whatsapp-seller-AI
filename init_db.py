from database import engine, Base
from models.seller import Seller
from models.product import Product
from models.order import Order

# Crée toutes les tables à partir des modèles
Base.metadata.create_all(bind=engine)

print("✅ Tables créées avec succès !")