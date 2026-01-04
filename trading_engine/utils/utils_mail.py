import os
import smtplib
import logging
from pathlib import Path
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# Configuración básica de logging
logger = logging.getLogger(__name__)

def send_email(subject, body, to_email, attachment_path=None, config_path=None):
    """
    Función dinámica para enviar correos usando una configuración inyectada.
    """
    
    # 🎯 PASO 1: Carga de configuración dinámica
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            load_dotenv(config_file, override=True) # override=True asegura que use estas credenciales
        else:
            logger.warning(f"⚠️ Archivo de configuración de mail no encontrado en: {config_path}")
    
    from_email = os.environ.get("GMAIL_USER")
    from_password = os.environ.get("GMAIL_PASS")
    
    if not from_email or not from_password:
        logger.error("Error: Credenciales GMAIL_USER o GMAIL_PASS no encontradas en el entorno.")
        return

    # --- Manejo de destinatarios (Tu lógica actual, que es buena) ---
    if isinstance(to_email, str):
        recipient_list = [email.strip() for email in to_email.split(',')]
    elif isinstance(to_email, list):
        recipient_list = to_email
    else:
        logger.error(f"Formato de destinatario no válido: {type(to_email)}")
        return
        
    to_header = ", ".join(recipient_list)

    # --- Construcción del mensaje ---
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_header
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # --- Manejo de adjuntos ---
    if attachment_path and os.path.isfile(attachment_path):
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(attachment_path)}')
            msg.attach(part)
        except Exception as e:
            logger.error(f"No se pudo adjuntar el archivo: {e}")
    
    # --- Envío vía SMTP ---
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, from_password)
        server.sendmail(from_email, recipient_list, msg.as_string())
        server.quit()
        logger.info(f"✅ Correo enviado a {to_header} exitosamente.")
    except Exception as e:
        logger.error(f"❌ Error al enviar correo: {e}")