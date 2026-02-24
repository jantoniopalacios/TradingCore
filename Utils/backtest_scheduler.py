import sys
from pathlib import Path
from flask import Flask
import json

# Añadir el directorio raíz del proyecto al sys.path
project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from scenarios.BacktestWeb.Backtest import ejecutar_backtest
from scenarios.BacktestWeb.database import Usuario
from scenarios.BacktestWeb.database import db


app = Flask(__name__)
# Configuración de conexión a PostgreSQL (igual que en el sistema principal)
DB_USER = "postgres"
DB_PASS = "admin"
DB_HOST = "localhost"
DB_PORT = "5433"
DB_NAME = "trading_db"
DATABASE_URL = f"postgresql+pg8000://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
db.init_app(app)

def ejecutar_backtests_usuarios():
    with app.app_context():
        usuarios = Usuario.query.all()
        for usuario in usuarios:
            config = {}
            if usuario.config_actual:
                try:
                    config = json.loads(usuario.config_actual)
                except Exception as e:
                    print(f"Error parsing config_actual for {usuario.username}: {e}")
            enviar_mail = config.get('enviar_mail', False)
            destinatario_email = config.get('destinatario_email', None)
            print(f"Usuario: {usuario.username}, enviar_mail: {enviar_mail}, destinatario_email: {destinatario_email}")
            if (
                str(enviar_mail).lower() in ['true', '1', 'yes']
                or enviar_mail is True
                or enviar_mail == 1
            ) and destinatario_email and str(destinatario_email).strip():
                print(f"--> Ejecutando backtest para {usuario.username}")
                config_dict = {
                    'user_mode': usuario.username,
                    'enviar_mail': True,
                    'destinatario_email': destinatario_email,
                }
                ejecutar_backtest(config_dict)

if __name__ == "__main__":
    ejecutar_backtests_usuarios()
