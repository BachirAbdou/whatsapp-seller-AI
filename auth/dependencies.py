from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from fastapi import Request, HTTPException
from database import SessionLocal
from models.seller import Seller
from auth.security import SECRET_KEY, ALGORITHM
from fastapi.responses import RedirectResponse
from fastapi import Request, HTTPException, status, Depends


security = HTTPBearer()

# vendeur pas approuvé
'''def get_current_seller(request: Request):

    seller_id = request.cookies.get("seller_id")

    if not seller_id:
        raise HTTPException(status_code=401)

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.id == int(seller_id)).first()

    session.close()

    if not seller:
        raise HTTPException(status_code=401)

    return seller'''
def get_current_seller(request: Request):

    seller_id = request.cookies.get("seller_id")

    if not seller_id:
        raise HTTPException(status_code=401)

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.id == int(seller_id)).first()

    session.close()

    if not seller:
        raise HTTPException(status_code=401)

    # 🔥 BLOQUER SI PAS APPROUVÉ et laisser passer les admins
    if seller.role not in ["admin", "superadmin"] and not seller.is_approved:
        raise HTTPException(status_code=402)

    return seller

def get_admin(request: Request):

    seller = get_current_seller(request)

    # 🔴 pas connecté
    if not seller:
        raise HTTPException(status_code=401)

    # 🔴 pas admin
    if seller.role not in ("admin", "superadmin"):
        raise HTTPException(status_code=403)

    return seller


def get_superadmin(request: Request):

    seller = get_current_seller(request)

    if seller.role != "superadmin":
        raise HTTPException(status_code=403)

    return seller