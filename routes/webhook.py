from fastapi import APIRouter, Form
from fastapi.responses import PlainTextResponse

router = APIRouter()

@router.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(...)):

    response = f"Message reçu : {Body}"

    return PlainTextResponse(response)