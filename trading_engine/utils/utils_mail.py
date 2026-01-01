import os
import smtplib
import logging
from pathlib import Path
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

# --- CONFIGURACIÓN DE RUTA FIJA ---
# Definimos la ruta absoluta o relativa fija al servidor
# Si el script se ejecuta desde la raíz del proyecto (TradingCore), esta ruta es:
fichero_mail = Path("trading_engine/utils/Config/mail_setup.env")

# Carga las variables de entorno desde la ubicación fija
if fichero_mail.exists():
    load_dotenv(fichero_mail)
else:
    # Si prefieres una ruta absoluta para total seguridad:
    # fichero_mail = Path(r"C:\Users\juant\Proyectos\Python\TradingCore\trading_engine\utils\Config\mail_setup.env")
    print(f"⚠️ Alerta: No se encontró el archivo en {fichero_mail.absolute()}")

# Configuración básica de logging
logger = logging.getLogger(__name__)

def send_email(subject, body, to_email, attachment_path=None):
    """
    Función para enviar un correo electrónico con un archivo adjunto opcional.
    
    Args:
        subject (str): El asunto del correo electrónico.
        body (str): El cuerpo del mensaje de correo electrónico.
        to_email (str/list): Las direcciones de correo electrónico de los destinatarios. 
                             Puede ser una cadena (separada por comas) o una lista de cadenas.
        attachment_path (str, optional): La ruta al archivo a adjuntar. 
                                         Por defecto es None.
    """
    from_email = os.environ.get("GMAIL_USER")  # Usar .get() para evitar KeyError
    from_password = os.environ.get("GMAIL_PASS")
    
    if not from_email or not from_password:
        logger.error("Las variables de entorno GMAIL_USER o GMAIL_PASS no están configuradas.")
        print("Error: Las credenciales de correo no están configuradas en el archivo .env")
        return

    # 🌟 PASO CLAVE: Manejar múltiples destinatarios 🌟
    if isinstance(to_email, str):
        # Si es una cadena, la dividimos por comas (y limpiamos espacios) para obtener la lista final.
        recipient_list = [email.strip() for email in to_email.split(',')]
    elif isinstance(to_email, list):
        recipient_list = to_email
    else:
        logger.error(f"Formato de destinatario no válido: {type(to_email)}. Debe ser str o list.")
        return
        
    # Unir la lista para el encabezado 'To' (estético para el email)
    to_header = ", ".join(recipient_list)


    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_header  # ⬅️ Usamos la cadena separada por comas para el encabezado
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    if attachment_path and os.path.isfile(attachment_path):
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename= {os.path.basename(attachment_path)}')
            msg.attach(part)
        except Exception as e:
            logger.error(f"No se pudo adjuntar el archivo {attachment_path}: {e}")
            print(f"Error al adjuntar el archivo: {e}")
            # Se permite que el programa continúe, pero sin el adjunto
            attachment_path = None
    
    try:
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(from_email, from_password)
        text = msg.as_string()
        # ⬅️ Usamos la LISTA de destinatarios para la función sendmail()
        server.sendmail(from_email, recipient_list, text)
        server.quit()
        logger.info(f"Correo enviado a {to_header} desde {from_email}")
        print(f"Correo enviado a {to_header} desde {from_email}")
    except Exception as e:
        logger.error(f"Error al enviar correo: {e}")
        print(f"Error al enviar correo: {e}")