from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import uuid
from auth.dependencies import get_current_seller
from database import SessionLocal
from models.product import Product
from fastapi import UploadFile, File, Form
import shutil
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="/dashboard/products")

templates = Jinja2Templates(directory="templates")

@router.get("/", response_class=HTMLResponse)
def list_products(request: Request, seller = Depends(get_current_seller)):

    session = SessionLocal()

    products = session.query(Product).filter(Product.seller_id == seller.id).all()

    return templates.TemplateResponse(
        "products.html",
        {
            "request": request,
            "products": products
        }
    )

@router.get("/new", response_class=HTMLResponse)
def new_product_page(request: Request, seller = Depends(get_current_seller)):

    return templates.TemplateResponse(
        "new_product.html",
        {"request": request}
    )

@router.post("/new")
def create_product(
    name: str = Form(...),
    price: int = Form(...),
    image: UploadFile = File(...),
    seller = Depends(get_current_seller)
):

    session = SessionLocal()

    unique_id = uuid.uuid4().hex
    filename = f"{unique_id}_{image.filename}"

    filepath = f"uploads/{filename}"

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)

    product = Product(
        name=name,
        price=price,
        image=filepath,
        seller_id=seller.id
    )

    session.add(product)
    session.commit()

    return RedirectResponse("/dashboard/products", status_code=303)

@router.get("/delete/{product_id}")
def delete_product(product_id: int, seller = Depends(get_current_seller)):

    session = SessionLocal()

    product = session.query(Product).filter(
        Product.id == product_id,
        Product.seller_id == seller.id
    ).first()

    if product:
        session.delete(product)
        session.commit()

    return RedirectResponse("/dashboard/products", status_code=303)


@router.get("/edit/{product_id}", response_class=HTMLResponse)
def edit_product_page(
    request: Request,
    product_id: int,
    seller = Depends(get_current_seller)
):

    session = SessionLocal()

    product = session.query(Product).filter(
        Product.id == product_id,
        Product.seller_id == seller.id
    ).first()

    return templates.TemplateResponse(
        "edit_product.html",
        {
            "request": request,
            "product": product
        }
    )


@router.post("/edit/{product_id}")
def update_product(
    product_id: int,
    name: str = Form(...),
    price: int = Form(...),
    seller = Depends(get_current_seller)
):

    session = SessionLocal()

    product = session.query(Product).filter(
        Product.id == product_id,
        Product.seller_id == seller.id
    ).first()

    if product:
        product.name = name
        product.price = price
        session.commit()

    return RedirectResponse("/dashboard/products", status_code=303)