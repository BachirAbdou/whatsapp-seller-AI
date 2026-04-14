'''from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from database import SessionLocal
from models.product import Product
from models.order import Order
from models.message import Message
from models.seller import Seller
from models.pending_orders import PendingOrder
from services.ai_service import detect_order
from datetime import datetime
from openai import OpenAI
from pydantic import BaseModel
from services.subscription_service import seller_has_active_subscription
import os

router = APIRouter()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class WhatsAppMessage(BaseModel):
    Body: str
    From: str
    ProfileName: str


def generate_response(message, catalogue, seller, is_first_message=False):

    context_section = ""
    if seller.context_note:
        context_section = f"""
Note importante du vendeur (à intégrer naturellement dans tes réponses) :
{seller.context_note}
"""

    first_message_rule = ""
    if is_first_message:
        first_message_rule = f"""
🔴 RÈGLE IMPORTANTE — PREMIER MESSAGE :
C'est le tout premier message de ce client. Tu DOIS te présenter ainsi au début de ta réponse :
"Bonjour ! Je suis {seller.assistant_name}, l'assistante virtuelle de {seller.name} 🤖
Je réponds automatiquement aux messages — dites-moi comment je peux vous aider 😊"
Ensuite réponds normalement à sa question.
"""

    prompt = f"""
Tu es {seller.assistant_name}, assistante WhatsApp virtuelle du vendeur {seller.name}.

IDENTITÉ :
- Tu es un assistant IA, pas un humain
- Si le client demande si tu es un humain ou un robot → réponds honnêtement que tu es une assistante virtuelle
- Ne fais jamais semblant d'être le vendeur lui-même

Ton objectif : répondre comme un humain, de manière naturelle, chaleureuse et professionnelle.

Règles importantes :
- Ne dis PAS "le vendeur est occupé" sauf si on te le demande
- Ne dis PAS bonjour ou bonsoir à chaque message (sauf premier message)
- Sois direct, simple et agréable
- Évite les phrases longues
- Parle comme un humain (pas comme un robot)
- Ne te répète jamais
- Adapte ta réponse au message du client
- Si le client pose une question → réponds clairement
- Si le client veut un produit → sois commercial mais naturel

Style :
- Ton amical 😊
- Court et clair
- Pas trop formel
- Pas de phrases inutiles

{first_message_rule}

{context_section}

Catalogue produits :
{catalogue}

Message client :
{message}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


@router.post("/whatsapp/{seller_id}")
async def whatsapp_webhook(seller_id: int, data: WhatsAppMessage):

    Body = data.Body
    From = data.From
    ProfileName = data.ProfileName

    print("MESSAGE RECU FASTAPI:", Body)

    # 🔥 FILTRE NUMÉROS FAKE
    phone = From.split("@")[0]

    # 🔥 filtrer faux numéros
    if len(phone) > 15:
        print("Numéro invalide ignoré:", phone)
        return PlainTextResponse("")

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.id == seller_id).first()

    if not seller:
        session.close()
        return PlainTextResponse("")

    # 🔒 vérifier abonnement
    if not seller_has_active_subscription(session, seller.id):
        session.close()
        return PlainTextResponse("⚠️ Le vendeur doit renouveler son abonnement.")

    if not seller.ai_enabled:
        session.close()
        return PlainTextResponse("")

    vendeur_id = seller.id

    # sauvegarder message
    msg = Message(
        seller_id=vendeur_id,
        client_numero=From,
        message=Body
    )

    session.add(msg)
    session.commit()

    # récupérer catalogue
    produits = session.query(Product).filter(Product.seller_id == vendeur_id).all()

    catalogue = "\n".join([f"{p.name} - {p.price}" for p in produits]) or "Aucun produit."

    body_lower = Body.lower()

    identity_questions = [
    "qui es tu",
    "tu es qui",
    "qui me parle",
    "qui me répond"
    ]

    if any(q in body_lower for q in identity_questions):

        session.close()

        return PlainTextResponse(
            f"Je suis {seller.assistant_name}, l'assistant WhatsApp de {seller.name} 😊"
        )

    is_confirmation = Body.strip().lower() in [
        "oui",
        "je confirme",
        "1",
        "ok",
        "d'accord",
        "confirmer"
    ]

    # vérifier si une commande attend confirmation
    pending = session.query(PendingOrder)\
        .filter(
            PendingOrder.client_numero == From,
            PendingOrder.seller_id == vendeur_id,
            PendingOrder.status == "waiting_confirmation"
        )\
        .order_by(PendingOrder.id.desc())\
        .first()
    
        # ===============================
    # GESTION ADRESSE
    # ===============================

    order_waiting_address = session.query(Order)\
        .filter(
            Order.client_numero == From,
            Order.seller_id == vendeur_id,
            Order.adresse == None
        )\
        .order_by(Order.id.desc())\
        .first()

    if order_waiting_address and len(Body.strip()) > 8:

        order_waiting_address.adresse = Body
        order_waiting_address.statut = "En attente livraison"

        session.commit()
        session.close()

        return PlainTextResponse(
            "Adresse enregistrée ✅ Votre commande sera livrée bientôt."
        )

    # ===============================
    # CONFIRMATION COMMANDE
    # ===============================

    if is_confirmation and pending:

        order = Order(
            seller_id=vendeur_id,
            client_nom=ProfileName,
            client_numero=From,
            produit=pending.produit,
            adresse=None,
            statut="Confirmée",
            date=datetime.now()
        )

        # pending.status = "confirmed"
        session.delete(pending)

        session.add(order)
        session.commit()

        response = "✅ Commande confirmée ! Envoyez votre adresse pour la livraison."
        session.close()
        return PlainTextResponse(response)

    else:

        # détecter si message contient commande
        try:
            order_data = detect_order(Body, catalogue)
        except:
            order_data = {"order_detected": False}

        if order_data.get("order_detected"):

            product = order_data["items"][0]["product"]

            pending = PendingOrder(
                seller_id=vendeur_id,
                client_numero=From,
                produit=product,
                status="waiting_confirmation"
            )

            session.add(pending)
            session.commit()

            pending_msg = Message(
                seller_id=vendeur_id,
                client_numero=From,
                message=f"CONFIRMATION_PENDING:{product}"
            )

            session.add(pending_msg)
            session.commit()

            response = f"""
        Vous souhaitez commander :

        {product}

        Confirmez-vous la commande ?
        Répondez : oui je confirme
        """
        else:
            response = generate_response(Body, catalogue, seller)


    session.close()

    bot_msg = Message(
        seller_id=vendeur_id,
        client_numero=From,
        message="BOT:" + response
    )

    session.add(bot_msg)
    session.commit()
    session.close()

    return PlainTextResponse(response)'''


