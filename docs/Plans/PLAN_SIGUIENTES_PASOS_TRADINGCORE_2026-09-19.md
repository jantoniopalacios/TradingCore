# Plan de siguientes pasos - TradingCore

Última actualización: 19/09/2026

## 1. Objetivo

Definir una secuencia de trabajo corta, verificable y documentada para continuar la evolución de TradingCore después del cierre de la fase de documentación y ayudas contextuales.

La prioridad es reducir deuda funcional antes de añadir nuevas capacidades: primero validar contratos entre UI, configuración y motor; después reforzar tests y operación; por último abordar mejoras de datos, rendimiento o nuevas estrategias.

## 2. Punto de partida

Estado consolidado al cierre de la fase anterior:

- `main` limpio y actualizado.
- Ayudas contextuales disponibles en Global, EMA, RSI, MACD, ATR, Estocástico, Bollinger y Volumen/MoS.
- Documentación de usuario y técnica revisada.
- Manual operativo actualizado.
- Acceso a documentación filtrado por rol.
- Validación web superada (`39 passed`) y prueba visual correcta.
- Último commit documental: `1dc2c44 docs: actualizar ayudas y manual operativo`.

## 3. Prioridad 1 - Revisar integración funcional de MACD

### Motivo

Es el principal punto funcional pendiente identificado durante la revisión documental.

La UI utiliza:

- `macd_buy_logic`: `macd_cruce_up`, `macd_histogram_buy`, `None`.
- `macd_sell_logic`: `macd_cruce_down`, `macd_histogram_sell`, `None`.

La lógica interna de `Filtro_MACD.py` trabaja con estados y condiciones que no se han confirmado todavía como una traducción directa y completa de esas opciones de UI.

### Trabajo

1. Trazar el flujo completo desde formulario web hasta `Filtro_MACD.py`.
2. Identificar la traducción real de `macd_buy_logic` y `macd_sell_logic`.
3. Determinar si las opciones de histograma están implementadas, parcialmente implementadas o solo expuestas en UI.
4. Corregir únicamente la integración necesaria, sin rediseñar MACD.
5. Añadir tests unitarios para cada opción de compra y venta.
6. Actualizar ayuda contextual y guía de indicadores si cambia el comportamiento validado.

### Criterio de cierre

Cada opción MACD visible en UI tiene un comportamiento inequívoco, probado y documentado.

## 4. Prioridad 2 - Auditoría de contratos UI -> configuración -> motor

### Objetivo

Evitar discrepancias similares a la detectada en MACD.

### Alcance

Revisar los parámetros visibles de:

- Global y gestión de riesgo.
- EMA.
- RSI.
- MACD.
- ATR.
- Stochastic FAST/MID/SLOW.
- Bollinger Bands.
- Volumen y MoS.

Para cada parámetro verificar:

1. Nombre HTML (`name` / `id`).
2. Lectura y normalización en backend.
3. Valor por defecto.
4. Tipo real (`bool`, `str`, `float`, `int`).
5. Propagación a la estrategia.
6. Uso efectivo por el motor.
7. Persistencia y recuperación de configuraciones.
8. Correspondencia con ayuda y documentación.

### Entregable sugerido

Una tabla técnica única con:

`UI | clave config | default | tipo | módulo consumidor | efecto | test asociado`.

### Criterio de cierre

No existen controles visibles sin consumidor conocido ni parámetros de motor importantes sin correspondencia clara en configuración.

## 5. Prioridad 3 - Consolidar tests de lógica combinada

### Objetivo

Cubrir las reglas de interacción entre indicadores, no solo cada indicador de forma aislada.

### Casos prioritarios

- Señales técnicas de compra con lógica OR.
- Filtros globales activos con lógica AND.
- B&H cuando no existen señales técnicas activas.
- Filtro global RSI y su interacción con B&H.
- ATR como filtro de entrada.
- Volumen/MoS como filtros.
- Cierres técnicos con varios indicadores activos.
- Stop base, swing, trailing y break-even sobre una posición ya abierta.

### Especial atención

Mantener documentado el comportamiento real del break-even:

`entry_price * (1 - breakeven_trigger_pct)`

No tratarlo como un disparador de beneficio salvo que el motor se rediseñe explícitamente en el futuro.

### Criterio de cierre

Las combinaciones críticas tienen tests de regresión y los resultados esperados no dependen de interpretación manual.

