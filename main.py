from database import SessionLocal
from models.seller import Seller
from models.product import Product

'''db = SessionLocal()

admins = db.query(Seller).filter(Seller.role == "superadmin").all()

for a in admins:
    print(a.id, a.email, a.role)

'''
db = SessionLocal()

seller = db.query(Seller).filter(Seller.email == "bachirabdou723@gmail.com").first()

seller.role = "superadmin"

db.commit()