from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from database import SessionLocal
from models.product import Product
from models.order import Order
from models.message import Message
from models.seller import Seller
from models.pending_orders import PendingOrder
from services.ai_service import detect_order
from datetime import datetime
from openai import OpenAI
from pydantic import BaseModel
from services.subscription_service import seller_has_active_subscription
import os

router = APIRouter()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class WhatsAppMessage(BaseModel):
    Body: str
    From: str
    ProfileName: str


def generate_response(message, catalogue, seller, is_first_message=False):

    context_section = ""
    if seller.context_note:
        context_section = f"""
Note importante du vendeur (à intégrer naturellement dans tes réponses) :
{seller.context_note}
"""

    first_message_rule = ""
    if is_first_message:
        first_message_rule = f"""
🔴 RÈGLE IMPORTANTE — PREMIER MESSAGE :
C'est le tout premier message de ce client. Tu DOIS te présenter ainsi au début de ta réponse :
"Bonjour ! Je suis {seller.assistant_name}, l'assistante virtuelle de {seller.name} 🤖
Je réponds automatiquement aux messages — dites-moi comment je peux vous aider 😊"
Ensuite réponds normalement à sa question.
"""

    prompt = f"""
Tu es {seller.assistant_name}, assistante WhatsApp virtuelle du vendeur {seller.name}.

IDENTITÉ :
- Tu es un assistant IA, pas un humain
- Si le client demande si tu es un humain ou un robot → réponds honnêtement que tu es une assistante virtuelle
- Ne fais jamais semblant d'être le vendeur lui-même

Ton objectif : répondre comme un humain, de manière naturelle, chaleureuse et professionnelle.

Règles importantes :
- Ne dis PAS "le vendeur est occupé" sauf si on te le demande
- Ne dis PAS bonjour ou bonsoir à chaque message (sauf premier message)
- Sois direct, simple et agréable
- Évite les phrases longues
- Parle comme un humain (pas comme un robot)
- Ne te répète jamais
- Adapte ta réponse au message du client
- Si le client pose une question → réponds clairement
- Si le client veut un produit → sois commercial mais naturel

Style :
- Ton amical 😊
- Court et clair
- Pas trop formel
- Pas de phrases inutiles

{first_message_rule}

{context_section}

Catalogue produits :
{catalogue}

Message client :
{message}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


@router.post("/whatsapp/{seller_id}")
async def whatsapp_webhook(seller_id: int, data: WhatsAppMessage):

    Body = data.Body
    From = data.From
    ProfileName = data.ProfileName

    print("MESSAGE RECU FASTAPI:", Body)

    # 🔥 FILTRE NUMÉROS FAKE
    phone = From.split("@")[0]

    if len(phone) > 15:
        print("Numéro invalide ignoré:", phone)
        return PlainTextResponse("")

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.id == seller_id).first()

    if not seller:
        session.close()
        return PlainTextResponse("")

    # 🔒 vérifier abonnement
    if not seller_has_active_subscription(session, seller.id):
        session.close()
        return PlainTextResponse("⚠️ Le vendeur doit renouveler son abonnement.")

    if not seller.ai_enabled:
        session.close()
        return PlainTextResponse("")

    vendeur_id = seller.id

    # 🔥 vérifier si premier message du client (avant d'ajouter le nouveau)
    message_count = session.query(Message)\
        .filter(
            Message.seller_id == vendeur_id,
            Message.client_numero == From
        ).count()

    is_first_message = message_count == 0

    # sauvegarder message
    msg = Message(
        seller_id=vendeur_id,
        client_numero=From,
        message=Body
    )

    session.add(msg)
    session.commit()

    # récupérer catalogue
    produits = session.query(Product).filter(Product.seller_id == vendeur_id).all()

    catalogue = "\n".join([f"{p.name} - {p.price}" for p in produits]) or "Aucun produit."

    body_lower = Body.lower()

    identity_questions = [
        "qui es tu",
        "tu es qui",
        "qui me parle",
        "qui me répond"
    ]

    if any(q in body_lower for q in identity_questions):
        session.close()
        return PlainTextResponse(
            f"Je suis {seller.assistant_name}, l'assistant WhatsApp de {seller.name} 😊"
        )

    is_confirmation = Body.strip().lower() in [
        "oui",
        "je confirme",
        "1",
        "ok",
        "d'accord",
        "confirmer"
    ]

    # vérifier si une commande attend confirmation
    pending = session.query(PendingOrder)\
        .filter(
            PendingOrder.client_numero == From,
            PendingOrder.seller_id == vendeur_id,
            PendingOrder.status == "waiting_confirmation"
        )\
        .order_by(PendingOrder.id.desc())\
        .first()

    # ===============================
    # GESTION ADRESSE
    # ===============================

    order_waiting_address = session.query(Order)\
        .filter(
            Order.client_numero == From,
            Order.seller_id == vendeur_id,
            Order.adresse == None
        )\
        .order_by(Order.id.desc())\
        .first()

    if order_waiting_address and len(Body.strip()) > 8:

        order_waiting_address.adresse = Body
        order_waiting_address.statut = "En attente livraison"

        session.commit()
        session.close()

        return PlainTextResponse(
            "Adresse enregistrée ✅ Votre commande sera livrée bientôt."
        )

    # ===============================
    # CONFIRMATION COMMANDE
    # ===============================

    if is_confirmation and pending:

        order = Order(
            seller_id=vendeur_id,
            client_nom=ProfileName,
            client_numero=From,
            produit=pending.produit,
            adresse=None,
            statut="Confirmée",
            date=datetime.now()
        )

        session.delete(pending)
        session.add(order)
        session.commit()

        response = "✅ Commande confirmée ! Envoyez votre adresse pour la livraison."
        session.close()
        return PlainTextResponse(response)

    else:

        # détecter si message contient commande
        try:
            order_data = detect_order(Body, catalogue)
        except:
            order_data = {"order_detected": False}

        if order_data.get("order_detected"):

            product = order_data["items"][0]["product"]

            pending = PendingOrder(
                seller_id=vendeur_id,
                client_numero=From,
                produit=product,
                status="waiting_confirmation"
            )

            session.add(pending)
            session.commit()

            pending_msg = Message(
                seller_id=vendeur_id,
                client_numero=From,
                message=f"CONFIRMATION_PENDING:{product}"
            )

            session.add(pending_msg)
            session.commit()

            response = f"""Vous souhaitez commander :

{product}

Confirmez-vous la commande ?
Répondez : oui je confirme"""

        else:
            # 🔥 passer is_first_message à generate_response
            response = generate_response(Body, catalogue, seller, is_first_message)

    session.close()

    bot_msg = Message(
        seller_id=vendeur_id,
        client_numero=From,
        message="BOT:" + response
    )

    session.add(bot_msg)
    session.commit()
    session.close()

    return PlainTextResponse(response)