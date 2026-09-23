# Plan de siguientes pasos - TradingCore

Última actualización: 23/09/2026

## 1. Objetivo

Definir una secuencia de trabajo corta, verificable y documentada para continuar la evolución de TradingCore después del cierre de la fase de documentación y ayudas contextuales.

Este documento es un **plan vivo**. Debe actualizarse cuando se identifiquen nuevas tareas relevantes, nuevas funcionalidades o cambios de prioridad, de forma que refleje siempre el trabajo pendiente real y el orden acordado.

La prioridad general es reducir deuda funcional y documental antes de añadir nuevas capacidades: primero asegurar que cada tipo de usuario dispone de la documentación adecuada; después validar contratos entre UI, configuración y motor; reforzar tests y operación; y finalmente abordar mejoras de datos, rendimiento o nuevas estrategias.

## 2. Punto de partida

Estado consolidado a 19/09/2026:

- `main` limpio y actualizado tras cerrar el bloque MACD.
- Ayudas contextuales disponibles en Global, EMA, RSI, MACD, ATR, Estocástico, Bollinger y Volumen/MoS.
- Manual de Usuario creado en `docs/User/MANUAL_USUARIO_TRADINGCORE.md`.
- Acceso documental reorganizado por rol: el usuario normal accede al Manual de Usuario y el administrador conserva acceso completo a `docs/`.
- Índice, README y convenciones documentales actualizados para reflejar la separación por audiencia.
- Tests web de autorización documental actualizados y validados (`40 passed`).
- Revisión funcional de MACD completada:
  - `macd_buy_logic` y `macd_sell_logic` se consumen directamente en el motor;
  - `Cruce Up`, `Histograma Buy`, `Cruce Down`, `Histograma Sell` y `None` tienen comportamiento explícito;
  - `MACD activo + Compra=None` ya no desplaza indebidamente el fallback B&H;
  - corregido el orden de parámetros `window_slow` / `window_fast` al inicializar MACD con `ta`;
  - tests unitarios de señales técnicas validados (`32 passed`);
  - ayuda contextual, Manual de Usuario y guía de combinación de indicadores actualizados.
- Commit de documentación y acceso por rol: `f9b8dc5 docs: crear manual de usuario y restringir acceso por rol`.
- Commit de cierre MACD: `6ad2d9e fix: alinear MACD entre interfaz y motor`.
- Plan de trabajo versionado en `docs/Plans/`.

El siguiente bloque técnico es la **auditoría completa de contratos UI -> configuración -> motor** para detectar discrepancias similares a las corregidas en MACD.

## 3. Prioridad 1 - Crear un verdadero Manual de Usuario [COMPLETADA]

### Motivo

Los usuarios normales de TradingCore:

- acceden únicamente a la interfaz web;
- no tienen acceso al código fuente;
- no arrancan ni detienen la aplicación;
- no administran PostgreSQL, Git, PowerShell, scheduler, ramas ni despliegues;
- necesitan instrucciones completas para usar la aplicación desde la UI.

El administrador, en cambio, tiene acceso al código y a la operación del sistema y debe poder consultar toda la documentación técnica y operativa.

### Trabajo

1. Crear `docs/User/MANUAL_USUARIO_TRADINGCORE.md`.
2. Redactarlo desde el punto de vista exclusivo de un usuario de la web, sin requisitos técnicos de administración.
3. Incluir, como mínimo:
   - acceso e inicio de sesión;
   - recorrido completo por la interfaz;
   - configuración global;
   - explicación de EMA, RSI, MACD, ATR, Estocástico, Bollinger, Volumen y MoS;
   - combinación de indicadores, señales y filtros;
   - guardado y recuperación de configuraciones;
   - selección de símbolos;
   - lanzamiento y seguimiento de un backtest;
   - interpretación de resultados, operaciones y gráficos;
   - historial;
   - notificaciones;
   - documentación y ayudas contextuales;
   - problemas frecuentes;
   - glosario.
4. Reutilizar como fuente las ayudas contextuales y guías funcionales ya validadas, evitando duplicar explicaciones contradictorias.
5. Separar claramente la documentación de usuario de la documentación técnica/administrativa.

### Criterio de cierre

Un usuario sin conocimientos de Python, Git, PostgreSQL ni administración de servidores puede utilizar TradingCore únicamente con el manual y la ayuda contextual de la UI.

**Estado:** completada en `f9b8dc5`.