## 6. Prioridad 4 - Endurecer operación de la aplicación web

### Problema observado

Durante la validación se detectó que una instancia antigua de Flask podía seguir sirviendo plantillas anteriores y provocar diagnósticos falsos.

### Trabajo

1. Revisar `start_web.bat` y `stop_web.bat`.
2. Hacer visible el PID/proceso que ocupa el puerto 5000.
3. Evitar o advertir claramente el arranque cuando ya existe otra instancia.
4. Añadir una comprobación operativa sencilla al flujo de verificación.
5. Valorar un fichero PID o mecanismo equivalente si simplifica el control en Windows.

### Criterio de cierre

El operador puede saber de forma inequívoca qué proceso web está activo y reiniciarlo sin dejar instancias antiguas.

## 7. Prioridad 5 - Revisar datos fundamentales y proveedores

### Objetivo

Retomar esta parte solo después de cerrar contratos y tests de indicadores.

### Trabajo previsto

- Confirmar qué métricas fundamentales consume realmente cada estrategia.
- Revisar el papel actual de Yahoo Finance y Alpha Vantage.
- Separar la lógica del motor del proveedor concreto.
- Normalizar el formato de datos fundamentales.
- Revisar caché, antigüedad y actualización incremental.
- Evitar inferir actualidad únicamente por nombres de fichero o trimestre.

### Criterio de cierre

El motor solicita métricas normalizadas y la capa de datos decide proveedor, caché y actualización.

## 8. Prioridad 6 - Observabilidad, rendimiento y mantenimiento

Solo después de estabilizar la lógica funcional:

- revisar tiempos de backtest y cuellos de botella;
- revisar crecimiento de logs, cachés y artefactos de gráficos;
- validar scheduler y ejecución periódica;
- eliminar código legacy únicamente cuando exista cobertura suficiente;
- mantener separados scripts de producción, diagnóstico, mantenimiento y experimentación.

## 9. Orden de ejecución recomendado

1. Crear checkpoint del estado actual si se desea una referencia adicional al cierre documental.
2. Abrir rama específica para revisión MACD.
3. Resolver y testear MACD.
4. Ejecutar auditoría UI -> configuración -> motor.
5. Corregir discrepancias encontradas en commits pequeños e independientes.
6. Ampliar tests de combinaciones.
7. Endurecer arranque/parada web.
8. Revisar datos fundamentales.
9. Abordar rendimiento, scheduler y limpieza legacy.

## 10. Forma de trabajo

Para cada bloque:

1. Analizar primero el comportamiento actual.
2. Definir alcance exacto antes de modificar código.
3. Trabajar en rama específica cuando el cambio no sea trivial.
4. Cambios pequeños y commits temáticos.
5. Ejecutar tests relevantes antes del commit.
6. Ejecutar `git diff --check`.
7. Hacer prueba visual si cambia interfaz o plantillas.
8. Revisar ayuda contextual y documentación antes de cerrar.
9. Merge a `main` solo con rama limpia y validada.
10. No hacer `push` salvo decisión explícita.

## 11. Uso de Copilot

Para controlar consumo de cuota:

- usar Copilot principalmente para cambios de código con alcance bien definido;
- preparar previamente el análisis, archivos afectados y criterios de aceptación;
- evitar prompts exploratorios largos;
- realizar directamente cambios pequeños de documentación, textos, tests simples o correcciones mecánicas cuando resulte más eficiente;
- revisar siempre el diff generado antes de aceptar cambios.

## 12. Definition of Done por bloque

Antes de cerrar cualquier bloque:

```text
[ ] Alcance definido
[ ] Código implementado
[ ] Tests añadidos o actualizados
[ ] Tests relevantes superados
[ ] git diff --check sin errores
[ ] Prueba visual realizada si aplica
[ ] Ayuda contextual revisada si aplica
[ ] Documentación de usuario revisada
[ ] Documentación técnica revisada
[ ] Commit temático realizado
[ ] Rama limpia
[ ] Merge a main realizado cuando corresponda
[ ] Tag/checkpoint creado si el hito lo justifica
```

## 13. Próximo bloque concreto

El siguiente trabajo recomendado es **Revisión funcional de MACD**, porque es la discrepancia funcional conocida más clara que quedó explícitamente pendiente durante la fase de documentación.

No conviene iniciar nuevas funcionalidades de indicadores antes de resolver este contrato entre UI y motor.
