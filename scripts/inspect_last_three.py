#!/usr/bin/env python3
import sys
from pathlib import Path
# Ensure project root is in sys.path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.app import create_app
from trading_engine.core.database_pg import db
from scenarios.BacktestWeb.database import ResultadoBacktest, Trade, Usuario
from sqlalchemy import func, desc

app = create_app(user_mode='admin')

with app.app_context():
    # Encontrar las últimas 3 tandas (id_estrategia por usuario)
    q = db.session.query(
        ResultadoBacktest.usuario_id,
        ResultadoBacktest.id_estrategia,
        func.max(ResultadoBacktest.fecha_ejecucion).label('max_date')
    ).group_by(ResultadoBacktest.usuario_id, ResultadoBacktest.id_estrategia)

    tandas = q.order_by(desc('max_date')).limit(3).all()

    if not tandas:
        print('No se encontraron resultados en la BD.')
    else:
        for usuario_id, id_estrategia, max_date in tandas:
            print('='*60)
            print(f'Tanda: {id_estrategia} | Usuario ID: {usuario_id} | Fecha última: {max_date}')
            resultados = ResultadoBacktest.query.filter_by(usuario_id=usuario_id, id_estrategia=id_estrategia).order_by(ResultadoBacktest.symbol).all()
            print(f'Activos en tanda: {len(resultados)}')
            for r in resultados:
                print('-'*40)
                print(f'ID resultado: {r.id} | Símbolo: {r.symbol} | Fecha ejecución: {r.fecha_ejecucion}')
                print(f'  Return %: {r.return_pct} | Trades: {r.total_trades} | Win rate: {r.win_rate} | Sharpe: {r.sharpe_ratio}')
                notas = (r.notas[:200] + '...') if r.notas and len(r.notas)>200 else (r.notas or '')
                print(f'  Notas: {notas}')
                has_graph = bool(r.grafico_html and r.grafico_html.strip())
                print(f'  Grafico guardado en DB: {has_graph}')

                trades = Trade.query.filter_by(backtest_id=r.id).all()
                print(f'  Trades registrados: {len(trades)}')
                # Mostrar hasta 3 trades de ejemplo
                for t in trades[:3]:
                    print(f"    - {t.tipo} | entrada={t.precio_entrada} salida={t.precio_salida} pnl={t.pnl_absoluto} desc={t.descripcion}")

    # También listar archivos HTML en Graphics/admin
    import os
    from scenarios.BacktestWeb.configuracion import BACKTESTING_BASE_DIR
    graphics_dir = BACKTESTING_BASE_DIR / 'Graphics' / 'admin'
    print('\nArchivos Bokeh en Graphics/admin:')
    if graphics_dir.exists():
        for f in sorted(os.listdir(graphics_dir)):
            print('  -', f)
    else:
        print('  No existe Graphics/admin')

    # Mostrar path de FullRatio
    fr = BACKTESTING_BASE_DIR / 'Run_Results' / 'admin' / 'FullRatio' / 'FR_diario.csv'
    print('\nFullRatio path:', fr)

print('\nInspección finalizada.')