## 4. Prioridad 2 - Reorganizar el acceso documental por rol [COMPLETADA]

### Objetivo

Alinear la documentación visible con el modelo real de usuarios.

### Modelo objetivo

**Usuario normal:**

- `docs/User/MANUAL_USUARIO_TRADINGCORE.md`;
- ayuda contextual integrada en la UI;
- otros documentos funcionales solo si se decide expresamente que aportan valor al usuario final.

**Administrador:**

- acceso completo a `docs/`;
- README técnico;
- manual operativo;
- arquitectura;
- guías técnicas y funcionales;
- API;
- planes;
- índices;
- cualquier otra documentación de desarrollo, mantenimiento u operación.

### Trabajo

1. Revisar la allowlist de documentación para usuarios normales en `scenarios/BacktestWeb/file_handler.py`.
2. Priorizar el nuevo Manual de Usuario como documento principal.
3. Retirar del acceso normal documentos claramente técnicos, especialmente `QUICK_START_BACKTEST_WEB.md` y `README.md`, salvo decisión posterior en sentido contrario.
4. Mantener acceso total para `admin`.
5. Actualizar `docs/Index/00_INDEX_DOCUMENTACION.md`, `docs/README.md` y las convenciones documentales para reflejar esta separación.
6. Añadir/ajustar tests web de autorización documental por rol.

### Criterio de cierre

El usuario normal solo ve documentación útil para operar la UI y el administrador conserva acceso completo a toda la documentación.

**Estado:** completada en `f9b8dc5`; validación web `40 passed` y comprobación visual realizada.

## 5. Prioridad 3 - Integración funcional de MACD [COMPLETADO]

La correspondencia UI -> configuración -> motor ha quedado validada y corregida.

Estado cerrado:

- compra por cruce alcista MACD/Signal;
- compra por cambio del histograma a positivo;
- venta por cruce bajista MACD/Signal;
- venta por cambio del histograma a negativo;
- `None` desactiva el lado correspondiente;
- Buy & Hold no queda desplazado por MACD si no existe una lógica de compra utilizable;
- tests y ayuda contextual actualizados.

Commit de referencia: `6ad2d9e fix: alinear MACD entre interfaz y motor`.

## 6. Prioridad 4 - Auditoría de contratos UI -> configuración -> motor [COMPLETADO]

La auditoría funcional de Global/Riesgo, EMA, RSI, MACD, ATR, Stochastic, Bollinger, Volumen y MoS se ha ejecutado. Las discrepancias prioritarias se han corregido en commits independientes.

Correcciones cerradas:

- persistencia de booleanos (`atr_enabled`, `margen_seguridad_minimo`, `volume_minimo`) y render explícito de `stoploss_swing_enabled` - `b933e2c`;
- MACD - `6ad2d9e`;
- Stochastic - `5a79719`;
- compra Bollinger y gating B&H - `277a831`;
- MoS mínimo/ascendente y combinación AND - `da92dd7`;
- Volumen basado en V-SMA y tendencia ascendente real - `8809036`.

Validación del cierre de Volumen: `49 passed` en `tests/unit/test_technical_signals.py` y `42 passed` en `tests/web/test_routes.py`.

Pendientes de limpieza o revisión no bloqueantes cerrados posteriormente:

- Bollinger: la UI y documentación ya reflejan que `bb_sell_crossover` puede cerrar por cruce bajista de banda superior o SMA central;
- `bb_window_state`: retirado de la UI al no participar actualmente en la lógica de señales o estados; se conserva en configuración por compatibilidad;
- EMA/RSI: comentarios y docstrings legacy limpiados sin modificar la lógica funcional;
- tests de interacción entre múltiples indicadores y filtros ampliados y consolidados.

## 7. Prioridad 5 - Consolidar tests de lógica combinada

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

## 8. Prioridad 6 - Endurecer operación de la aplicación web

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

## 9. Prioridad 7 - Revisar datos fundamentales y proveedores

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

## 10. Prioridad 8 - Observabilidad, rendimiento y mantenimiento

Solo después de estabilizar la lógica funcional:

- revisar tiempos de backtest y cuellos de botella;
- revisar crecimiento de logs, cachés y artefactos de gráficos;
- validar scheduler y ejecución periódica;
- eliminar código legacy únicamente cuando exista cobertura suficiente;
- mantener separados scripts de producción, diagnóstico, mantenimiento y experimentación.

## 11. Orden de ejecución recomendado

Estado a 23/09/2026:

