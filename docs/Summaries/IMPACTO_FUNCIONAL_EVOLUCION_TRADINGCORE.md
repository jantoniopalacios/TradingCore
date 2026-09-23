# Impacto funcional de la evolución de TradingCore

**Última actualización:** 20/09/2026
**Estado:** documento vivo
**Audiencia:** propietario del sistema, administrador y cualquier persona que necesite entender cómo los cambios del plan pueden afectar a los resultados sin entrar en detalles de programación.

## 1. Objetivo

Este documento explica, en lenguaje no técnico, qué implicaciones tienen los cambios realizados durante la ejecución del plan de mejora de TradingCore respecto a la aplicación que se utilizaba anteriormente.

El objetivo no es describir código, sino responder a preguntas prácticas:

- ¿qué podía hacer la aplicación anterior de forma distinta a lo que mostraba la pantalla?;
- ¿qué tipos de estrategias podían verse afectados?;
- ¿cómo podía cambiar el número de operaciones, las fechas de entrada o salida y las métricas del backtest?;
- ¿qué resultados históricos conviene volver a ejecutar?;
- ¿qué cambios son solo documentales u operativos y no alteran una estrategia?

Este documento debe actualizarse en cada bloque restante del plan, incluso cuando el nuevo bloque no cambie los resultados de las estrategias. En ese caso se dejará constancia explícita de que no existe impacto funcional esperado.

A partir de este documento se mantendrá también la trazabilidad sobre qué resultados obtenidos con versiones anteriores siguen siendo directamente comparables con los actuales y cuáles requieren repetir el backtest.

## 2. Cómo interpretar los resultados anteriores

No todos los backtests ejecutados con versiones anteriores de TradingCore deben considerarse incorrectos.

La regla práctica es:

- si una estrategia no utilizaba ninguna de las funciones afectadas por una corrección, sus resultados no se consideran alterados por esa corrección;
- si utilizaba una función afectada, el resultado anterior debe considerarse **pendiente de revalidación**;
- una revalidación significa volver a ejecutar el mismo símbolo, fechas, temporalidad, capital, comisiones y configuración con la versión corregida y comparar ambos resultados;
- una diferencia entre el resultado antiguo y el nuevo no implica necesariamente que la estrategia sea mejor o peor: significa que ahora la aplicación está ejecutando con mayor fidelidad la configuración seleccionada por el usuario.

Las métricas que pueden cambiar como consecuencia de una corrección funcional incluyen, entre otras:

- número de operaciones;
- fechas y precios de entrada;
- fechas y precios de salida;
- duración de las operaciones;
- rentabilidad;
- Win Rate;
- drawdown;
- beneficio o pérdida por operación;
- motivo registrado de entrada o salida.

## 3. Cambios sin impacto esperado sobre los resultados de las estrategias

### 3.1 Manual de Usuario y reorganización de la documentación

Se creó un Manual de Usuario orientado a personas que utilizan únicamente la interfaz web y se separó la documentación de usuario de la documentación técnica.

**Implicación para los resultados:** ninguna.

Este cambio modifica cómo se explica y se accede a la documentación, pero no modifica las reglas de compra, venta o filtrado de una estrategia.

### 3.2 Control de acceso a la documentación por rol

El usuario normal pasó a ver solo la documentación funcional permitida, mientras que el administrador mantiene acceso a la documentación técnica.

**Implicación para los resultados:** ninguna.

Afecta a permisos de consulta de documentación, no al motor de backtest.

### 3.3 Consolidación documental transversal

Se actualizaron el Manual de Usuario, las guías, la referencia de indicadores, el plan, el índice, las convenciones y el Manual operativo para reflejar el comportamiento corregido.

**Implicación para los resultados:** ninguna por sí misma.

Su importancia consiste en evitar que una persona configure una estrategia basándose en una explicación antigua o contradictoria.

## 4. Persistencia de opciones de configuración

Durante la auditoría se detectó que algunas opciones de tipo activado/desactivado no se guardaban o recuperaban de forma completamente coherente. Se corrigieron, entre otras, las opciones relacionadas con ATR, mínimo de Margen de Seguridad, mínimo de Volumen y la representación del stop por swing.

### Qué podía ocurrir antes

Una persona podía guardar una configuración creyendo que una determinada opción quedaba activada o desactivada y, al recuperar esa configuración, la aplicación podía no reconstruir exactamente la intención original.

