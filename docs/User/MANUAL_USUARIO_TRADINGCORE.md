# Manual de Usuario de TradingCore

**Última actualización:** 29/09/2026
**Audiencia:** usuarios de la interfaz web de TradingCore
**Alcance:** uso funcional de la aplicación. No incluye instalación, arranque/parada del servidor, Git, PowerShell, PostgreSQL, código fuente ni tareas de administración.

---

## 1. Objetivo del manual

Este manual explica cómo utilizar TradingCore desde la interfaz web para configurar una estrategia, seleccionar activos, ejecutar backtests, revisar resultados, consultar gráficos e interpretar las principales opciones disponibles.

El usuario normal no necesita conocer cómo está desplegada la aplicación ni cómo se mantiene técnicamente. Si la aplicación no está disponible, no permite iniciar sesión o muestra un error de infraestructura, debe comunicarlo al administrador.

La ayuda contextual integrada en cada pestaña complementa este manual. Cuando exista una duda sobre un parámetro concreto, puede utilizarse el botón **Ayuda** de la pestaña correspondiente.

---

## 2. Qué puede hacer un usuario

Desde la interfaz web, un usuario puede, según las opciones habilitadas en su cuenta:

- iniciar sesión;
- seleccionar símbolos y periodo de análisis;
- configurar parámetros globales de la estrategia;
- activar y configurar indicadores técnicos;
- configurar mecanismos de protección de posiciones;
- guardar su configuración;
- lanzar un backtest;
- seguir el progreso de la ejecución;
- revisar el historial de resultados;
- consultar operaciones y gráficos;
- configurar notificaciones disponibles para su usuario;
- consultar este manual y las ayudas contextuales.

Las tareas de administración del servidor, usuarios, procesos, base de datos, código fuente y despliegue corresponden al administrador.

---

## 3. Acceso e inicio de sesión

1. Abra en el navegador la dirección de TradingCore proporcionada por el administrador.
2. Introduzca sus credenciales.
3. Tras autenticarse, accederá a la pantalla principal.

Si las credenciales no funcionan o la aplicación no responde, no intente reiniciar servicios ni modificar ficheros. Contacte con el administrador.

---

## 4. Recorrido general por la interfaz

La interfaz web se organiza en pestañas y subpestañas. Las principales áreas funcionales son:

- **Configuración**: parámetros globales e indicadores de la estrategia.
- **Símbolos**: activos y temporalidad del backtest.
- **Historial**: ejecuciones anteriores y resultados guardados.
- **Gráficos**: representación visual de precios, indicadores y operaciones.
- **Ficheros / Documentación**: acceso a documentación permitida para el usuario.

Dentro de **Configuración** existen subpestañas para:

- Global;
- EMA;
- RSI;
- MACD;
- ATR;
- Estocástico;
- Bollinger;
- Volumen / Margen de Seguridad (MoS).

Cambiar de una subpestaña a otra no guarda automáticamente los cambios en la base de datos. Los valores se mantienen en el formulario mientras no se recargue la página.

---

## 5. Guardar la configuración

El botón **Guardar Config** guarda la configuración actual del usuario.

### Cuándo conviene guardar

Guarde la configuración:

- después de realizar cambios que quiera conservar;
- antes de una acción que pueda recargar la pantalla;
- antes de cerrar sesión;
- antes de salir de la aplicación.

Cambiar entre subpestañas no obliga a guardar inmediatamente, pero una recarga puede hacer que se pierdan cambios todavía no persistidos.

### Fecha final

La fecha final del backtest se inicializa normalmente con el día anterior. Si se modifica manualmente para una ejecución, ese valor se utiliza en dicha ejecución y queda asociado a los resultados, aunque no forme parte de la configuración persistente habitual del usuario.

---

## 6. Configuración global

La pestaña **Global** reúne los parámetros generales que afectan a toda la estrategia.

Entre los parámetros habituales se encuentran:

- **Capital inicial (`cash`)**: capital con el que comienza la simulación.
- **Comisión (`commission`)**: coste aplicado a las operaciones simuladas.
- **Intervalo / temporalidad**: frecuencia de los datos utilizados, por ejemplo diario o semanal.
- **Stop / trailing base**: porcentaje de protección aplicado durante la evolución de una posición.
- **Notificación por correo**: permite solicitar una notificación al finalizar cuando esta función está habilitada.

