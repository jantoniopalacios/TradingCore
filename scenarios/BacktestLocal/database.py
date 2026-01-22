# database.py

"""
Docstring for scenarios.BacktestWeb.database
Este módulo define las tablas de la base de datos para la aplicación de backtesting web.
Incluye las tablas para usuarios, resultados de backtesting, trades detallados y símbolos.  
Cada tabla está diseñada para almacenar información relevante y facilitar la gestión de datos en la aplicación.
#  --- TABLAS DEFINIDAS ---
# 1. Tabla de Usuarios
# 2. Tabla de Resultados de Backtest
# 3. Tabla de Trades Detallados
# 4. Tabla de Símbolos
# Cada tabla incluye comentarios detallados sobre su propósito y estructura.
# En resumen, este módulo es esencial para la gestión de datos en la aplicación de backtesting web.
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Inicializamos el objeto de la base de datos
db = SQLAlchemy()



"""#  --- TABLA DE USUARIOS ---
# Esta tabla almacena la información de los usuarios que utilizan la aplicación
# Incluye campos para el nombre de usuario y la contraseña
# Permite la gestión de múltiples usuarios en la plataforma
# Cada usuario puede tener múltiples resultados de backtesting asociados
# Facilita la autenticación y autorización de los usuarios
# Mejora la organización y gestión de los datos de los usuarios
# En resumen, esta tabla es esencial para manejar la información de los usuarios en la aplicación
# """
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    
    # Relación: Un usuario tiene muchos resultados de backtesting
    resultados = db.relationship('ResultadoBacktest', backref='propietario', lazy=True)


"""#  --- TABLA DE RESULTADOS DE BACKTEST ---
# Esta tabla almacena los resultados de cada backtest realizado por los usuarios
# Incluye métricas clave para evaluar el rendimiento de la estrategia
# También guarda la configuración global utilizada en el backtest
# Permite flexibilidad para almacenar parámetros específicos de la estrategia
# Además, incluye campos para observaciones y gráficos generados
# Cada resultado está vinculado a un usuario específico
# Facilita el análisis y comparación de diferentes estrategias y configuraciones
# Mejora la organización y gestión de los datos de backtesting
# En resumen, esta tabla es esencial para almacenar y analizar los resultados de los backtests realizados por los usuarios
#  """
class ResultadoBacktest(db.Model):
    __tablename__ = 'resultados_backtest'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)

    # Un número entero que identifica la tanda (ej: 1, 2, 3...)
    id_estrategia = db.Column(db.Integer, nullable=False)

    # 1. METRICAS (Fijas para poder comparar)
    symbol = db.Column(db.String(10), nullable=False)
    sharpe_ratio = db.Column(db.Float)
    max_drawdown = db.Column(db.Float)
    profit_factor = db.Column(db.Float)
    return_pct = db.Column(db.Float)
    total_trades = db.Column(db.Integer)
    win_rate = db.Column(db.Float)
    sortino_ratio = db.Column(db.Float, nullable=True) # Sugerencia
    expectancy = db.Column(db.Float, nullable=True)    # Sugerencia

    # 2. CONFIGURACION GLOBAL (Fijas)
    fecha_inicio_datos = db.Column(db.String(20))
    fecha_fin_datos = db.Column(db.String(20))
    intervalo = db.Column(db.String(10))
    cash_inicial = db.Column(db.Float)
    comision = db.Column(db.Float)
    enviar_mail = db.Column(db.Boolean, default=False)

    # 3. EL "CONTENEDOR" DE ESTRATEGIA (Flexibilidad total)
    # Aquí guardaremos el resto (RSI, Stoch, EMA, MACD, BB...) como un diccionario JSON
    params_tecnicos = db.Column(db.Text, nullable=True) 
    
    # 4. OBSERVACIONES Y GRÁFICOS
    notas = db.Column(db.Text, nullable=True)
    grafico_html = db.Column(db.Text, nullable=True)

    fecha_ejecucion = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación: Un backtest tiene muchos trades detallados
    trades = db.relationship('Trade', backref='backtest', cascade='all, delete-orphan')
"""
#  --- NUEVA TABLA DE TRADES DETALLADOS ---
# Esta tabla almacena los trades individuales realizados durante un backtest
# Cada trade está vinculado a un resultado de backtest específico
# Permite un análisis detallado del rendimiento de la estrategia
# Incluye información clave como tipo de trade, precios de entrada y salida, PnL
# Facilita la generación de reportes y estadísticas avanzadas
# Mejora la transparencia y comprensión del comportamiento de la estrategia
# En resumen, esta tabla es esencial para un análisis granular de los resultados del backtest
#
"""
class Trade(db.Model):
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True)
    backtest_id = db.Column(db.Integer, db.ForeignKey('resultados_backtest.id'), nullable=False)
    
    tipo = db.Column(db.String(20)) # COMPRA / VENTA
    descripcion = db.Column(db.String(255)) # Descripción del trade (ej: "Entrada por cruce de medias")
    fecha = db.Column(db.String(30))
    precio_entrada = db.Column(db.Float)
    precio_salida = db.Column(db.Float)
    pnl_absoluto = db.Column(db.Float)
    retorno_pct = db.Column(db.Float)

#  --- NUEVA TABLA DE SIMBOLOS ---
# Esta tabla almacena los símbolos que cada usuario quiere analizar
# Incluye los nuevos campos para la estrategia
# Permite gestionar múltiples símbolos por usuario
# Cada símbolo está vinculado a un usuario específico
# Así, cada usuario puede tener su propia lista de símbolos con configuraciones personalizadas
# Esto facilita la gestión y el análisis individualizado de cada símbolo
# Además, permite escalar fácilmente si se desea agregar más configuraciones en el futuro
# La relación con la tabla de usuarios asegura que cada símbolo esté asociado correctamente
# y permite acceder a los símbolos de un usuario de manera sencilla
# También facilita la eliminación en cascada si un usuario es eliminado
# Esto mejora la organización y la claridad de los datos en la base de datos
# En resumen, esta tabla es esencial para gestionar los símbolos y sus configuraciones de manera eficiente y personalizada por usuario
#
class Simbolo(db.Model):
    __tablename__ = 'simbolos'
    
    id = db.Column(db.Integer, primary_key=True)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    
    # --- NUEVOS CAMPOS DE ESTRATEGIA ---
    # Para decidir si el motor debe calcular el Full Ratio
    usar_full_ratio = db.Column(db.Boolean, default=True)
    
    # Para decidir si se deben buscar fundamentales (Alpha Vantage vs Yahoo)
    tiene_fundamentales = db.Column(db.Boolean, default=True)
    
    # --- RELACIÓN ---
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    
    # Relación inversa para acceder fácil: usuario.mis_simbolos
    propietario = db.relationship('Usuario', backref=db.backref('mis_simbolos', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self):
        return f'<Simbolo {self.symbol} (FR:{self.usar_full_ratio}, Fund:{self.tiene_fundamentales})>'