Esto no significa que todas las configuraciones guardadas fueran erróneas. El riesgo se concentra en las estrategias que dependían de esas opciones concretas.

### Cómo podía afectar a un backtest

Una condición podía quedar aplicada cuando el usuario esperaba que no lo estuviera, o al revés. En consecuencia:

- podían aparecer operaciones que el filtro pretendía evitar;
- podían desaparecer operaciones que el usuario esperaba permitir;
- una estrategia recuperada de una configuración guardada podía producir resultados diferentes a una configuración aparentemente igual introducida manualmente.

### Resultados que conviene revalidar

Conviene volver a ejecutar backtests anteriores que dependieran de:

- filtro ATR activado/desactivado;
- condición de mínimo de Margen de Seguridad;
- condición de mínimo de Volumen;
- stop por swing cuando se recuperaba desde una configuración guardada.

## 5. MACD

Se corrigió la correspondencia entre las opciones visibles de MACD y la lógica realmente ejecutada por el motor.

La aplicación permite elegir una lógica de compra y otra de venta, por cruce de líneas o por cambio de signo del histograma, además de la opción de no utilizar señal en uno de los lados.

### Qué podía ocurrir antes

La opción seleccionada en pantalla no estaba completamente alineada con la interpretación interna. En especial, las opciones basadas en histograma y la opción de no utilizar una señal no tenían una correspondencia suficientemente clara y garantizada.

### Cómo podía afectar a un backtest

Una estrategia con MACD podía:

- entrar en una fecha diferente a la esperada;
- no entrar cuando el usuario esperaba una señal;
- salir antes o después;
- mantener una posición que debería haberse cerrado;
- utilizar o dejar de utilizar la vía de respaldo Buy & Hold de forma distinta a la intención del usuario.

Cualquiera de estas diferencias puede alterar de forma importante el número de operaciones y las métricas finales.

### Resultados que conviene revalidar

Todos los backtests anteriores que utilizaran MACD como señal de compra o venta, especialmente los que utilizaran las opciones de histograma o la opción `Ninguna`.

## 6. Estocástico Fast, Mid y Slow

Se corrigió la conexión entre las opciones de compra/venta seleccionadas para cada variante del Estocástico y la lógica ejecutada.

### Qué podía ocurrir antes

Las selecciones visibles de compra y venta podían no gobernar realmente el comportamiento del motor. Además, seleccionar que una variante no aportara señal no garantizaba correctamente que esa vía quedara desactivada.

### Cómo podía afectar a un backtest

Una estrategia podía:

- comprar aunque el usuario hubiera seleccionado no utilizar esa señal;
- utilizar una condición distinta de la seleccionada;
- cerrar o mantener una posición en momentos distintos a los esperados;
- generar más o menos operaciones que la estrategia configurada visualmente.

### Resultados que conviene revalidar

Todos los backtests anteriores que utilizaran Stochastic Fast, Mid o Slow como señal de compra o de venta.

## 7. Bandas de Bollinger

Se corrigió la lógica de compra de Bollinger y su relación con la vía de respaldo Buy & Hold.

### Qué podía ocurrir antes

Al desactivar la opción de compra por cruce, el motor podía interpretar esa situación como una compra por simple toque o permanencia bajo la banda inferior.

Además, tener Bollinger activo podía impedir la vía de respaldo Buy & Hold aunque no existiera una condición de compra Bollinger realmente utilizable.

### Cómo podía afectar a un backtest

Podían darse dos tipos de diferencia:

1. **Operaciones adicionales:** compras producidas por tocar o permanecer por debajo de la banda inferior aunque el usuario no hubiera configurado esa lógica como señal.
2. **Operaciones ausentes:** la estrategia podía dejar de utilizar la entrada de respaldo Buy & Hold simplemente por tener Bollinger activo.

Esto puede cambiar tanto el número de operaciones como el momento en que comienza una posición y, por tanto, toda su evolución posterior.

### Situación actual

La compra Bollinger queda ligada al cruce alcista sobre la banda inferior cuando la opción correspondiente está habilitada.

La salida Bollinger se activa con `bb_sell_crossover` cuando el precio cruza a la baja la banda superior o la SMA central. La interfaz y la documentación ya reflejan expresamente ambas condiciones.

`bb_window_state` se ha retirado de la interfaz porque no participa actualmente en la lógica de señales o estados. Se mantiene en configuración por compatibilidad con configuraciones existentes.

