#!/usr/bin/env python3
"""
Script para verificar coherencia entre parámetros de configuración 
y resultados de backtests guardados en la BD
"""
import sys
import json
from pathlib import Path
from decimal import Decimal

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.app import create_app
from trading_engine.core.database_pg import db
from scenarios.BacktestWeb.database import ResultadoBacktest, Trade, Usuario
from sqlalchemy import func, desc

def analizar_coherencia():
    app = create_app(user_mode='admin')
    
    with app.app_context():
        # Obtener las últimas 3 tandas
        q = db.session.query(
            ResultadoBacktest.usuario_id,
            ResultadoBacktest.id_estrategia,
            func.max(ResultadoBacktest.fecha_ejecucion).label('max_date')
        ).group_by(ResultadoBacktest.usuario_id, ResultadoBacktest.id_estrategia)

        tandas = q.order_by(desc('max_date')).limit(3).all()

        for usuario_id, id_estrategia, max_date in tandas:
            print('='*70)
            print(f'TANDA {id_estrategia} | Usuario ID: {usuario_id} | Fecha: {max_date}')
            print('='*70)
            
            resultados = ResultadoBacktest.query.filter_by(
                usuario_id=usuario_id, 
                id_estrategia=id_estrategia
            ).order_by(ResultadoBacktest.symbol).all()

            for r in resultados:
                print(f'\n📊 Símbolo: {r.symbol} | ID Resultado: {r.id}')
                print('-'*70)
                
                # 1. PARÁMETROS TÉCNICOS
                params = {}
                if r.params_tecnicos:
                    try:
                        params = json.loads(r.params_tecnicos)
                    except:
                        params = {}

                print('CONFIGURACIÓN UTILIZADA:')
                print(f'  ✓ Período de datos: {r.fecha_inicio_datos} a {r.fecha_fin_datos}')
                print(f'  ✓ Cash inicial: ${r.cash_inicial} | Comisión: {r.comision}')
                print(f'  ✓ Intervalo: {r.intervalo}')
                
                # Indicadores activados
                indicadores_activos = []
                if params.get('rsi'):
                    indicadores_activos.append(f"RSI(period={params.get('rsi_period', 14)})")
                if params.get('ema_cruce_signal'):
                    indicadores_activos.append(f"EMA(fast={params.get('ema_fast_period', 5)}, slow={params.get('ema_slow_period', 30)})")
                if params.get('macd'):
                    indicadores_activos.append(f"MACD(fast={params.get('macd_fast', 12)}, slow={params.get('macd_slow', 26)})")
                if params.get('bb_active'):
                    indicadores_activos.append(f"BB(window={params.get('bb_window', 20)})")
                
                print(f'  ✓ Indicadores: {", ".join(indicadores_activos) if indicadores_activos else "Ninguno"}')
                
                # Flags RSI
                rsi_flags = []
                if params.get('rsi_minimo'):
                    rsi_flags.append('RSI Mínimo (Sobreventa)')
                if params.get('rsi_maximo'):
                    rsi_flags.append('RSI Máximo (Sobrecompra)')
                if params.get('rsi_ascendente'):
                    rsi_flags.append('RSI Ascendente')
                if params.get('rsi_descendente'):
                    rsi_flags.append('RSI Descendente')
                if rsi_flags:
                    print(f'  ✓ Señales RSI: {", ".join(rsi_flags)}')
                
                # 2. RESULTADOS
                print(f'\nRESULTADOS:')
                print(f'  ✓ Return %: {r.return_pct}%')
                print(f'  ✓ Total Trades: {r.total_trades} | Win Rate: {r.win_rate}%')
                print(f'  ✓ Sharpe Ratio: {r.sharpe_ratio} | Max Drawdown: {r.max_drawdown}%')
                print(f'  ✓ Profit Factor: {r.profit_factor}')
                
                # 3. ANÁLISIS DE TRADES
                trades = Trade.query.filter_by(backtest_id=r.id).all()
                print(f'\nTRADES EJECUTADOS: {len(trades)} operaciones')
                
                # Agrupar por razón
                trades_por_razon = {}
                for t in trades:
                    razon = t.descripcion or 'Sin especificar'
                    if razon not in trades_por_razon:
                        trades_por_razon[razon] = []
                    trades_por_razon[razon].append(t)
                
                print('  Distribución por razón:')
                for razon, lista_trades in sorted(trades_por_razon.items(), key=lambda x: -len(x[1])):
                    pct = (len(lista_trades) / len(trades) * 100) if trades else 0
                    print(f'    - {razon}: {len(lista_trades)} ({pct:.1f}%)')
                
                # 4. VALIDACIÓN DE COHERENCIA
                print(f'\nVALIDACIÓN DE COHERENCIA:')
                
                # Si RSI está activo, debe haber trades con RSI en descripción
                if params.get('rsi'):
                    rsi_trades = [t for t in trades if 'RSI' in (t.descripcion or '')]
                    rsi_pct = (len(rsi_trades) / len(trades) * 100) if trades else 0
                    status = '✓' if rsi_pct > 30 else '⚠️'
                    print(f'  {status} RSI activo → {len(rsi_trades)} trades con RSI ({rsi_pct:.1f}%)')
                else:
                    rsi_trades = [t for t in trades if 'RSI' in (t.descripcion or '')]
                    if rsi_trades:
                        print(f'  ⚠️ RSI INACTIVO pero hay {len(rsi_trades)} trades con señal RSI (INCONSISTENCIA)')
                    else:
                        print(f'  ✓ RSI inactivo → Sin trades RSI')
                
                # Si EMA está activo, debe haber trades con EMA
                if params.get('ema_cruce_signal'):
                    ema_trades = [t for t in trades if 'EMA' in (t.descripcion or '')]
                    ema_pct = (len(ema_trades) / len(trades) * 100) if trades else 0
                    status = '✓' if ema_pct > 20 else '⚠️'
                    print(f'  {status} EMA activo → {len(ema_trades)} trades con EMA ({ema_pct:.1f}%)')
                else:
                    ema_trades = [t for t in trades if 'EMA' in (t.descripcion or '')]
                    if ema_trades:
                        print(f'  ⚠️ EMA INACTIVO pero hay {len(ema_trades)} trades con EMA (INCONSISTENCIA)')
                    else:
                        print(f'  ✓ EMA inactivo → Sin trades EMA')
                
                # Validar cierre de trades (no debería haber compras sin venta o abiertas)
                compras_abiertas = len([t for t in trades if t.tipo=='COMPRA' and t.precio_salida==0])
                print(f'  ℹ️  Posiciones abiertas (precio_salida=0): {compras_abiertas}')
                
                # Validar PnL
                total_pnl = sum(t.pnl_absoluto for t in trades if t.pnl_absoluto)
                print(f'  ℹ️  PnL total registrado: ${total_pnl:.2f}')

if __name__ == '__main__':
    analizar_coherencia()
    print('\n' + '='*70)
    print('Análisis de coherencia completado.')
    print('='*70)
