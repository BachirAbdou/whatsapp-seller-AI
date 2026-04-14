from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()

templates = Jinja2Templates(directory="templates")

@router.get("/pricing")
def pricing_page(request: Request):

    return templates.TemplateResponse(
        "pricing.html",
        {"request": request}
    )