Estos parámetros afectan al contexto de ejecución y gestión de riesgo, pero no todos generan señales de compra o venta.

---

## 7. Cómo interpreta TradingCore las señales

TradingCore combina varios tipos de condiciones. Para entender una estrategia conviene distinguir tres conceptos:

### 7.1 Señales de entrada

Son condiciones capaces de proponer una compra. Algunos indicadores pueden actuar como una vía de entrada propia.

### 7.2 Filtros

Un filtro no tiene por qué generar una compra por sí mismo. Puede limitar o bloquear una entrada propuesta por otra condición.

### 7.3 Señales de salida y protecciones

Las ventas pueden deberse a señales técnicas o a mecanismos de protección de la posición, como stop, trailing, break-even o swing.

Por tanto, activar más indicadores no significa necesariamente generar más compras. Algunos indicadores añaden señales y otros endurecen las condiciones de entrada.

---

## 8. Estrategia base y comportamiento B&H

Cuando no existe una señal técnica de compra activa, TradingCore puede utilizar una lógica base de entrada apoyada en la situación favorable de la EMA lenta.

Regla práctica:

- si no existen señales técnicas de entrada activas, la estrategia base puede actuar;
- al activar una señal técnica de entrada, dicha vía pasa a formar parte de la lógica de compra;
- los filtros globales siguen pudiendo bloquear una compra aunque exista una señal favorable.

El comportamiento exacto depende de los indicadores y filtros activados simultáneamente.

---

## 9. EMA

La **EMA (Exponential Moving Average)** es una media móvil que da más peso a los precios recientes. TradingCore utiliza una EMA rápida y una EMA lenta para identificar tendencia y cambios de dirección.

### Parámetros principales

- **Periodo EMA lenta**: controla la sensibilidad de la tendencia principal.
- **Periodo EMA rápida**: interviene especialmente en la lógica de cruce.
- **Cruce EMA**: puede utilizarse como señal de compra.
- **EMA lenta en mínimo**: puede actuar como condición de compra.
- **EMA lenta ascendente**: puede actuar como condición de compra.
- **EMA lenta en máximo**: puede utilizarse como condición de venta.
- **EMA lenta descendente**: puede utilizarse como condición de venta.

### Interpretación

Una EMA con periodos cortos reacciona antes a los cambios del precio, pero también puede producir más ruido. Una EMA con periodos largos es más estable, pero responde más tarde.

Use el botón **Ayuda** de la pestaña EMA para consultar las condiciones exactas configurables en la versión actual.

---

## 10. RSI

El **RSI (Relative Strength Index)** es un oscilador que mide la fuerza relativa del movimiento del precio.

### Parámetros principales

- **Periodo RSI**: número de velas utilizado para calcular el indicador.
- **Nivel bajo**: zona utilizada para condiciones asociadas a sobreventa.
- **Nivel alto**: zona utilizada para condiciones asociadas a sobrecompra.
- **Mínimo**: puede actuar como señal de compra.
- **Ascendente**: puede actuar como señal de compra.
- **Máximo**: puede actuar como señal de venta.
- **Descendente**: puede actuar como señal de venta.
- **Umbral de fuerza (`rsi_strength_threshold`)**: funciona como filtro global de fuerza y puede bloquear compras.

### Punto importante

El umbral de fuerza puede impedir una compra incluso cuando otra condición técnica sea favorable. Por ello debe interpretarse como un filtro adicional y no como una señal de entrada independiente.

El RSI también puede intervenir en configuraciones de trailing dinámico cuando esa opción está activada.

---

## 11. MACD

El **MACD (Moving Average Convergence Divergence)** compara una media exponencial rápida con una lenta y utiliza una línea de señal para identificar cambios de impulso. TradingCore permite elegir de forma independiente la lógica de compra y la de venta.

### Parámetros principales

- **Periodo rápido**: periodo de la EMA rápida.
- **Periodo lento**: periodo de la EMA lenta.
- **Periodo de señal**: periodo utilizado para calcular la línea Signal.
- **Lógica de compra**: `Cruce Up`, `Histograma Buy` o `Ninguna`.
- **Lógica de venta**: `Cruce Down`, `Histograma Sell` o `Ninguna`.

### Lógicas de compra