### Resultados que conviene revalidar

Backtests anteriores con Bollinger activo, especialmente cuando la compra por cruce estaba desactivada o cuando se esperaba que Buy & Hold siguiera disponible.

## 8. Margen de Seguridad (MoS)

Se corrigió el filtro de Margen de Seguridad para que las opciones seleccionadas por el usuario tengan efecto real.

### Qué podía ocurrir antes

La opción que exigía que el Margen de Seguridad estuviera en un mínimo estaba disponible en configuración, pero no se aplicaba realmente al decidir una entrada.

### Cómo funciona tras la corrección

Cuando MoS está activo:

- debe superar el umbral configurado;
- si se exige estado mínimo, debe cumplirse;
- si se exige tendencia ascendente, debe cumplirse;
- si se exigen ambas confirmaciones, deben cumplirse las dos.

### Cómo podía afectar a un backtest

La versión anterior podía permitir compras que el usuario esperaba que fueran rechazadas por no cumplir la condición de mínimo.

Por tanto, una estrategia con ese filtro podía haber tenido:

- más operaciones de las previstas;
- entradas en activos o fechas que no cumplían toda la selección realizada;
- métricas de rentabilidad y riesgo calculadas sobre un conjunto de operaciones distinto del deseado.

### Resultados que conviene revalidar

Backtests anteriores con Margen de Seguridad activo, especialmente cuando estaba seleccionada la condición de mínimo o se combinaban mínimo y ascendente.

## 9. Volumen

Se corrigieron tanto la explicación de la interfaz como la interpretación de la condición de Volumen.

### Qué podía ocurrir antes

Había dos problemas relevantes para una persona no técnica:

1. La pantalla hablaba de una media exponencial de volumen, mientras que el cálculo utilizado realmente era una media simple.
2. La opción descrita como volumen ascendente no comprobaba realmente que la media de volumen estuviera ascendiendo. Se basaba en un contador interno de cuántas veces el volumen había superado su media, utilizando además un umbral que no era visible como parámetro normal de la interfaz.

### Cómo funciona tras la corrección

La referencia se denomina V-SMA porque es una media móvil simple de volumen.

La condición de volumen ascendente significa ahora que esa V-SMA está realmente ascendiendo.

Además, el volumen actual debe superar la V-SMA multiplicada por el factor configurado. Las condiciones adicionales de estado se aplican según la selección realizada.

### Cómo podía afectar a un backtest

Dos estrategias visualmente iguales podían estar siendo interpretadas de una forma que el usuario no tenía manera razonable de deducir desde la pantalla.

Esto podía provocar:

- entradas aceptadas aunque la tendencia de volumen no estuviera ascendiendo;
- entradas rechazadas aunque sí lo estuviera;
- diferencias en el número de operaciones;
- diferencias en rentabilidad y drawdown derivadas de seleccionar un conjunto diferente de entradas.

### Resultados que conviene revalidar

Conviene revalidar los backtests anteriores con filtro de Volumen activo cuando utilizaban la condición de volumen ascendente. También conviene revisar aquellos cuya configuración se hubiera calibrado suponiendo que la referencia era una EMA, ya que el cálculo utilizado por la aplicación era en realidad una SMA.

## 10. Resumen de revalidación de resultados anteriores

| Configuración utilizada en el backtest antiguo | Revalidación recomendada | Motivo |
| --- | --- | --- |
| Solo cambios documentales / permisos | No por este motivo | No cambian reglas de estrategia |
| ATR guardado/recuperado | Sí, si dependía de su estado activado/desactivado | Persistencia de configuración |
| Stop por swing recuperado desde configuración | Sí, si su activación era relevante | Representación/recuperación del estado |
| MACD | Sí | Señales de compra/venta corregidas |
| Stochastic Fast/Mid/Slow | Sí | Selección UI y ejecución corregidas |
| Bollinger | Sí | Compra y relación con Buy & Hold corregidas |
| MoS | Sí | Condiciones mínimo/ascendente ahora se aplican |
| Volumen | Sí | SMA y significado de ascendente corregidos |
| Estrategias que no usan ninguna función anterior | No por estas correcciones | No hay evidencia de impacto directo |

## 11. Qué no puede concluirse solo con estas correcciones

Estas correcciones permiten afirmar que determinadas configuraciones se ejecutan ahora de forma más coherente con lo seleccionado en la interfaz.

No permiten afirmar por sí solas que:

