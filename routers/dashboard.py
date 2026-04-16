from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.responses import StreamingResponse
import requests, qrcode
from io import BytesIO
from auth.dependencies import get_current_seller
from database import SessionLocal
from models.product import Product
from models.order import Order
from models.message import Message
from fastapi.templating import Jinja2Templates
from models.seller import Seller
from fastapi.responses import RedirectResponse
from PIL import Image, ImageDraw
from services.subscription_service import seller_has_active_subscription
from routers.soubscriptions import require_active_subscription
from models.soubscription import Subscription
from fastapi.responses import Response
from datetime import datetime
from datetime import datetime, timedelta
import math
from datetime import datetime
from sqlalchemy import func, cast, Date


router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/dashboard")
def dashboard(request: Request, seller = Depends(require_active_subscription)):

    session = SessionLocal()

    orders = session.query(Order).filter(Order.seller_id == seller.id).count()

    products = session.query(Product).filter(Product.seller_id == seller.id).count()

    messages = session.query(Message).filter(Message.seller_id == seller.id).count()

    subscription = session.query(Subscription)\
    .filter(
        Subscription.seller_id == seller.id,
        Subscription.status == "active"
    )\
    .order_by(Subscription.id.desc())\
    .first()

    days_left = None
    hours_left = None

    if subscription:
        remaining = subscription.end_date - datetime.utcnow()
        total_seconds = remaining.total_seconds()

        if total_seconds <= 0:
            subscription = None
            days_left = 0
            hours_left = 0
        else:
            days_left = int(total_seconds // 86400)
            hours_left = int((total_seconds % 86400) // 3600)
    else:
        days_left = 0
        hours_left = 0

    session.close()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "seller": seller,
            "orders": orders,
            "products": products,
            "messages": messages,
            "subscription": subscription,
            "days_left": days_left,
            "hours_left": hours_left
        }
    )

'''@router.get("/dashboard/settings", response_class=HTMLResponse)
def settings_page(request: Request, seller = Depends(get_current_seller)):

    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "seller": seller
        }
    )'''
@router.get("/dashboard/settings", response_class=HTMLResponse)
def settings_page(request: Request, seller = Depends(require_active_subscription)):

    session = SessionLocal()

    recent_orders = session.query(Order)\
        .filter(Order.seller_id == seller.id)\
        .order_by(Order.date.desc())\
        .limit(5)\
        .all()

    # 🔥 AJOUTER ÇA
    subscription = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller.id,
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
            "recent_orders": recent_orders,
            "subscription": subscription,
            "now": datetime.utcnow()  
        }
    )

@router.post("/dashboard/ia_toggle")
def ia_toggle(activate: bool = Form(...), seller = Depends(get_current_seller)):

    session = SessionLocal()

    seller_db = session.query(Seller).filter(Seller.id == seller.id).first()

    seller_db.ai_enabled = activate

    print("IA activate:", activate)

    session.commit()
    session.close()

    return RedirectResponse(url="/dashboard", status_code=303)

'''
@app.post("/dashboard/connect_whatsapp")
def connect_whatsapp(seller = Depends(get_current_seller)):
    import requests
    resp = requests.post("http://localhost:3000/connect", json={"seller_id": seller.id})
    return {"message": resp.json()}
'''
@router.post("/dashboard/connect_whatsapp")
def connect_whatsapp(seller = Depends(get_current_seller)):

    session = SessionLocal()

    if not seller_has_active_subscription(session, seller.id):
        session.close()

        return RedirectResponse("/pricing", status_code=303)

    session.close()

    requests.post(
        "http://localhost:3000/connect",
        json={"seller_id": seller.id}
    )

    return {"message": "connexion lancée"}