- **Cruce Up**: genera señal cuando la línea MACD cruza al alza la línea Signal.
- **Histograma Buy**: genera señal cuando el histograma pasa de cero o negativo a positivo.
- **Ninguna**: MACD no genera señales de compra. El indicador puede seguir activo para cálculo y visualización.

### Lógicas de venta

- **Cruce Down**: genera señal cuando la línea MACD cruza a la baja la línea Signal.
- **Histograma Sell**: genera señal cuando el histograma pasa de cero o positivo a negativo.
- **Ninguna**: MACD no genera señales de venta.

Las opciones de compra y venta son independientes. Por ejemplo, puede utilizarse `Cruce Up` para entrar y `Histograma Sell` para salir. Si la lógica de compra está en **Ninguna**, tener MACD activado no se considera por sí solo una vía técnica de compra y no desplaza el comportamiento de respaldo Buy & Hold.

Use el botón **Ayuda** de la pestaña MACD para consultar estas condiciones mientras configura la estrategia.

---

## 12. ATR

El **ATR (Average True Range)** mide volatilidad. En TradingCore se utiliza como filtro de rango de volatilidad aceptable.

### Funcionamiento práctico

- Si el ATR está dentro del rango configurado, no bloquea la entrada por este criterio.
- Si el ATR queda fuera del rango aceptado, la compra puede quedar bloqueada.
- Actúa como filtro y no como señal de compra independiente.

Puede ser útil para evitar operaciones en periodos excesivamente planos o excesivamente volátiles.

---

## 13. Estocástico

El oscilador **Estocástico** compara el cierre actual con el rango reciente del precio. TradingCore permite configurar tres variantes independientes: **Fast**, **Mid** y **Slow**.

Para cada variante puede seleccionarse una única lógica de compra y una única lógica de venta:

- **Compra - Mínimo**: exige que el estado de esa variante esté en mínimo.
- **Compra - Ascendente**: exige que el estado esté ascendiendo.
- **Compra - Ninguna**: esa variante no genera señal de compra.
- **Venta - Máximo**: genera salida cuando el estado está en máximo.
- **Venta - Descendente**: genera salida cuando el estado está descendiendo.
- **Venta - Ninguna**: esa variante no genera señal de venta.

La opción **Ninguna** desactiva la señal de ese lado; no debe interpretarse como una condición que se cumple automáticamente. Las variantes Fast, Mid y Slow se evalúan de forma independiente según su configuración.

## 14. Bandas de Bollinger

Las **Bandas de Bollinger** crean una envolvente alrededor de una media móvil central utilizando la volatilidad del precio.

En la lógica de compra validada actualmente, Bollinger solo aporta una señal técnica cuando está activo **y** `bb_buy_crossover` está habilitado. La señal se produce cuando el precio cruza al alza la banda inferior, confirmando una reversión desde esa zona.

Si `bb_buy_crossover` está desactivado, Bollinger no genera una compra por simple toque o permanencia bajo la banda inferior y no desplaza por sí solo la vía de respaldo Buy & Hold.

Con `bb_sell_crossover` activado, Bollinger genera una salida técnica cuando el precio cruza a la baja la banda superior o cuando cruza a la baja la SMA central.

## 15. Volumen

El filtro de **Volumen** confirma que una posible entrada tenga suficiente participación del mercado. En la implementación actual utiliza como referencia una **SMA de volumen (V-SMA)**.

La condición base exige que el volumen actual sea superior a:

`V-SMA × volume_avg_multiplier`

Además pueden activarse estados adicionales. `volume_minimo` exige que la V-SMA esté en mínimo dentro de la ventana configurada y `volume_ascendente` exige que la V-SMA esté realmente en tendencia ascendente.

El antiguo contador interno de veces que el volumen superaba su media ya no define el estado "ascendente". Si se seleccionan varios estados de volumen, basta con que se cumpla uno de los estados seleccionados, además de cumplirse siempre el umbral de nivel.

Volumen actúa como filtro de entrada: no crea por sí solo una compra si no existe antes una señal técnica válida.

## 16. Margen de Seguridad (MoS)

El **Margen de Seguridad (MoS)** se calcula globalmente para cada activo en el módulo fundamental. Cada usuario configura si su estrategia lo usa como filtro y con qué parámetros. Cuando está activo, exige que el valor global de MoS supere `margen_seguridad_threshold`.

Pueden añadirse dos confirmaciones:

