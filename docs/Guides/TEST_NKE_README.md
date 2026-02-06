````markdown
# 🎯 Test de Backtest: NKE con EMA

He creado 3 scripts para testear tu motor con NKE y diferentes configuraciones de EMA.

---

## 📁 Scripts Disponibles

### 1. **test_backtest_nke.py** (Básico y directo)
Ejecuta un backtest simple con configuración predeterminada.

```bash
cd c:\Users\juant\Proyectos\Python\TradingCore
python test_backtest_nke.py
```

**Qué hace:**
- ✅ Carga datos de NKE (1d)
- ✅ Inicializa EMA Rápida (12) y Lenta (26)
- ✅ Ejecuta estrategia con cruce de EMAs
- ✅ Aplica Stop Loss 5%
- ✅ Muestra métricas (Return, Sharpe, Drawdown, Win Rate, etc.)
- ✅ Genera gráfico HTML interactivo

**Salida esperada:**
```
========================================
🎯 TEST BACKTEST: NKE con EMA
========================================

✅ Cargando datos desde: ...
📊 Datos cargados: 1258 registros | Rango: 2018-01-02 a 2023-12-29

🔧 Inicializando indicadores...
✅ EMA_Fast (12) e EMA_Slow (26) inicializadas

⚙️  Ejecutando backtest...

========================================
📊 RESULTADOS DEL BACKTEST
========================================

Return (%):         X.XX%
Buy & Hold (%):     Y.YY%
Total Trades:       N
Win Rate (%):       Z.ZZ%
Sharpe Ratio:       A.AA
Max Drawdown (%):   B.BB%
Profit Factor:      C.CC

📈 Generando gráfico...
✅ Gráfico guardado: backtest_nke_test.html
```

---

### 2. **test_backtest_nke_interactive.py** (Menú interactivo)
Permite seleccionar y personalizar configuraciones sin editar código.

```bash
python test_backtest_nke_interactive.py
```

**Qué hace:**
- 📋 Muestra 5 presets predefinidos
- 🎨 Permite personalizar parámetros
- 🔄 Ejecuta múltiples tests en la misma sesión
- 📊 Compara resultados

---

### 3. **GUIDE_TEST_NKE.md** (Documentación)
Guía de referencia con:
- Instrucciones paso a paso
- Cómo usar la interfaz web
- Parámetros que puedes variar
- Cómo interpretar resultados
- Información técnica

---

## 🚀 Inicio Rápido

### Opción A: Script Automático (recomendado para empezar)
```bash
cd c:\Users\juant\Proyectos\Python\TradingCore
python test_backtest_nke.py
```

### Opción B: Script Interactivo (para experimentar)
```bash
cd c:\Users\juant\Proyectos\Python\TradingCore
python test_backtest_nke_interactive.py
```

### Opción C: Interfaz Web (GUI)
```bash
cd c:\Users\juant\Proyectos\Python\TradingCore
python -m scenarios.BacktestWeb.app
# Abre http://localhost:5000
# Login: admin / admin
```

---

## ⚙️ Requisitos

✅ Datos de NKE presentes: `Data_files/NKE_1d_MAX.csv`  
✅ Motor central instalado: `trading_engine/`  
✅ Backtesting.py disponible  
✅ Pandas, NumPy disponibles

---

**¡Listo para testear!** 🚀

````