@router.get("/dashboard/connect_whatsapp_qr")
def connect_whatsapp_qr(seller = Depends(get_current_seller)):

    session = SessionLocal()

    if not seller_has_active_subscription(session, seller.id):
        session.close()
        return Response(status_code=403)

    session.close()

    BASE_URL = "https://TON-NODE-SERVICE.onrender.com"

    try:
        resp = requests.get(f"{BASE_URL}/qr/{seller.id}", timeout=10)
        data = resp.json()

        print("QR STATUS NODE:", data)
    
    except:
        return Response(status_code=204)

    if data.get("status") != "qr_ready":
        return Response(status_code=204)

    qr_text = data.get("qr")

    if not qr_text:
        return Response(status_code=204)

    img = qrcode.make(qr_text)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")

@router.get("/dashboard/whatsapp_status")
def whatsapp_status(seller = Depends(get_current_seller)):

    resp = requests.get(f"https://ton-service-node.onrender.com/status/{seller.id}")

    return resp.json()

# sans claude
'''@router.get("/dashboard/messages", response_class=HTMLResponse)
def messages_page(
    request: Request,
    client: str = None,
    seller = Depends(require_active_subscription)
):

    session = SessionLocal()

    # 🔥 marquer tous les messages comme vus
    session.query(Message)\
        .filter(
            Message.seller_id == seller.id,
            Message.seen == False,
            ~Message.message.startswith("BOT:")
        )\
        .update({"seen": True})

    session.commit()

    clients = session.query(Message.client_numero)\
        .filter(Message.seller_id == seller.id)\
        .distinct()\
        .all()

    clients = [c[0] for c in clients]

    messages = []

    if client:
        messages = session.query(Message)\
            .filter(
                Message.seller_id == seller.id,
                Message.client_numero == client
            )\
            .order_by(Message.id.asc())\
            .all()

    session.close()

    return templates.TemplateResponse(
        "messages.html",
        {
            "request": request,
            "clients": clients,
            "messages": messages,
            "selected_client": client
        }
    )'''
from sqlalchemy import func

@router.get("/dashboard/messages", response_class=HTMLResponse)
def messages_page(
    request: Request,
    client: str = None,
    seller = Depends(require_active_subscription)
):
    session = SessionLocal()

    # 🔥 marquer les messages du client sélectionné comme vus
    if client:
        session.query(Message)\
            .filter(
                Message.seller_id == seller.id,
                Message.client_numero == client,
                Message.seen == False,
                ~Message.message.startswith("BOT:")
            )\
            .update({"seen": True})
        session.commit()

    # 🔥 récupérer les clients avec infos enrichies
    client_numeros = session.query(Message.client_numero)\
        .filter(Message.seller_id == seller.id)\
        .distinct()\
        .all()

    clients_data = []

    for (numero,) in client_numeros:

        # dernier message
        last_msg = session.query(Message)\
            .filter(
                Message.seller_id == seller.id,
                Message.client_numero == numero
            )\
            .order_by(Message.id.desc())\
            .first()

        # nombre de messages non lus
        unread_count = session.query(Message)\
            .filter(
                Message.seller_id == seller.id,
                Message.client_numero == numero,
                Message.seen == False,
                ~Message.message.startswith("BOT:")
            ).count()

        clients_data.append({
            "numero": numero,
            "last_message": last_msg.message if last_msg else "",
            "last_date": last_msg.created_at if last_msg else None,
            "unread": unread_count
        })

    # 🔥 trier par date du dernier message (plus récent en premier)
    clients_data.sort(
        key=lambda x: x["last_date"] or datetime.min,
        reverse=True
    )

    messages = []

    if client:
        messages = session.query(Message)\
            .filter(
                Message.seller_id == seller.id,
                Message.client_numero == client
            )\
            .order_by(Message.id.asc())\
            .all()

    session.close()

    return templates.TemplateResponse(
        "messages.html",
        {
            "request": request,
            "clients_data": clients_data,  # 🔥 nouveau
            "messages": messages,
            "selected_client": client
        }
    )