- **`margen_seguridad_minimo`**: exige que el MoS esté en estado mínimo.
- **`margen_seguridad_ascendente`**: exige que el MoS esté ascendiendo.

Las confirmaciones activadas se combinan con lógica **AND**: si se activan mínimo y ascendente, ambas deben cumplirse además del umbral. Si faltan los datos necesarios de MoS, el filtro activo bloquea la entrada.

MoS se aplica como filtro **AND posterior** a una señal técnica de compra: puede autorizarla o bloquearla, pero no genera por sí solo una señal de compra ni una señal de venta independiente. `margen_seguridad_threshold`, `margen_seguridad_minimo` y `margen_seguridad_ascendente` pertenecen a la configuración de cada usuario. Es distinto del filtrado fundamental previo del universo de símbolos.

## 17. Cómo se combinan los indicadores

No debe interpretarse cada indicador de forma aislada. El resultado depende del conjunto de señales y filtros activos.

Un ejemplo conceptual:

1. EMA o RSI detectan una condición que podría proponer una compra.
2. El filtro global de RSI comprueba que exista suficiente fuerza.
3. ATR comprueba que la volatilidad esté dentro del rango permitido.
4. Volumen puede exigir confirmación de actividad.
5. MoS puede exigir una valoración fundamental suficientemente atractiva.
6. Si todos los filtros obligatorios son favorables, se permite la entrada.

Una estrategia con muchos filtros suele realizar menos operaciones. Una estrategia con menos filtros puede realizar más operaciones, pero estar más expuesta a señales débiles.

---

## 18. Stops y protección de posiciones

TradingCore puede combinar varias protecciones sobre una misma posición. Estas protecciones no son necesariamente excluyentes: pueden coexistir y endurecer el nivel de stop.

### 18.1 Trailing stop

El trailing acompaña al precio cuando la posición evoluciona favorablemente. El stop puede subir o mantenerse, pero no debe relajarse bajando a un nivel menos protector.

### 18.2 Trailing dinámico según RSI

Cuando está activado, el porcentaje de trailing puede cambiar en función del nivel del RSI.

### 18.3 Break-even

En la implementación actual, el parámetro `breakeven_trigger_pct` se utiliza para calcular un suelo de protección respecto al precio de entrada:

`precio_entrada × (1 - porcentaje)`

No debe interpretarse como un porcentaje mínimo de beneficio necesario para "activar" el break-even.

Ejemplo conceptual: con una entrada a 100 y un porcentaje del 2 %, el suelo calculado es 98.

### 18.4 Stop por swing

El stop por swing utiliza mínimos recientes y un margen configurable. Si propone un nivel más protector que otros stops activos, puede convertirse en el stop efectivo.

### Regla práctica

Cuando hay varios niveles candidatos, el sistema busca conservar el nivel más protector compatible con la lógica implementada.

---

## 19. Selección de símbolos y temporalidad

Antes de lanzar un backtest:

1. seleccione los símbolos que desea analizar;
2. confirme el intervalo o temporalidad;
3. revise el rango de fechas;
4. compruebe que la configuración de indicadores es la deseada;
5. guarde la configuración si quiere conservar los cambios.

Cuando el filtro fundamental está activo, se aplica a los mismos símbolos seleccionados para el backtest, sin ampliar esa lista. La selección fundamental usa la fecha global más reciente disponible; un resultado no evaluable por datos insuficientes no equivale a un activo desestimado por sus métricas.

### Filtro fundamental y dashboard

El switch **Filtro Fundamental** hace que el backtest intente actualizar la información fundamental de los símbolos seleccionados. Yahoo mantiene la actualización operativa y Alpha Vantage aporta histórico cuando el administrador ha configurado `ALPHA_VANTAGE_KEY`. Si no existe esa variable, se omite el bootstrap Alpha Vantage; el backtest puede continuar con los datos disponibles.

Desde **Fundamentales** se accede a `/fundamentals`; al seleccionar un símbolo se abre `/fundamentals/<symbol>`. El dashboard solo muestra símbolos configurados para el usuario y es de solo lectura: muestra datos almacenados, no descarga proveedores ni recalcula ratios.