- una estrategia concreta vaya a ganar más;
- una estrategia vaya a tener menor riesgo;
- los resultados nuevos vayan a ser mejores que los antiguos;
- todo backtest antiguo sea inválido.

Para conocer el efecto real sobre una estrategia concreta hay que repetir el backtest con exactamente las mismas condiciones y comparar.

## 12. Registro vivo de los siguientes bloques

Esta sección se actualizará al cerrar cada uno de los bloques restantes del plan.

### 20/09/2026 - Consolidación documental transversal

**Estado:** completada.
**Commit:** `0c8f5a2 docs: consolidar auditoria de indicadores`.

**Impacto funcional sobre resultados:** ninguno adicional. El cambio consolida y explica modificaciones funcionales ya realizadas.

### Tests de lógica combinada

**Estado:** completado.

Se ha ampliado la cobertura automática para comprobar cómo interactúan entre sí las señales técnicas, los filtros globales, el modo Buy & Hold y la gestión de stops.

Las pruebas confirman, entre otros casos, que:

- las señales técnicas de compra se combinan mediante lógica OR;
- los filtros globales pueden bloquear una señal de compra válida;
- Buy & Hold solo actúa cuando no hay una vía técnica de compra habilitada;
- RSI global puede bloquear también una entrada Buy & Hold;
- ATR, Volumen y Margen de Seguridad actúan como filtros excluyentes;
- las señales técnicas de venta se combinan mediante OR;
- trailing, break-even y swing conservan el stop más protector y el stop no retrocede.

**Impacto sobre resultados históricos:** ninguno esperado por este bloque.

No se ha modificado la lógica de trading ni los parámetros utilizados por las estrategias. Este trabajo añade pruebas de regresión para fijar el comportamiento ya existente y detectar cambios accidentales en el futuro.

Por tanto, este bloque no obliga por sí mismo a repetir backtests anteriores.

### Bloque posterior - Bollinger y limpieza EMA/RSI

**Estado:** completado.

Se ha alineado la interfaz y la documentación con el comportamiento real de la salida Bollinger, se ha retirado `bb_window_state` de la UI manteniéndolo únicamente por compatibilidad de configuración, y se han limpiado comentarios/docstrings legacy de EMA/RSI. No se ha modificado la lógica de trading en este bloque.


### Impacto sobre resultados históricos

No se espera un impacto adicional en resultados de backtest por este bloque:

- la lógica Bollinger de salida ya existía y no se ha cambiado;
- `bb_window_state` no tenía efecto funcional sobre señales o estados;
- los cambios EMA/RSI son exclusivamente de documentación interna y comentarios;
- se ha añadido cobertura de regresión para la salida Bollinger por SMA central.

Por tanto, este bloque no obliga por sí mismo a repetir backtests anteriores.


### Pendiente posterior - Operación de la aplicación web

**Estado:** pendiente.

El objetivo principal es hacer más fiable el arranque/parada y evitar instancias antiguas de la aplicación. En principio es un cambio operativo y no debería cambiar el cálculo de las estrategias, salvo que durante la revisión se detecte un defecto funcional adicional.

### Pendiente posterior - Datos fundamentales y proveedores

**Estado:** pendiente.

Este bloque sí puede tener implicaciones sobre la información utilizada por filtros fundamentales. Antes de introducir cambios se documentará qué datos cambian, desde qué fecha y qué backtests pueden dejar de ser directamente comparables.

### Pendiente posterior - Rendimiento, scheduler y limpieza legacy

**Estado:** pendiente.

Las optimizaciones de rendimiento no deben alterar resultados. El scheduler puede afectar a cuándo se ejecutan procesos, no a la lógica matemática de una estrategia. Cualquier excepción detectada se documentará expresamente.

## 13. Regla de mantenimiento de este documento

Al cerrar cada bloque del plan se debe añadir una entrada que indique:

1. qué se ha cambiado en términos comprensibles para una persona no técnica;
2. si cambia o no el comportamiento de una estrategia;
3. qué configuraciones pueden verse afectadas;
4. qué métricas podrían variar;
5. si deben reejecutarse backtests históricos;
6. commit o checkpoint que introduce el cambio;
7. incertidumbres o aspectos todavía pendientes.

Si un bloque no tiene impacto funcional esperado, debe registrarse igualmente con la frase **“sin impacto funcional esperado sobre los resultados de las estrategias”**.