@router.get("/dashboard/orders", response_class=HTMLResponse)
def orders_page(request: Request, seller = Depends(require_active_subscription)):

    session = SessionLocal()

    # 🔥 marquer toutes les commandes comme vues
    session.query(Order)\
        .filter(
            Order.seller_id == seller.id,
            Order.seen == False
        )\
        .update({"seen": True})

    session.commit()

    orders = session.query(Order)\
        .filter(Order.seller_id == seller.id)\
        .order_by(Order.date.desc())\
        .all()

    confirmed = session.query(Order)\
        .filter(Order.seller_id == seller.id, Order.statut == "Confirmée")\
        .count()

    delivery = session.query(Order)\
        .filter(Order.seller_id == seller.id, Order.statut == "En livraison")\
        .count()

    delivered = session.query(Order)\
        .filter(Order.seller_id == seller.id, Order.statut == "Livrée")\
        .count()

    session.close()

    return templates.TemplateResponse(
        "orders.html",
        {
            "request": request,
            "orders": orders,
            "confirmed": confirmed,
            "delivery": delivery,
            "delivered": delivered
        }
    )

@router.post("/dashboard/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    status: str = Form(...),
    seller = Depends(require_active_subscription)
):

    session = SessionLocal()

    order = session.query(Order)\
        .filter(
            Order.id == order_id,
            Order.seller_id == seller.id
        )\
        .first()

    order.statut = status

    session.commit()
    session.close()

    return RedirectResponse("/dashboard/orders", status_code=303)

# ne prend pas en compte l'abonnement de sept jours
'''@router.get("/api/check-subscription/{seller_id}")
def check_subscription(seller_id: int):

    session = SessionLocal()

    sub = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller_id,
            Subscription.status == "active"
        )\
        .order_by(Subscription.id.desc())\
        .first()

    session.close()

    if not sub or sub.end_date < datetime.utcnow():
        return {"active": False}

    return {"active": True}'''
@router.get("/api/check_subscription/{seller_id}")
def check_subscription(seller_id: int):

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.id == seller_id)\
        .first()

    # 🔥 1. FREE TRIAL (7 jours)
    if seller and seller.created_at:
        trial_end = seller.created_at + timedelta(days=7)

        if datetime.utcnow() < trial_end:
            session.close()
            return {"active": True}

    # 🔥 2. ABONNEMENT
    sub = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller_id,
            Subscription.status == "active"
        )\
        .order_by(Subscription.id.desc())\
        .first()

    session.close()

    if sub and sub.end_date > datetime.utcnow():
        return {"active": True}

    return {"active": False}

@router.get("/api/notifications")
def get_notifications(seller = Depends(get_current_seller)):

    session = SessionLocal()

    new_orders = session.query(Order)\
        .filter(
            Order.seller_id == seller.id,
            Order.seen == False
        ).count()

    # 🔥 récupérer les clients avec messages non lus
    unread_clients = session.query(Message.client_numero)\
        .filter(
            Message.seller_id == seller.id,
            Message.seen == False,
            ~Message.message.startswith("BOT:")
        ).distinct().all()

    unread_clients = [c[0] for c in unread_clients]

    new_messages = len(unread_clients)

    session.close()

    return {
        "orders": new_orders,
        "messages": new_messages,
        "unread_clients": unread_clients  # 🔥 liste des clients non lus
    }

@router.post("/dashboard/context_note")
def save_context_note(
    note: str = Form(...),
    seller = Depends(get_current_seller)
):
    session = SessionLocal()
    seller_db = session.query(Seller).filter(Seller.id == seller.id).first()
    seller_db.context_note = note.strip() or None
    session.commit()
    session.close()
    return RedirectResponse("/dashboard/settings", status_code=303)

@router.post("/dashboard/context_note/clear")
def clear_context_note(seller = Depends(get_current_seller)):
    session = SessionLocal()
    seller_db = session.query(Seller).filter(Seller.id == seller.id).first()
    seller_db.context_note = None
    session.commit()
    session.close()
    return RedirectResponse("/dashboard/settings", status_code=303)


