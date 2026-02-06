````markdown
# ⚡ QUICK START: Probar Backtest Web (5 minutos)

## 🎯 Objetivo
Verificar que el backtest ahora funciona desde la web y genera resultados visibles.

---

## ✅ Paso 1: Verificar Sistema (1 minuto)

```powershell
# Terminal 1: Verifica que todo está listo
python verificar_backtest_web.py
```

**Deberías ver:**
```
✅ VERIFICACIÓN COMPLETA - Sistema listo para backtest desde web ✨
```

---

## ✅ Paso 2: Monitorear Logs en Tiempo Real (1 minuto)

```powershell
# Terminal 2: Abre nueva ventana PowerShell
Get-Content -Path ".\logs\trading_app.log" -Wait
```

---

## ✅ Paso 3: Iniciar Servidor Web (1 minuto)

```powershell
# Terminal 3: Abre otra nueva ventana PowerShell
python app.py
# O si usas gunicorn:
# gunicorn -w 1 app:app --reload
```

---

## ✅ Paso 4: Ejecutar Backtest desde Web (2 minutos)

1. **Abre navegador:**
   ```
   http://localhost:5000
   ```

2. **Inicia sesión** (usuario admin / su usuario registrado)

3. **Configura el backtest:**
   - Selecciona symbolo: **NKE** (o cualquier otro disponible)
   - Activa algunos indicadores (ej: EMA, MACD)
   - Haz clic: **"Lanzar Backtest"**

4. **Mira Terminal 2 (logs):**
Deberías ver inmediatamente algo como:
```
[LAUNCH] Usuario admin lanzando backtest...
[LAUNCH] Configuración preparada:
  - Usuario: admin (ID=1)
  - Tanda: #1
  - Indicadores activos: 3
  - Símbolos: 1
[LAUNCH] ✅ Iniciando hilo de backtest...
```

---

## 🎉 Si Todo Funciona

**Verás en los logs:**
- ✅ 9 pasos completados
- ✅ Datos descargados y procesados
- ✅ Backtest ejecutado
- ✅ Gráficos generados
- ✅ Resultados guardados en BD

**En la web:**
- ✅ Página de resultados poblada
- ✅ Gráfico Bokeh disponible
- ✅ Métricas visibles (Return, Sharpe, etc.)

---

## 🚨 Si Hay Problemas

### ❌ Problema: "Sin datos históricos"
**En logs verás:**
```
❌ Sin datos históricos descargados
```
**Solución:** Verifica que archivos CSV existen en `Data_files/NKE_1d_MAX.csv`

---

## 🚀 Listo!

Ya deberías tener un backtest funcional desde web con:
- ✅ Logging completo
- ✅ Resultados visibles
- ✅ Gráficos generados
- ✅ Datos en BD

**¡A estrategiar! 📈**

````
