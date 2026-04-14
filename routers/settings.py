from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from database import SessionLocal
from models.seller import Seller
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from models.soubscription import Subscription
from typing import Optional
from datetime import datetime

templates = Jinja2Templates(directory="templates")

router = APIRouter()

@router.post("/settings/update")
def update_settings(
    request: Request,
    name: str = Form(...),
    assistant_name: str = Form(...),
    email: Optional[str] = Form(None),
    whatsapp_number: Optional[str] = Form(None)
):

    seller_id = request.cookies.get("seller_id")

    if not seller_id:
        return RedirectResponse("/login", status_code=303)

    seller_id = int(seller_id)

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.id == seller_id)\
        .first()

    if not seller:
        session.close()
        return RedirectResponse("/login", status_code=303)

    # 🔥 UPDATE NOM
    seller.name = name
    seller.assistant_name = assistant_name

    # 🔥 EMAIL (SEULEMENT SI FOURNI)
    if email:
        email = email.lower().strip()

        existing = session.query(Seller)\
            .filter(Seller.email == email, Seller.id != seller.id)\
            .first()

        if existing:
            session.close()
            return RedirectResponse("/settings?error=email", status_code=303)

        seller.email = email

    # 🔥 WHATSAPP
    if whatsapp_number is not None:
        seller.whatsapp_number = whatsapp_number

    session.commit()
    session.close()

    return RedirectResponse("/settings?success=1", status_code=303)

@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request):

    seller_id = request.cookies.get("seller_id")

    if not seller_id:
        return RedirectResponse("/login", status_code=303)

    seller_id = int(seller_id)

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.id == seller_id)\
        .first()

    success = request.query_params.get("success")
    error = request.query_params.get("error")

    subscription = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller_id,
            Subscription.status == "active"
        )\
        .order_by(Subscription.id.desc())\
        .first()

    session.close()

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "seller": seller,
            "subscription": subscription,
            "success": success,
            "error": error,
            "now": datetime.utcnow()
        }
    )