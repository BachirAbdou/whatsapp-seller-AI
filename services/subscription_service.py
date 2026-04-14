from datetime import datetime
from models.soubscription import Subscription
from models.seller import Seller

def seller_has_active_subscription(session, seller_id):

    seller = session.query(Seller).filter(Seller.id == seller_id).first()

    if not seller:
        return False

    # ✅ FREE TRIAL (7 jours)
    from datetime import timedelta
    if seller.created_at:
        trial_end = seller.created_at + timedelta(days=7)
        if datetime.utcnow() < trial_end:
            return True

    # ✅ CHECK ABONNEMENT
    sub = session.query(Subscription)\
        .filter(
            Subscription.seller_id == seller_id,
            Subscription.status == "active"
        )\
        .order_by(Subscription.id.desc())\
        .first()

    if not sub or sub.end_date < datetime.utcnow():
        return False

    return True