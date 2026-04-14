from openai import OpenAI
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def detect_order(message, catalogue):

    prompt = f"""
Catalogue produits :
{catalogue}

Analyse le message client.

Si c'est une commande retourne un JSON.

Format :

{{
 "order_detected": true,
 "items": [
   {{"product": "nom produit", "quantity": nombre}}
 ]
}}

Si ce n'est pas une commande :

{{"order_detected": false}}

Message client :
{message}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    text = response.choices[0].message.content

    try:
        return json.loads(text)
    except:
        return {"order_detected": False}