La **Cobertura** representa periodos EPS históricos de la caché normalizada, no la existencia de una valoración: 0 = Sin datos; 1–3 = Cobertura insuficiente; 4–19 = Cobertura parcial; 20 o más = Cobertura suficiente. LTM EPS resume cuatro trimestres completos y necesita cuatro periodos válidos. PER M5Y es una media de 20 PER trimestrales válidos; **No calculado** no significa necesariamente que exista un error. La disponibilidad de métricas Full Ratio se muestra aparte.

`fiscal_date` identifica el periodo contable. `reportedDate` es la fecha de publicación: el backtest no considera el dato disponible antes de esa fecha para evitar look-ahead. El estado Bootstrap describe el progreso de la carga histórica; el icono de ayuda junto al estado explica cada valor.

La temporalidad modifica la serie de datos utilizada por todos los indicadores. Una configuración diaria y una semanal pueden producir resultados muy distintos aunque el resto de parámetros sea idéntico.

---

## 20. Lanzar un backtest

Una vez revisada la configuración:

1. seleccione los símbolos;
2. revise los parámetros globales;
3. active los indicadores deseados;
4. pulse **Lanzar Backtest**.

Durante la ejecución se muestra un modal de progreso con:

- fase actual;
- porcentaje de avance;
- mensajes o bitácora de eventos;
- estado final de la ejecución.

El botón **OK** permanece bloqueado hasta que la ejecución termina o se produce un error. Al cerrar el modal una vez finalizado, la pantalla se actualiza para reflejar el historial más reciente.

No es necesario refrescar manualmente la página para comprobar si el backtest ha terminado.

---

## 21. Interpretar los resultados

Los resultados deben analizarse conjuntamente. Una única métrica no permite valorar una estrategia por sí sola.

Entre las métricas habituales pueden encontrarse:

- rentabilidad;
- número de operaciones;
- porcentaje de operaciones ganadoras;
- beneficio y pérdida;
- drawdown;
- evolución temporal;
- comparación con la estrategia base o referencia disponible.

### Rentabilidad

Indica la variación del capital durante el periodo simulado.

### Número de operaciones

Permite saber si el resultado procede de muchas operaciones o de unos pocos casos aislados.

### Win Rate

Es la proporción de operaciones positivas. Un Win Rate alto no implica necesariamente una estrategia mejor si las pérdidas medias son mucho mayores que las ganancias medias.

### Drawdown

Representa una caída desde un máximo previo de la curva de capital. Es una medida importante del riesgo experimentado durante la simulación.

---

## 22. Revisar operaciones

Al analizar operaciones individuales, revise al menos:

- fecha de entrada;
- fecha de salida;
- precio de entrada;
- precio de salida;
- resultado de la operación;
- motivo técnico registrado para la entrada o salida;
- stop aplicado cuando corresponda.

Las razones técnicas ayudan a entender qué indicadores o protecciones intervinieron en cada operación.

---

## 23. Gráficos

El visor de gráficos permite revisar visualmente la evolución del activo y relacionarla con las operaciones generadas por la estrategia.

Al interpretar un gráfico:

1. identifique la tendencia general del precio;
2. localice las entradas y salidas;
3. observe la situación de los indicadores activos;
4. compruebe si las salidas coinciden con señales técnicas o stops;
5. compare el comportamiento visual con las métricas del backtest.

Los gráficos son una herramienta de análisis complementaria; no sustituyen la revisión de resultados y operaciones.

---

## 24. Historial

La pestaña **Historial** permite consultar ejecuciones ya guardadas.

Utilícela para:

- revisar backtests anteriores;
- comparar configuraciones y periodos;
- volver a consultar métricas;
- acceder a resultados y gráficos disponibles;
- verificar la configuración utilizada en una ejecución concreta.

Cuando compare dos backtests, compruebe que símbolos, fechas, intervalo, capital, comisiones e indicadores sean comparables.

---

## 25. Notificaciones

Si su usuario tiene habilitada la opción de correo, puede configurar el envío de una notificación al finalizar determinadas ejecuciones.

La configuración de correo no modifica la lógica de compra o venta. Solo afecta a la notificación.

El usuario no necesita arrancar ni detener procesos de servidor para utilizar esta función. La disponibilidad técnica del servicio corresponde al administrador.

---

## 26. Ayuda contextual

Las pestañas Global, EMA, RSI, MACD, ATR, Estocástico, Bollinger y Volumen/MoS disponen de botón **Ayuda**.

Estas ayudas explican, según la pestaña:

