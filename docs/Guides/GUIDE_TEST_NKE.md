# Guia de prueba NKE

## Objetivo
Ejecutar un backtest de referencia sobre `NKE` para validar configuracion, flujo de ejecucion y metricas basicas.

## Opcion A: Ejecucion por script

1. Ir a la raiz del proyecto.
```powershell
cd c:\Users\juant\Proyectos\Python\TradingCore
```

2. Ejecutar el script de prueba.
```powershell
python scripts/test_backtest_nke.py
```

Resultado esperado:
- carga de datos historicos.
- inicializacion de indicadores.
- ejecucion de backtest.
- salida de metricas (`Return`, `Sharpe`, `Max Drawdown`, `Win Rate`).
- generacion de grafico HTML.

## Opcion B: Ejecucion desde la web

1. Iniciar la aplicacion Flask.
```powershell
python scenarios/BacktestWeb/app.py
```

2. Abrir `http://localhost:5000`.
3. Iniciar sesion.
4. Configurar `NKE` como simbolo unico.
5. Parametros sugeridos:
- fecha inicio: `2020-01-01`
- fecha fin: `2023-12-31`
- capital: `10000`
- comision: `0.002`
- stop loss: `0.05`
- EMA rapida: `12`
- EMA lenta: `26`

6. Guardar configuracion y lanzar backtest.
7. Revisar historial, graficos y logs.

## Parametros recomendados para experimentacion
- EMA rapida: `5`, `10`, `12`, `20`.
- EMA lenta: `26`, `30`, `50`, `100`.
- stop loss: `0.03`, `0.05`, `0.07`, `0.10`.
- intervalo: `1d`, `1h`, `1wk`.
- rango temporal: distintos ciclos de mercado.

## Como interpretar resultados
- `Return [%]`: rentabilidad total de la estrategia.
- `Buy & Hold Return [%]`: referencia pasiva del activo.
- `Total Trades`: numero de operaciones.
- `Win Rate [%]`: porcentaje de operaciones ganadoras.
- `Sharpe Ratio`: retorno ajustado por riesgo.
- `Max Drawdown [%]`: peor caida desde maximos.
- `Profit Factor`: ratio ganancias/perdidas.

## Configuracion tecnica base del test
- activo: `NKE`.
- fuente de datos: `Data_files/NKE_1d_MAX.csv`.
- capital inicial: `10000`.
- comision: `0.2%`.
- estrategia base: cruce EMA (`12`/`26`) con filtros opcionales.

## Siguientes pasos
1. Comparar periodos EMA para estabilidad.
2. Probar confirmaciones con RSI y MACD.
3. Validar en otros activos (`AAPL`, `MSFT`, etc.).
