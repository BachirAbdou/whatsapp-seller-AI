from fastapi import APIRouter, Form, Request
from database import SessionLocal
from models.seller import Seller
from auth.security import hash_password
from auth.security import verify_password, create_access_token
from fastapi.responses import RedirectResponse
from fastapi import Request
from fastapi.templating import Jinja2Templates
from slugify import slugify
from PIL import Image, ImageDraw
from io import BytesIO
from models.soubscription import Subscription
from models.seller import Seller
from datetime import datetime, timedelta
import secrets
from services.email_service import send_verification_email, send_reset_email

login_attempts = {}

router = APIRouter()

templates = Jinja2Templates(directory="templates")

def is_login_blocked(email):

    data = login_attempts.get(email)

    if not data:
        return False

    attempts = data["attempts"]
    last_try = data["time"]

    if attempts >= 5:

        if datetime.utcnow() - last_try < timedelta(minutes=10):
            return True

        else:
            # reset après 10 minutes
            login_attempts[email] = {"attempts": 0, "time": datetime.utcnow()}
            return False

    return False

@router.post("/register")
def register(
    request: Request,
    name: str = Form(...),
    assistant_name: str = Form(...),   # ✅ ajouté
    email: str = Form(...),
    password: str = Form(...)
):

    session = SessionLocal()

    # normaliser email
    email = email.lower().strip()

    token = secrets.token_urlsafe(32)

    # mot de passe minimum
    if len(password) < 10:
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Mot de passe trop court (10 caractères minimum)"
            }
        )

    # ✅ valeur par défaut si vide
    assistant_name = assistant_name or "Assistant"

    existing = session.query(Seller).filter(Seller.email == email).first()

    if existing:
        session.close()
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "error": "Un compte avec ce email existe déjà"
            }
        )

    # 🔹 génération du slug
    base_slug = slugify(name)
    slug = base_slug
    i = 1

    while session.query(Seller).filter(Seller.slug == slug).first():
        slug = f"{base_slug}-{i}"
        i += 1

    seller = Seller(
        name=name,
        assistant_name=assistant_name,
        email=email,
        password_hash=hash_password(password),
        slug=slug,
        email_token=token
    )

    session.add(seller)
    session.commit()
    session.refresh(seller)

    # send_verification_email(email, token)

    trial = Subscription(
        seller_id=seller.id,
        plan="trial",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=7),
        status="active"
    )

    session.add(trial)
    session.commit()

    # ✅ envoyer email après commit
    try:
        send_verification_email(email, token)
    except Exception as e:
        print("Erreur email:", e)

    session.close()

    response = RedirectResponse("/login?check_email=1", status_code=303)

    # on met ça quand pas validation mail
    '''response.set_cookie(
        key="seller_id",
        value=str(seller.id),
        httponly=True,
        secure=True,
        samesite="lax"
    )'''

    session.close()

    return response

@router.get("/verify-email/{token}")
def verify_email(token: str):

    session = SessionLocal()

    seller = session.query(Seller)\
        .filter(Seller.email_token == token)\
        .first()

    if not seller:
        session.close()
        return {"error": "Token invalide"}

    seller.email_verified = True
    seller.email_token = None

    session.commit()
    session.close()

    BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
    return RedirectResponse(f"{BASE_URL}/login?verified=1", status_code=303)

@router.get("/login")
def login_page(request: Request):

    return templates.TemplateResponse(
        "login.html",
        {"request": request}
    )

@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):

    session = SessionLocal()

    email = email.lower().strip()

    # vérifier blocage
    if is_login_blocked(email):

        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Trop de tentatives. Réessayez dans 10 minutes."
            }
        )

    seller = session.query(Seller).filter(Seller.email == email).first()

    if not seller:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Compte introuvable"}
        )

    if not seller.email_verified:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Veuillez vérifier votre email"
            }
        )

    if not seller or not verify_password(password, seller.password_hash):

        # 🔴 enregistrer tentative échouée
        data = login_attempts.get(email, {"attempts": 0})

        login_attempts[email] = {
            "attempts": data["attempts"] + 1,
            "time": datetime.utcnow()
        }

        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Email ou mot de passe incorrect"}
        )
    
    # 🔒 vérification approbation (sauf admin)
    if seller.role.lower() not in ["admin", "superadmin"] and not seller.is_approved:
        response = RedirectResponse("/pending-approval", status_code=303)

        response.set_cookie(
            key="seller_id",
            value=str(seller.id),
            httponly=True,
            secure=True,
            samesite="lax"
        )

        return response

    # 🟢 login réussi → reset tentatives
    if email in login_attempts:
        del login_attempts[email]

    # redirection selon le rôle
    #if seller.role == "admin":
    #    redirect_url = "/admin"
    #else:
    #    redirect_url = "/dashboard"
    redirect_url = "/admin" if seller.role in ["admin", "superadmin"] else "/dashboard"

    response = RedirectResponse(redirect_url, status_code=303)

    response.set_cookie(
        key="seller_id",
        value=str(seller.id),
        httponly=True,
        secure=True,
        samesite="lax"
    )

    return response


@router.get("/register")
def register_page(request: Request):

    return templates.TemplateResponse(
        "register.html",
        {"request": request}
    )

@router.get("/forgot-password")
def forgot_password_page(request: Request):
    return templates.TemplateResponse(
        "forgot_password.html",
        {"request": request}
    )

@router.get("/logout")
def logout():

    response = RedirectResponse(url="/login")

    response.delete_cookie("seller_id")

    return response


@router.post("/forgot-password")
def forgot_password(request: Request, email: str = Form(...)):

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.email == email).first()

    if seller:
        token = secrets.token_urlsafe(32)

        seller.reset_token = token
        seller.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)

        session.commit()

        # 🔥 lien reset
        reset_link = f"http://localhost:8000/reset-password/{token}"

        try:
            send_reset_email(email, reset_link)  # tu peux adapter
        except Exception as e:
            print(e)

    session.close()

    return templates.TemplateResponse(
        "forgot_password.html",
        {
            "request": request,
            "message": "Si cet email existe, un lien a été envoyé"
        }
    )

@router.get("/reset-password/{token}")
def reset_password_page(request: Request, token: str):

    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "token": token
        }
    )

@router.post("/reset-password")
def reset_password(
    request: Request,
    token: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...)
):
    session = SessionLocal()
    seller = session.query(Seller).filter(Seller.reset_token == token).first()

    if not seller:
        session.close()
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "error": "Token invalide", "token": token}
        )

    if seller.reset_token_expiry < datetime.utcnow():
        session.close()
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "error": "Token expiré", "token": token}
        )

    if password != confirm_password:
        session.close()
        return templates.TemplateResponse(
            "reset_password.html",
            {"request": request, "error": "Les mots de passe ne correspondent pas", "token": token}
        )

    seller.password_hash = hash_password(password)
    seller.reset_token = None
    seller.reset_token_expiry = None
    session.commit()
    session.close()

    return templates.TemplateResponse(
        "reset_password.html",
        {"request": request, "success": "Mot de passe changé avec succès ! Vous allez être redirigé.", "token": ""}
    )

'''
@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...)
):

    session = SessionLocal()

    seller = session.query(Seller).filter(Seller.email == email).first()

    if not seller:
        return {"error": "Utilisateur introuvable"}

    if not verify_password(password, seller.password_hash):
        return {"error": "Mot de passe incorrect"}

    token = create_access_token({"seller_id": seller.id})

    session.close()

    return {
        "access_token": token,
        "token_type": "bearer"
    }'''