- qué mide o configura el apartado;
- cómo lo utiliza TradingCore;
- parámetros disponibles;
- condiciones de compra;
- condiciones de venta o bloqueo;
- relación con otros filtros;
- ejemplos;
- advertencias sobre el comportamiento real actual.

Cuando el manual y una ayuda contextual parezcan describir de forma distinta una opción concreta, comuníquelo al administrador para que la documentación sea revisada.

---

## 27. Problemas frecuentes

### No puedo iniciar sesión

Compruebe usuario y contraseña. Si persiste, contacte con el administrador.

### La aplicación no carga

No intente reiniciar el servidor. Informe al administrador.

### He cambiado parámetros y después han desaparecido

Es probable que la página se haya recargado antes de guardar. Utilice **Guardar Config** antes de salir o provocar una recarga.

### El backtest termina sin operaciones

Puede deberse a una combinación demasiado restrictiva de señales y filtros, al periodo seleccionado o a la falta de condiciones válidas en los datos analizados.

Revise especialmente:

- indicadores de compra activos;
- filtro RSI;
- rango ATR;
- volumen;
- MoS;
- fechas y temporalidad.

### El backtest muestra un error

Anote el mensaje mostrado y comuníquelo al administrador si el problema se repite.

### Un resultado parece extraño

Revise:

- rango de fechas;
- intervalo;
- símbolos;
- capital y comisión;
- indicadores activos;
- operaciones individuales;
- razones de entrada y salida;
- stops y protecciones.

### No recibo el correo esperado

Compruebe que la opción de notificación esté activada y que la dirección sea correcta. Si todo es correcto, contacte con el administrador.

---

## 28. Buenas prácticas de uso

- Cambie pocos parámetros cada vez cuando esté comparando estrategias.
- Guarde una configuración antes de abandonar la pantalla.
- Compare estrategias utilizando periodos y símbolos equivalentes.
- No valore una estrategia únicamente por rentabilidad.
- Revise también drawdown, número de operaciones y operaciones individuales.
- Utilice las ayudas contextuales antes de modificar parámetros cuyo efecto no conozca.
- Registre qué cambios ha realizado cuando esté realizando comparaciones sistemáticas.

---

## 29. Glosario

**ATR**: indicador de volatilidad basado en el rango verdadero del precio.
**Backtest**: simulación de una estrategia sobre datos históricos.
**Bandas de Bollinger**: bandas construidas alrededor de una media utilizando desviaciones de precio.
**B&H / Buy & Hold**: referencia o lógica base de mantener una posición según las condiciones implementadas.
**Break-even**: mecanismo de protección relacionado con el precio de entrada.
**Comisión**: coste simulado por operar.
**Drawdown**: caída desde un máximo previo de la curva de capital.
**EMA**: media móvil exponencial.
**Estocástico**: oscilador que compara el cierre con el rango reciente.
**Filtro**: condición que puede permitir o bloquear una señal generada por otra lógica.
**MACD**: indicador de tendencia e impulso basado en medias exponenciales.
**MoS**: Margen de Seguridad; filtro fundamental relacionado con valoración.
**RSI**: oscilador de fuerza relativa.
**Señal de compra**: condición que propone una entrada.
**Señal de venta**: condición que propone el cierre de una posición.
**Stop Loss**: nivel de protección destinado a limitar pérdidas.
**Swing low**: mínimo local reciente utilizado como referencia para determinadas protecciones.
**Trailing stop**: stop que acompaña favorablemente la evolución del precio.
**Win Rate**: porcentaje de operaciones positivas sobre el total.

---

## 30. Cuándo contactar con el administrador

Contacte con el administrador cuando:

- no pueda acceder a la aplicación;
- la aplicación no esté disponible;
- aparezca un error persistente;
- falten datos o símbolos esperados;
- una ayuda contextual contradiga el comportamiento observado;
- no funcionen notificaciones correctamente configuradas;
- necesite una función no disponible en la interfaz.

No es necesario que el usuario acceda al código, a la base de datos ni a procesos del sistema para resolver estas incidencias.

---

## 31. Estado de este manual

Este manual forma parte de la documentación viva de TradingCore. Debe revisarse siempre que cambie una función visible para el usuario, un parámetro, una pestaña, una regla de operación o una ayuda contextual.

Las modificaciones puramente técnicas que no afecten al comportamiento visible del usuario no requieren cambiar este manual.
