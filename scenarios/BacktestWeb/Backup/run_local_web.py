# Importamos la función que crea la app desde el otro escenario
from ..BacktestWeb.app import create_app

# Creamos la instancia de la aplicación
app = create_app(user_mode="juantxu_local")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏠 MODO LOCAL: Iniciando réplica privada (localhost)")
    print("🔗 Acceso solo desde este PC: http://127.0.0.1:5000")
    print("="*60 + "\n")

    # La diferencia clave: host='127.0.0.1' y debug=True
    app.run(host='127.0.0.1', port=5000, debug=True)