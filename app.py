# app/main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from database import Base, engine
from database import SessionLocal
from models.seller import Seller
from middlewares.subscription_required import subscription_required
from fastapi import Request
from fastapi import FastAPI
from fastapi.exceptions import HTTPException

from routers import auth
from routers import dashboard
from routers import products
from routers import whatsapp
from routers import admin
from routers import pricing
from routers import settings 
from routers import soubscriptions
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):

    if exc.status_code == 401:
        return RedirectResponse("/login")

    if exc.status_code == 402:
        return RedirectResponse("/pending-approval")  # 👈 IMPORTANT

    if exc.status_code == 403:
        return RedirectResponse("/pricing?expired=true")

    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse("/login")

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# templates HTML
templates = Jinja2Templates(directory="templates")

# homepage
#@app.get("/", response_class=HTMLResponse)
#def home(request: Request):
#    return templates.TemplateResponse("home.html", {"request": request})
@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    seller_id = request.cookies.get("seller_id")

    if seller_id:

        session = SessionLocal()
        seller = session.query(Seller).filter(Seller.id == seller_id).first()
        session.close()

        if seller:
            return RedirectResponse("/dashboard")

    return templates.TemplateResponse(
        "home.html",
        {"request": request}
    )

# routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(products.router)
app.include_router(whatsapp.router)
app.include_router(settings.router)

app.include_router(admin.router)

app.include_router(pricing.router)

app.include_router(soubscriptions.router)

app.include_router(admin.router) 

app.include_router(auth.router) 

app.middleware("http")(subscription_required)

# fichiers statiques
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# création tables
Base.metadata.create_all(bind=engine)


'''from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from openai import OpenAI
from dotenv import load_dotenv
from models import seller, product, order
from models.product import Product
from models.seller import Seller
from models.order import Order
from models.message import Message
from services.ai_service import detect_order
from fastapi.responses import RedirectResponse
from database import SessionLocal, Base, engine
from datetime import datetime
from routers import auth
from routers import dashboard
from routers import products
from fastapi.staticfiles import StaticFiles
import os

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(products.router)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory="templates")

# --- Webhook Twilio ---
VENDEUR_SLUGS = {
    "boutiqueA": 1,
    "boutiqueB": 2
}

def generate_response(message, catalogue):
    prompt = f"""
Tu es un assistant WhatsApp pour un vendeur.

Catalogue produits :
{catalogue}

Règles :
- Réponds de façon courte et claire
- Sois poli et professionnel
- Si le client veut commander, demande son nom et son adresse
- Si la question concerne prix ou disponibilité, utilise le catalogue

Message client :
{message}
"""
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

@app.post("/whatsapp/{slug}")
async def whatsapp_webhook(
    slug: str,
    Body: str = Form(...),
    From: str = Form(...),
    ProfileName: str = Form(...)
):

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.slug == slug).first()

    if not seller:
        return PlainTextResponse("Boutique introuvable")

    vendeur_id = seller.id

    # sauvegarder message
    msg = Message(
        seller_id=vendeur_id,
        client_numero=From,
        message=Body
    )

    session.add(msg)
    session.commit()

    # Charger catalogue du vendeur
    produits = session.query(Product).filter(Product.seller_id == vendeur_id).all()
    catalogue = "\n".join([f"{p.name} - {p.price}" for p in produits]) or "Aucun produit enregistré."

    # Détection commande
    order_data = detect_order(Body, catalogue)

    if order_data.get("order_detected") and order_data.get("items"):

        for item in order_data["items"]:

            order = Order(
                seller_id=vendeur_id,
                client_nom=ProfileName,
                client_numero=From,
                produit=item["product"],
                adresse="À compléter",
                statut="En attente",
                date=datetime.now()
            )

            session.add(order)

        session.commit()

        response = "Votre commande est enregistrée. Pouvez-vous envoyer votre adresse de livraison ?"

    else:

        response = generate_response(Body, catalogue)

    session.close()
    return PlainTextResponse(response)

@app.post("/update_status/{order_id}")
def update_status(order_id: int, status: str = Form(...)):

    session = SessionLocal()

    order = session.query(Order).filter(Order.id == order_id).first()

    if order:
        order.statut = status
        session.commit()

    seller_id = order.seller_id if order else 1

    session.close()

    return RedirectResponse(url=f"/dashboard/{seller_id}", status_code=303)

@app.get("/products/{seller_id}", response_class=HTMLResponse)
def products_page(request: Request, seller_id: int):

    session = SessionLocal()

    products = session.query(Product).filter(Product.seller_id == seller_id).all()

    session.close()

    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "products": products,
            "seller_id": seller_id
        }
    )

@app.post("/add_product/{seller_id}")
def add_product(
    seller_id: int,
    name: str = Form(...),
    price: str = Form(...),
    description: str = Form("")
):

    session = SessionLocal()

    product = Product(
        seller_id=seller_id,
        name=name,
        price=price,
        description=description
    )

    session.add(product)
    session.commit()

    session.close()

    return RedirectResponse(url=f"/products/{seller_id}", status_code=303)

@app.post("/delete_product/{product_id}")
def delete_product(product_id: int):

    session = SessionLocal()

    product = session.query(Product).filter(Product.id == product_id).first()

    seller_id = product.seller_id if product else 1
    if product:
        session.delete(product)
        session.commit()

    #seller_id = product.seller_id

    #session.delete(product)
    #session.commit()

    session.close()

    return RedirectResponse(url=f"/products/{seller_id}", status_code=303)


@app.get("/")
def home(request: Request):

    seller_id = request.cookies.get("seller_id")

    if seller_id:
        return RedirectResponse("/dashboard")

    return RedirectResponse("/login")
    '''