@router.get("/dashboard/stats", response_class=HTMLResponse)
def stats_page(request: Request, seller = Depends(require_active_subscription)):

    session = SessionLocal()

    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # 🔥 Total commandes
    total_orders = session.query(Order)\
        .filter(Order.seller_id == seller.id).count()

    # 🔥 Commandes aujourd'hui
    orders_today = session.query(Order)\
        .filter(
            Order.seller_id == seller.id,
            func.date(Order.date) == today
        ).count()

    # 🔥 Commandes cette semaine
    orders_week = session.query(Order)\
        .filter(
            Order.seller_id == seller.id,
            Order.date >= week_ago
        ).count()

    # 🔥 Commandes ce mois
    orders_month = session.query(Order)\
        .filter(
            Order.seller_id == seller.id,
            Order.date >= month_ago
        ).count()

    # 🔥 Commandes par statut
    orders_confirmed = session.query(Order)\
        .filter(Order.seller_id == seller.id, Order.statut == "Confirmée").count()
    orders_delivery = session.query(Order)\
        .filter(Order.seller_id == seller.id, Order.statut == "En livraison").count()
    orders_delivered = session.query(Order)\
        .filter(Order.seller_id == seller.id, Order.statut == "Livrée").count()
    orders_cancelled = session.query(Order)\
        .filter(Order.seller_id == seller.id, Order.statut == "Annulée").count()

    # 🔥 Produit le plus commandé
    top_products = session.query(
        Order.produit,
        func.count(Order.id).label("count")
    ).filter(Order.seller_id == seller.id)\
     .group_by(Order.produit)\
     .order_by(func.count(Order.id).desc())\
     .limit(5)\
     .all()

    # 🔥 Messages total et aujourd'hui
    total_messages = session.query(Message)\
        .filter(Message.seller_id == seller.id).count()

    messages_today = session.query(Message)\
        .filter(
            Message.seller_id == seller.id,
            func.date(Message.created_at) == today,
            ~Message.message.startswith("BOT:")
        ).count()

    # 🔥 Nombre de clients uniques
    unique_clients = session.query(Message.client_numero)\
        .filter(Message.seller_id == seller.id)\
        .distinct().count()

    # 🔥 Taux de conversion (messages → commandes)
    conversion_rate = 0
    if unique_clients > 0:
        conversion_rate = round((total_orders / unique_clients) * 100, 1)

    # 🔥 Commandes des 7 derniers jours (pour le graphique)
    orders_by_day = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        count = session.query(Order)\
            .filter(
                Order.seller_id == seller.id,
                func.date(Order.date) == day.date()
            ).count()
        orders_by_day.append({
            "day": day.strftime("%d/%m"),
            "count": count
        })

    # 🔥 Messages des 7 derniers jours (pour le graphique)
    messages_by_day = []
    for i in range(6, -1, -1):
        day = now - timedelta(days=i)
        count = session.query(Message)\
            .filter(
                Message.seller_id == seller.id,
                func.date(Message.created_at) == day.date(),
                ~Message.message.startswith("BOT:")
            ).count()
        messages_by_day.append({
            "day": day.strftime("%d/%m"),
            "count": count
        })

    session.close()

    return templates.TemplateResponse(
        "stats.html",
        {
            "request": request,
            "seller": seller,
            "total_orders": total_orders,
            "orders_today": orders_today,
            "orders_week": orders_week,
            "orders_month": orders_month,
            "orders_confirmed": orders_confirmed,
            "orders_delivery": orders_delivery,
            "orders_delivered": orders_delivered,
            "orders_cancelled": orders_cancelled,
            "top_products": top_products,
            "total_messages": total_messages,
            "messages_today": messages_today,
            "unique_clients": unique_clients,
            "conversion_rate": conversion_rate,
            "orders_by_day": orders_by_day,
            "messages_by_day": messages_by_day,
        }
    )
