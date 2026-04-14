from fastapi import Request
from fastapi import APIRouter
from fastapi.templating import Jinja2Templates
from database import SessionLocal
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from models.soubscription import Subscription
from auth.dependencies import get_current_seller
from fastapi import Depends
from fastapi import Form
from models.seller import Seller
from fastapi import HTTPException
from fastapi.responses import HTMLResponse

templates = Jinja2Templates(directory="templates")

router = APIRouter()

@router.get("/pricing")
def pricing_page(request: Request):

    return templates.TemplateResponse(
        "pricing.html",
        {"request": request}
    )

@router.post("/subscribe")
def subscribe(seller = Depends(get_current_seller)):

    session = SessionLocal()

    # créer abonnement en attente
    subscription = Subscription(
        seller_id=seller.id,
        plan="monthly",
        status="pending",
        start_date=None,
        end_date=None
    )

    session.add(subscription)
    session.commit()
    session.close()

    # 👉 ici tu redirigeras vers Mynita plus tard
    return RedirectResponse("/dashboard?payment=waiting", status_code=303)

@router.post("/subscribe/confirm")
def confirm_payment(seller = Depends(get_current_seller)):

    session = SessionLocal()

    sub = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller.id,
            Subscription.status == "pending"
        )\
        .order_by(Subscription.id.desc())\
        .first()

    if sub:
        sub.status = "active"
        sub.start_date = datetime.utcnow()
        sub.end_date = datetime.utcnow() + timedelta(days=30)

    session.commit()
    session.close()

    return RedirectResponse("/dashboard?payment=success", status_code=303)

'''@router.post("/subscribe/declare-payment")
def declare_payment(
    mynita_name: str = Form(...),
    seller = Depends(get_current_seller)
):

    session = SessionLocal()

    seller_db = session.query(Seller).filter(Seller.id == seller.id).first()

    # 🔴 SI déjà en attente → on bloque
    if seller_db.payment_status == "pending":
        session.close()
        return RedirectResponse("/dashboard?payment=already", status_code=303)

    # 🔴 SI déjà actif → on bloque aussi
    if seller_db.admin_approved:
        session.close()
        return RedirectResponse("/dashboard?payment=active", status_code=303)

    # ✅ Sinon on enregistre
    seller_db.mynita_name = mynita_name
    seller_db.payment_status = "pending"

    session.commit()
    session.close()

    return RedirectResponse("/dashboard?payment=waiting", status_code=303)'''

# Claude
@router.post("/subscribe/declare-payment")
def declare_payment(mynita_name: str = Form(...), seller = Depends(get_current_seller)):

    session = SessionLocal()
    seller_db = session.query(Seller).filter(Seller.id == seller.id).first()

    # 🔴 déjà en attente → bloquer
    if seller_db.payment_status == "pending":
        session.close()
        return RedirectResponse("/pricing?payment=already", status_code=303)

    # 🔴 abonnement encore actif → bloquer
    sub = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller.id,
            Subscription.status == "active"
        ).order_by(Subscription.id.desc()).first()

    if sub and sub.end_date > datetime.utcnow():
        session.close()
        return RedirectResponse("/pricing?payment=active", status_code=303)

    # ✅ enregistrer la demande
    seller_db.mynita_name = mynita_name
    seller_db.payment_status = "pending"

    session.commit()
    session.close()

    return RedirectResponse("/pricing?payment=waiting", status_code=303)

@router.post("/admin/confirm_payment/{seller_id}")
def confirm_payment(seller_id: int):

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.id == seller_id).first()

    # ✅ Activer statut vendeur
    # seller.payment_status = "approved"
    seller.admin_approved = True

    seller.payment_status = None  # ← ajouter ça

    # 🔥 Vérifier si abonnement déjà existant actif
    existing_sub = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller.id,
            Subscription.status == "active"
        )\
        .first()

    # ✅ Si abonnement expiré → prolonger, sinon créer
    if existing_sub:
        existing_sub.end_date = datetime.utcnow() + timedelta(days=30)
        existing_sub.status = "active"
        existing_sub.start_date = datetime.utcnow()
    else:
        subscription = Subscription(
            seller_id=seller.id,
            plan="monthly",
            status="active",
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30)
        )
        session.add(subscription)

    session.commit()
    session.close()

    return RedirectResponse("/admin/sellers", status_code=303)

# ne prend pas en compte l'abonnement de sept jours
'''def require_active_subscription(seller = Depends(get_current_seller)):

    session = SessionLocal()

    sub = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller.id,
            Subscription.status == "active"
        )\
        .order_by(Subscription.id.desc())\
        .first()

    session.close()

    if not sub or sub.end_date < datetime.utcnow():
        raise HTTPException(status_code=403)

    return seller'''
def require_active_subscription(seller = Depends(get_current_seller)):

    session = SessionLocal()

    seller_db = session.query(Seller).filter(Seller.id == seller.id).first()

    # ✅ 2. FREE TRIAL (7 jours)
    if seller_db.created_at:
        trial_end = seller_db.created_at + timedelta(days=7)
        if datetime.utcnow() < trial_end:
            session.close()
            return seller

    # ✅ 3. CHECK ABONNEMENT
    sub = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller.id,
            Subscription.status == "active"
        )\
        .order_by(Subscription.id.desc())\
        .first()

    session.close()

    if not sub or sub.end_date < datetime.utcnow():
        raise HTTPException(status_code=403)

    return seller

def require_approved_seller(seller = Depends(get_current_seller)):

    if not seller.is_approved:
        raise HTTPException(status_code=402)  # 👈 custom code

    return seller

@router.get("/pending-approval", response_class=HTMLResponse)
def pending_page(request: Request):

    seller_id = request.cookies.get("seller_id")

    if not seller_id:
        return RedirectResponse("/login")

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.id == int(seller_id)).first()

    session.close()

    if not seller:
        return RedirectResponse("/login")

    # ✅ si déjà approuvé → dashboard
    if seller.is_approved:
        return RedirectResponse("/dashboard")

    return templates.TemplateResponse(
        "pending.html",
        {
            "request": request,
            "seller": seller
        }
    )

@router.get("/dashboard/subscriptions", response_class=HTMLResponse)
def subscriptions_page(request: Request, seller = Depends(require_active_subscription)):

    session = SessionLocal()

    subs = session.query(Subscription)\
        .filter(Subscription.seller_id == seller.id)\
        .order_by(Subscription.id.desc())\
        .all()

    session.close()

    return templates.TemplateResponse(
        "subscriptions.html",
        {
            "request": request,
            "seller": seller,
            "subscriptions": subs,
            "now": datetime.utcnow()
        }
    )