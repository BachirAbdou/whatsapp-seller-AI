from fastapi import Request
from starlette.responses import RedirectResponse

from database import SessionLocal
from services.subscription_service import seller_has_active_subscription


async def subscription_required(request: Request, call_next):

    public_routes = [
        "/",
        "/login",
        "/register",
        "/static",
        "/uploads",
        "/pricing",                     # ← page pricing accessible
        "/subscribe/declare-payment",   # ← permettre de déclarer un paiement
        "/pending-approval",            # ← page d'attente
        "/api/notifications",           # ← badges sidebar
        "/dashboard/whatsapp_status",   # ← status whatsapp
    ]

    if request.url.path.startswith(tuple(public_routes)):
        return await call_next(request)

    seller_id = request.cookies.get("seller_id")

    if seller_id is None:
        return RedirectResponse("/login")

    seller_id = int(seller_id)

    session = SessionLocal()
    has_subscription = seller_has_active_subscription(session, seller_id)
    session.close()

    if not has_subscription:
        return RedirectResponse("/pricing")

    response = await call_next(request)
    return response