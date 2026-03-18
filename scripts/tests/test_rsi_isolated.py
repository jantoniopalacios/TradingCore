#!/usr/bin/env python3
"""
TEST 1: Verificar Aislamiento de RSI (RSI Solo, Sin EMA)

Objetivo: Confirmar que RSI genera trades incluso cuando EMA estÃ¡ desactivado
ParÃ¡metros:  rsi=True, rsi_ascendente=True, ema_cruce_signal=False
Activos:     NKE Ãºnicamente
PerÃ­odo:     2024-01-01 to 2024-12-31
Expectativa: MÃ­nimo 20+ trades con SOLO "RSI Ascendente" (sin EMA)
"""
import sys
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scenarios.BacktestWeb.app import create_app
from scenarios.BacktestWeb.Backtest import ejecutar_backtest
from scenarios.BacktestWeb.configuracion import cargar_y_asignar_configuracion, System
from trading_engine.core.database_pg import db
from scenarios.BacktestWeb.database import ResultadoBacktest, Trade, Usuario, Simbolo

def test_rsi_isolated():
    """TEST 1: RSI Aislado sin EMA"""
    
    print("="*70)
    print("TEST 1: RSI AISLADO (Sin EMA)")
    print("="*70)
    
    app = create_app(user_mode='admin')
    
    with app.app_context():
        # 1. Cargar config base
        cargar_y_asignar_configuracion('admin')
        
        # 2. Configurar parÃ¡metros para TEST 1
        config = {
            # Datos
            'start_date': '2024-01-01',
            'end_date': '2024-12-31',
            'intervalo': '1d',
            'cash': 10000,
            'commission': 0.0,
            'stoploss_percentage_below_close': 0.0,
            
            # INDICADORES
            # âŒ EMA DESACTIVADO
            'ema_cruce_signal': False,
            'ema_slow_minimo': False,
            'ema_slow_ascendente': False,
            'ema_slow_maximo': False,
            'ema_slow_descendente': False,
            
            # âœ… RSI ACTIVADO (AISLADO)
            'rsi': True,
            'rsi_period': 14,  # EstÃ¡ndar, no 40 de las tendas anteriores
            'rsi_low_level': 30,
            'rsi_high_level': 70,
            'rsi_minimo': False,      # Solo ascendente
            'rsi_ascendente': True,   # <-- ACTIVO
            'rsi_maximo': False,
            'rsi_descendente': False,
            
            # Otros indicadores desactivados
            'macd': False,
            'bb_active': False,
            'filtro_fundamental': False,
            'enviar_mail': False,
            'margen_seguridad_active': False,
            'volume_active': False,
            'stoch_fast': False,
            'stoch_mid': False,
            'stoch_slow': False,
            
            # Metadata
            'user_id': 1,
            'user_mode': 'admin',
            'tanda_id': 100,  # ID Ãºnico para este test
        }
        
        # 3. Asignar al System
        for key, value in config.items():
            if hasattr(System, key):
                setattr(System, key, value)
        
        # 4. Ejecutar backtest usando ejecutar_backtest (integrado)
        print(f"\nEjecutando backtest NKE con parÃ¡metros:")
        print(f"  âœ“ PerÃ­odo: {config['start_date']} a {config['end_date']}")
        print(f"  âœ“ RSI: Activo (period=14, ascendente=True)")
        print(f"  âœ“ EMA: Desactivado")
        print(f"  âœ“ Cash: ${config['cash']}")
        print(f"  âœ“ SÃ­mbolo(s): NKE")
        print(f"\nProcessando...")
        
        # Asegurarse que NKE estÃ¡ en DB
        u = Usuario.query.filter_by(username='admin').first()
        nke_sym = Simbolo.query.filter_by(usuario_id=u.id, symbol='NKE').first()
        if not nke_sym:
            new_sym = Simbolo(symbol='NKE', name='Nike', usuario_id=u.id)
            db.session.add(new_sym)
            db.session.commit()
        
        # Ejecutar usando la funciÃ³n integrada
        try:
            results_df, trades_df, graficos = ejecutar_backtest(config)
            
            if results_df is None or results_df.empty:
                print(f"\nâŒ FALLO: El backtest no retornÃ³ resultados")
                return False
            
            print(f"\nâœ… Ã‰XITO: Backtest completado")
            print(f"  Resultados: {len(results_df)} filas")
            
            # Analizar resultado NKE
            nke_result = results_df[results_df['Symbol'] == 'NKE'].iloc[0] if len(results_df) > 0 else None
            
            if nke_result is not None:
                print(f"\nðŸ“Š RESULTADOS NKE (RSI AISLADO):")
                print(f"  Return %: {nke_result.get('Return %', 'N/A')}%")
                print(f"  Total Trades: {nke_result.get('Total Trades', 'N/A')}")
                print(f"  Win Rate: {nke_result.get('Win Rate', 'N/A')}%")
                print(f"  Sharpe Ratio: {nke_result.get('Sharpe Ratio', 'N/A')}")
            
            # Analizar trades
            if trades_df is not None and not trades_df.empty:
                print(f"\n  Columns en trades_df: {trades_df.columns.tolist()}")
                
                # Usar columna correcta
                symbol_col = 'Symbol'
                desc_col = 'Descripcion'  # Capitalizado segÃºn output
                
                nke_trades = trades_df[trades_df[symbol_col] == 'NKE']
                print(f"\nðŸ“‹ TRADES EJECUTADOS (NKE): {len(nke_trades)}")
                
                # Agrupar por razÃ³n
                razones = nke_trades[desc_col].value_counts()
                print(f"\n  DistribuciÃ³n por razÃ³n:")
                for razon, count in razones.items():
                    pct = (count / len(nke_trades) * 100)
                    print(f"    - {razon}: {count} ({pct:.1f}%)")
                
                # Validar que NO hay EMA si EMA estÃ¡ desactivado
                ema_trades = len([t for t in nke_trades[desc_col] if 'EMA' in str(t)])
                rsi_trades = len([t for t in nke_trades[desc_col] if 'RSI' in str(t)])
                
                print(f"\n  ValidaciÃ³n:")
                print(f"    - Trades con RSI: {rsi_trades} ({rsi_trades/len(nke_trades)*100 if nke_trades.shape[0] > 0 else 0:.1f}%)")
                print(f"    - Trades con EMA: {ema_trades} ({ema_trades/len(nke_trades)*100 if nke_trades.shape[0] > 0 else 0:.1f}%)")
                
                if ema_trades > 0:
                    print(f"    âš ï¸  ADVERTENCIA: EMA desactivado pero hay {ema_trades} trades con EMA")
                    print(f"        Esto sugiere que EMA estÃ¡ implÃ­citamente activo en la lÃ³gica")
                    return False
                else:
                    print(f"    âœ… CORRECTO: Sin trades EMA cuando EMA estÃ¡ desactivado")
                
                if rsi_trades < 20:
                    print(f"    âš ï¸  ADVERTENCIA: Menos de 20 trades con RSI (esperaba mÃ­nimo 20)")
                    return False
                else:
                    print(f"    âœ… CORRECTO: RSI generÃ³ {rsi_trades} trades (suficiente)")
                
            return True
            
        except Exception as e:
            print(f"\nâŒ ERROR durante backtest: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = test_rsi_isolated()
    
    print("\n" + "="*70)
    if success:
        print("âœ… TEST 1 PASÃ“: RSI funciona correctamente aislado")
    else:
        print("âŒ TEST 1 FALLÃ“: Revisar lÃ³gica de RSI o EMA")
    print("="*70)
    
    sys.exit(0 if success else 1)