1. Manual de Usuario y acceso documental por rol - completado.
2. MACD - completado.
3. Auditoría UI -> configuración -> motor - completada.
4. Correcciones Stochastic, Bollinger, MoS y Volumen - completadas.
5. Consolidación documental transversal - completada en `0c8f5a2`.
6. Ampliar tests de lógica combinada - completado.
7. Revisar pendientes menores de Bollinger y limpieza EMA/RSI - completado.
8. [SIGUIENTE] Endurecer arranque/parada web.
9. Revisar datos fundamentales y proveedores.
10. Abordar rendimiento, scheduler y limpieza legacy.

## 12. Gestión continua del plan

El seguimiento no técnico del efecto de cada cambio sobre las estrategias se mantiene en `docs/Summaries/IMPACTO_FUNCIONAL_EVOLUCION_TRADINGCORE.md`. Ese documento es vivo y debe actualizarse al cerrar cada bloque restante del plan, aunque el bloque no tenga impacto funcional esperado sobre los resultados.

Este fichero debe mantenerse actualizado durante el desarrollo.

### Regla de mantenimiento

Cada vez que se incorpore una nueva tarea, mejora o funcionalidad relevante:

1. evaluar si modifica prioridades existentes;
2. añadirla al plan en la sección correspondiente o crear una nueva prioridad;
3. indicar motivo, alcance, trabajo y criterio de cierre;
4. actualizar el orden de ejecución si procede;
5. revisar el impacto en documentación de usuario, documentación técnica, tests y ayudas contextuales;
6. actualizar la fecha del plan;
7. actualizar `docs/Summaries/IMPACTO_FUNCIONAL_EVOLUCION_TRADINGCORE.md` con las implicaciones del bloque para una persona no técnica;
8. versionar el cambio documental en Git.

### Al cerrar una tarea

- marcarla como completada o trasladarla a una sección de hitos cerrados si conviene conservar trazabilidad;
- registrar el commit o hito relevante;
- actualizar el siguiente bloque concreto.

El plan no debe convertirse en un histórico exhaustivo de commits. Su función es mostrar el estado actual, las prioridades y el trabajo pendiente.

## 13. Forma de trabajo

Para cada bloque:

1. Analizar primero el comportamiento actual.
2. Definir alcance exacto antes de modificar código.
3. Actualizar este plan si aparece una nueva tarea o cambia la prioridad.
4. Trabajar en rama específica cuando el cambio no sea trivial.
5. Cambios pequeños y commits temáticos.
6. Ejecutar tests relevantes antes del commit.
7. Ejecutar `git diff --check`.
8. Hacer prueba visual si cambia interfaz o plantillas.
9. Revisar ayuda contextual y documentación antes de cerrar.
10. Merge a `main` solo con rama limpia y validada.
11. No hacer `push` salvo decisión explícita.

## 14. Uso de Copilot

Para controlar consumo de cuota:

- usar Copilot principalmente para cambios de código con alcance bien definido;
- preparar previamente el análisis, archivos afectados y criterios de aceptación;
- evitar prompts exploratorios largos;
- realizar directamente cambios pequeños de documentación, textos, tests simples o correcciones mecánicas cuando resulte más eficiente;
- revisar siempre el diff generado antes de aceptar cambios.

## 15. Definition of Done por bloque

Antes de cerrar cualquier bloque:

```text
[ ] Alcance definido
[ ] Plan actualizado si aplica
[ ] Código implementado
[ ] Tests añadidos o actualizados
[ ] Tests relevantes superados
[ ] git diff --check sin errores
[ ] Prueba visual realizada si aplica
[ ] Ayuda contextual revisada si aplica
[ ] Manual de Usuario revisado si aplica
[ ] Documentación técnica revisada
[ ] Documento de impacto funcional actualizado
[ ] Commit temático realizado
[ ] Rama limpia
[ ] Merge a main realizado cuando corresponda
[ ] Tag/checkpoint creado si el hito lo justifica
```

## 16. Próximo bloque concreto

El siguiente bloque recomendado es **endurecer el arranque y parada de la aplicación web**.

Objetivo inmediato:

1. revisar `start_web.bat` y `stop_web.bat`;
2. identificar de forma clara el proceso/PID que ocupa el puerto 5000;
3. evitar o advertir arranques duplicados;
4. facilitar una parada y reinicio inequívocos sin dejar instancias antiguas;
5. añadir una comprobación operativa sencilla al flujo de verificación.
