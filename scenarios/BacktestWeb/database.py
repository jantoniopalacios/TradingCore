# database.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Inicializamos el objeto de la base de datos
db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    
    # Relación: Un usuario tiene muchos resultados de backtesting
    resultados = db.relationship('ResultadoBacktest', backref='propietario', lazy=True)

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

class Trade(db.Model):
    __tablename__ = 'trades'
    id = db.Column(db.Integer, primary_key=True)
    backtest_id = db.Column(db.Integer, db.ForeignKey('resultados_backtest.id'), nullable=False)
    
    tipo = db.Column(db.String(20)) # COMPRA / VENTA
    fecha = db.Column(db.String(30))
    precio_entrada = db.Column(db.Float)
    precio_salida = db.Column(db.Float)
    pnl_absoluto = db.Column(db.Float)
    retorno_pct = db.Column(db.Float)