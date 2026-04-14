import smtplib
from email.mime.text import MIMEText
import os

def send_verification_email(to_email, token):

    link = f"http://127.0.0.1:8000/verify-email/{token}"

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f4f4f4; padding:20px;">
        
        <div style="max-width:500px; margin:auto; background:white; padding:30px; border-radius:10px;">
            
            <h2 style="color:#111;">
                Bienvenue 🚀
            </h2>

            <p style="color:#444;">
                Salut 👋,<br><br>

                Merci de t’être inscrit sur <strong>ton assistant WhatsApp</strong>.<br>
                Tu es à un pas de transformer tes messages en <strong>clients automatiquement</strong> 😎
            </p>

            <p style="color:#444;">
                👉 Ton assistant pourra :
                <br>• Répondre aux clients automatiquement  
                <br>• Présenter tes produits  
                <br>• Prendre des commandes 24h/24  
            </p>

            <p style="color:#444;">
                Pour commencer, il te suffit d’activer ton compte :
            </p>

            <div style="text-align:center; margin:30px 0;">
                <a href="{link}" 
                   style="
                        background:#6366f1;
                        color:white;
                        padding:12px 20px;
                        text-decoration:none;
                        border-radius:6px;
                        font-weight:bold;
                        display:inline-block;
                   ">
                    Activer mon compte
                </a>
            </div>

            <p style="color:#666;">
                ⏱️ Ça ne prend que quelques secondes.
            </p>

            <p style="color:#444;">
                Si tu n’as pas créé de compte, tu peux ignorer cet email sans problème.
            </p>

            <hr style="margin:25px 0; border:none; border-top:1px solid #eee;">

            <p style="color:#888; font-size:12px;">
                💡 Astuce : Une fois activé, connecte ton WhatsApp et laisse l’IA faire le travail pour toi.
            </p>

        </div>

    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = "Activez votre compte"
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(
            os.getenv("EMAIL"),
            os.getenv("EMAIL_PASSWORD")
        )

        server.send_message(msg)
        server.quit()

    except Exception as e:
        print("Erreur email:", e)



def send_reset_email(to_email, reset_link):
    """
    Envoie un email pour réinitialiser le mot de passe,
    avec un design similaire à l'email de vérification.
    """
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color:#f4f4f4; padding:20px;">
        
        <div style="max-width:500px; margin:auto; background:white; padding:30px; border-radius:10px;">
            
            <h2 style="color:#111;">
                Réinitialisation de votre mot de passe 🔒
            </h2>

            <p style="color:#444;">
                Salut 👋,<br><br>
                Nous avons reçu une demande pour réinitialiser le mot de passe associé à votre compte <strong>Whatsapp Seller</strong>.
            </p>

            <p style="color:#444;">
                Cliquez sur le bouton ci-dessous pour définir un nouveau mot de passe.  
                Ce lien expirera dans <strong>1 heure</strong>.
            </p>

            <div style="text-align:center; margin:30px 0;">
                <a href="{reset_link}" 
                   style="
                        background:#6366f1;
                        color:white;
                        padding:12px 20px;
                        text-decoration:none;
                        border-radius:6px;
                        font-weight:bold;
                        display:inline-block;
                   ">
                    Réinitialiser mon mot de passe
                </a>
            </div>

            <p style="color:#444;">
                Si vous n’avez pas demandé ce changement, ignorez simplement cet email.
            </p>

            <hr style="margin:25px 0; border:none; border-top:1px solid #eee;">

            <p style="color:#888; font-size:12px;">
                💡 Astuce : Une fois votre mot de passe réinitialisé, connectez-vous et continuez à utiliser votre assistant WhatsApp.
            </p>

        </div>

    </body>
    </html>
    """

    msg = MIMEText(html, "html")
    msg["Subject"] = "Réinitialisez votre mot de passe"
    msg["From"] = os.getenv("EMAIL")  # récupéré depuis .env
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        # identifiants cachés dans .env
        server.login(
            os.getenv("EMAIL"),
            os.getenv("EMAIL_PASSWORD")
        )

        server.send_message(msg)
        server.quit()

        print(f"Email de réinitialisation envoyé à {to_email}")

    except Exception as e:
        print("Erreur email:", e)

# pas jolie
'''def send_verification_email(to_email, token):

    link = f"http://127.0.0.1:8000/verify-email/{token}"

    msg = MIMEText(f"""
Cliquez pour activer votre compte :

{link}
""")

    msg["Subject"] = "Validation de votre compte"
    msg["From"] = os.getenv("EMAIL")
    msg["To"] = to_email

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(
            os.getenv("EMAIL"),
            os.getenv("EMAIL_PASSWORD")
        )

        server.send_message(msg)
        server.quit()

    except Exception as e:
        print("Erreur email:", e)'''