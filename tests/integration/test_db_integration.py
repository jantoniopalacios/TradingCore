import unittest
from flask import Flask
from scenarios.BacktestWeb.database import db, ResultadoBacktest, Usuario
import os
from datetime import datetime

class TestDatabase(unittest.TestCase):
    def setUp(self):
        """Configura una base de datos temporal en memoria para el test."""
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(self.app)
        
        with self.app.app_context():
            db.create_all()
            # Creamos un usuario de prueba
            user = Usuario(username="test_user", password="123")
            db.session.add(user)
            db.session.commit()

    def test_save_backtest_result(self):
        """Verifica que podemos guardar un resultado de backtest."""
        with self.app.app_context():
            nuevo_resultado = ResultadoBacktest(
                usuario_id=1,
                id_estrategia=1,
                symbol="AAPL",
                intervalo="1d",
                return_pct=150.50,
                win_rate=65.0,
                grafico_html="<html>Gráfico Simulado</html>"
            )
            db.session.add(nuevo_resultado)
            db.session.commit()

            res = ResultadoBacktest.query.filter_by(symbol="AAPL").first()
            self.assertIsNotNone(res)
            self.assertEqual(res.return_pct, 150.50)

    def test_backtest_result_execution_date_defaults_to_naive_datetime(self):
        with self.app.app_context():
            resultado = ResultadoBacktest(
                usuario_id=1,
                id_estrategia=1,
                symbol="MSFT",
                intervalo="1d",
                return_pct=10.0,
                win_rate=50.0,
                grafico_html="<html>Gráfico Simulado</html>"
            )
            db.session.add(resultado)
            db.session.commit()
            db.session.expire_all()

            recuperado = ResultadoBacktest.query.filter_by(symbol="MSFT").first()

            self.assertIsInstance(recuperado.fecha_ejecucion, datetime)
            self.assertIsNone(recuperado.fecha_ejecucion.tzinfo)

if __name__ == '__main__':
    unittest.main()