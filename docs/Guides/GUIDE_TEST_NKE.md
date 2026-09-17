# Guia de prueba NKE

Ultima actualizacion: 17/09/2026

## Objetivo
Ejecutar un backtest de referencia sobre `NKE` para validar configuracion, flujo de ejecucion y metricas basicas.

> Documento tecnico/admin. Los parametros de esta guia son orientativos para pruebas y no constituyen una configuracion recomendada universal.

## Opcion A: Ejecucion por script

1. Situarse en la raiz del repositorio con el entorno virtual activo.
2. Ejecutar el script de prueba:

```powershell
python scripts/test_backtest_nke.py
```

Resultado esperado:
- carga de datos historicos;
- inicializacion de indicadores;
- ejecucion del backtest;
- salida de metricas (`Return`, `Sharpe`, `Max Drawdown`, `Win Rate`);
- generacion de grafico HTML cuando corresponda.

## Opcion B: Ejecucion desde la web

1. Iniciar la aplicacion Flask:

```powershell
python scenarios/BacktestWeb/app.py
```

2. Abrir `http://localhost:5000`.
3. Iniciar sesion.
4. Configurar `NKE` como simbolo unico.
5. Usar una configuracion de prueba reproducible. Por ejemplo:
   - fecha inicio: `2020-01-01`;
   - fecha fin: `2023-12-31`;
   - capital: `10000`;
   - comision: `0.002`;
   - stop loss: `0.05`;
   - EMA rapida: `12`;
   - EMA lenta: `26`.
6. Guardar configuracion y lanzar el backtest.
7. Revisar historial, graficos y logs.

## Parametros para experimentacion

Valores orientativos para realizar comparativas controladas:
- EMA rapida: `5`, `10`, `12`, `20`;
- EMA lenta: `26`, `30`, `50`, `100`;
- stop loss: `0.03`, `0.05`, `0.07`, `0.10`;
- intervalo: `1d`, `1h`, `1wk`;
- rango temporal: distintos ciclos de mercado.

Mantener constantes simbolo, fechas, capital y comision cuando el objetivo sea comparar el efecto de un unico parametro.

## Como interpretar resultados
- `Return [%]`: rentabilidad total de la estrategia.
- `Buy & Hold Return [%]`: referencia pasiva del activo.
- `Total Trades`: numero de operaciones.
- `Win Rate [%]`: porcentaje de operaciones ganadoras.
- `Sharpe Ratio`: retorno ajustado por riesgo.
- `Max Drawdown [%]`: peor caida desde maximos.
- `Profit Factor`: ratio ganancias/perdidas.

## Configuracion tecnica base del test
- activo: `NKE`;
- fuente de datos historicos: `Data_files/NKE_1d_MAX.csv` cuando exista en cache;
- capital inicial: `10000`;
- comision: `0.2%`;
- estrategia base: cruce EMA (`12`/`26`) con filtros opcionales.

## Nota sobre MACD

La interfaz usa `macd_buy_logic` y `macd_sell_logic`. La integracion de las opciones basadas en histograma con la logica interna esta pendiente de revision funcional, por lo que no debe utilizarse como referencia de validacion hasta cerrar esa revision.

## Siguientes pasos
1. Comparar periodos EMA para estabilidad.
2. Probar confirmaciones con RSI.
3. Probar MACD por separado cuando se cierre su revision funcional.
4. Validar la misma metodologia en otros activos.
