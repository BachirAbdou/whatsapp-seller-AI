from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from database import SessionLocal
from models.seller import Seller
from auth.dependencies import get_admin
from models.order import Order
from models.message import Message
from fastapi import Form
from auth.security import hash_password
from auth.dependencies import get_superadmin
from fastapi.responses import RedirectResponse
from models.product import Product
from sqlalchemy.orm import joinedload
import requests
from models.soubscription import Subscription
from sqlalchemy import func
from datetime import datetime, timedelta
from auth.dependencies import get_current_seller

router = APIRouter(prefix="/admin")

templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
def admin_dashboard(
    request: Request,
    admin = Depends(get_admin)
):

    session = SessionLocal()

    sellers = session.query(Seller)\
        .filter(Seller.is_deleted == False)\
        .count()
    orders = session.query(Order).count()
    messages = session.query(Message).count()

    bots = session.query(Seller)\
        .filter(Seller.whatsapp_number != None)\
        .count()

    recent_sellers = session.query(Seller)\
        .filter(Seller.is_deleted == False)\
        .order_by(Seller.id.desc())\
        .limit(5)\
        .all()

    session.close()

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "sellers": sellers,
            "orders": orders,
            "messages": messages,
            "bots": bots,
            "recent_sellers": recent_sellers,
            "admin": admin
        }
    )


'''@router.get("/sellers", response_class=HTMLResponse)
def admin_sellers(
    request: Request,
    admin = Depends(get_admin)
):

    session = SessionLocal()

    sellers = session.query(Seller).all()

    session.close()

    return templates.TemplateResponse(
        "admin_sellers.html",
        {
            "request": request,
            "sellers": sellers
        }
    )
'''
@router.get("/sellers", response_class=HTMLResponse)
def admin_sellers(
    request: Request,
    search: str = "",
    admin = Depends(get_admin)
):

    session = SessionLocal()

    query = (
        session.query(Seller)
        .options(joinedload(Seller.products))  # ✅ AJOUT ICI
        .filter(Seller.is_deleted == False)
    )

    if search:
        query = query.filter(Seller.name.ilike(f"%{search}%"))

    sellers = query.all()

    session.close()

    return templates.TemplateResponse(
        "admin_sellers.html",
        {
            "request": request,
            "sellers": sellers,
            "search": search
        }
    )


@router.post("/create_admin")
def create_admin(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    admin = Depends(get_superadmin)
):

    session = SessionLocal()

    seller = Seller(
        name=name,
        email=email,
        password_hash=hash_password(password),
        role=role
    )

    session.add(seller)
    session.commit()

    session.close()

    return RedirectResponse("/admin/sellers", status_code=303)

@router.get("/bots", response_class=HTMLResponse)
def admin_bots(
    request: Request,
    admin = Depends(get_admin)
):

    session = SessionLocal()

    sellers = session.query(Seller)\
        .filter(Seller.is_deleted == False)\
        .all()

    session.close()

    return templates.TemplateResponse(
        "admin_bots.html",
        {
            "request": request,
            "sellers": sellers
        }
    )

@router.post("/api/bot_status")
def bot_status(data: dict):

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.id == data["seller_id"])\
        .first()

    if seller:

        seller.bot_status = data["status"]

        session.commit()

    session.close()

    return {"ok": True}


@router.get("/seller/{seller_id}", response_class=HTMLResponse)
def admin_seller_detail(

    seller_id: int,
    request: Request,
    admin = Depends(get_admin)

):

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.id == seller_id)\
        .first()

    products = session.query(Product)\
        .filter(Product.seller_id == seller_id)\
        .all()

    orders = session.query(Order)\
        .filter(Order.seller_id == seller_id)\
        .all()

    session.close()

    return templates.TemplateResponse(

        "admin_seller_detail.html",

        {
            "request": request,
            "seller": seller,
            "products": products,
            "orders": orders
        }

    )

@router.post("/approve_seller/{seller_id}")
def approve_seller(
    seller_id: int,
    admin = Depends(get_admin)
):

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.id == seller_id)\
        .first()

    seller.admin_approved = True

    session.commit()
    session.close()

    return RedirectResponse("/admin/sellers", status_code=303)

@router.post("/deactivate_seller/{seller_id}")
def deactivate_seller(
    seller_id: int,
    admin = Depends(get_admin)
):

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.id == seller_id)\
        .first()

    if not seller:
        session.close()
        return RedirectResponse("/admin/sellers", status_code=303)

    # 🔴 désactiver accès abonnement
    seller.admin_approved = False

    # 🔥 option (recommandé)
    seller.ai_enabled = False

    session.commit()
    session.close()

    return RedirectResponse("/admin/sellers", status_code=303)

@router.get("/orders")
def admin_orders(request: Request):

    return templates.TemplateResponse(
        "admin_orders.html",
        {"request": request}
    )

@router.get("/subscriptions")
def admin_subscriptions(request: Request):

    return templates.TemplateResponse(
        "admin_subscriptions.html",
        {"request": request}
    )

@router.get("/settings")
def admin_settings(request: Request):

    return templates.TemplateResponse(
        "admin_settings.html",
        {"request": request}
    )

@router.post("/delete_seller_permanent/{seller_id}")
def delete_seller_permanent(
    seller_id: int,
    admin = Depends(get_admin)
):

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.id == seller_id)\
        .first()

    try:
        requests.post(f"http://localhost:3000/disconnect/{seller_id}")
    except:
        pass

    if seller:

        # 🔥 supprimer tout
        session.query(Product).filter(Product.seller_id == seller_id).delete()
        session.query(Order).filter(Order.seller_id == seller_id).delete()
        session.query(Message).filter(Message.seller_id == seller_id).delete()
        session.query(Subscription).filter(Subscription.seller_id == seller_id).delete()

        # 💀 suppression définitive
        session.delete(seller)

    session.commit()
    session.close()

    return RedirectResponse("/admin/sellers", status_code=303)

@router.get("/create_admin", response_class=HTMLResponse)
def create_admin_page(request: Request, admin = Depends(get_admin)):

    return templates.TemplateResponse(
        "admin_create.html",
        {
            "request": request,
            "admin": admin
        }
    )

@router.post("/create_admin")
def create_admin(
    request: Request,
    name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    role: str = Form("admin"),
    admin = Depends(get_admin)
):

    if admin.role != "superadmin":
        return RedirectResponse("/admin/sellers", status_code=302)

    errors = {}

    # 🔴 validation
    if not name.strip():
        errors["name"] = "Le nom est requis"

    if not email.strip():
        errors["email"] = "L'email est requis"

    if not password.strip():
        errors["password"] = "Le mot de passe est requis"
    elif len(password) < 6:
        errors["password"] = "Minimum 6 caractères"

    # si erreurs → renvoyer form
    if errors:
        return templates.TemplateResponse(
            "admin_create.html",
            {
                "request": request,
                "errors": errors,
                "form": {
                    "name": name,
                    "email": email,
                    "role": role
                },
                "admin": admin
            }
        )

    session = SessionLocal()

    try:
        existing = session.query(Seller).filter(Seller.email == email).first()

        if existing:
            return templates.TemplateResponse(
                "admin_create.html",
                {
                    "request": request,
                    "error": "Email déjà utilisé",
                    "form": {
                        "name": name,
                        "email": email,
                        "role": role
                    },
                    "admin": admin
                }
            )

        if role not in ["admin", "superadmin"]:
            role = "admin"

        new_admin = Seller(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
            admin_approved=True,
            ai_enabled=False
        )

        session.add(new_admin)
        session.commit()

    finally:
        session.close()

    return RedirectResponse("/admin/sellers?created=1", status_code=302)

@router.post("/admin_logout")
def admin_logout():

    response = RedirectResponse(url="/login", status_code=302)

    # 🧹 supprimer le bon cookie
    response.delete_cookie("seller_id")

    return response

@router.post("/approve/{seller_id}")
def approve(seller_id: int):

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.id == seller_id).first()

    if seller:
        seller.is_approved = True
        session.commit()

    session.close()

    return RedirectResponse("/admin/sellers", status_code=303)

@router.post("/deactivate/{seller_id}")
def deactivate_seller(seller_id: int):
    session = SessionLocal()
    seller = session.query(Seller).filter(Seller.id == seller_id).first()
    if seller:
        seller.is_approved = False
        session.commit()
    session.close()
    return RedirectResponse("/admin/sellers", status_code=303)

@router.get("/api/activity")
def get_activity(request: Request):

    seller = get_current_seller(request)
    seller_id = seller.id

    session = SessionLocal()

    seven_days_ago = datetime.utcnow() - timedelta(days=6)

    results = (
        session.query(
            func.date(Message.created_at).label("day"),
            func.count(Message.id)
        )
        .filter(Message.seller_id == seller_id)
        .filter(Message.created_at >= seven_days_ago)
        .group_by(func.date(Message.created_at))
        .all()
    )

    session.close()

    data_map = {str(r.day): r[1] for r in results}

    output = []

    for i in range(7):
        day = datetime.utcnow() - timedelta(days=6 - i)
        day_str = day.strftime("%Y-%m-%d")

        count = data_map.get(day_str, 0)

        label = ["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"][day.weekday()]

        output.append({
            "day": label,
            "count": count
        })

    return output