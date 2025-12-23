# 🏛️ DOCUMENTACIÓN DE ARQUITECTURA (Backend / Motor de Trading)

Este documento describe la estructura modular, las responsabilidades de los componentes y las interfaces clave del Motor Central (`trading_engine`).

---

## 1. Diseño Arquitectónico: Monorepo Modular

El proyecto `TradingCore` sigue una arquitectura de Monorepo Modular. Múltiples proyectos de ejecución (Escenarios) consumen una única biblioteca central de lógica (el Motor).

- **Principio Clave:** El **Motor Central** es la única Fuente de Verdad para la lógica de Trading. Los Escenarios solo gestionan la **Ejecución**, la **Configuración** y la **Comunicación** (Backtesting, Live Trading, Web App).

| Componente | Ubicación | Rol Principal |
| :--- | :--- | :--- |
| **Motor Central** | `engines/trading_engine/` | Lógica de Negocio (Decisión), Cálculos de Indicadores, Gestión de Datos Base. |
| **Escenarios** | `scenarios/` | Puntos de entrada para la ejecución (ej. `BacktestLocal`, `TradingWebLive`). |

## 2. Estructura del Motor (`trading_engine`)

### 2.1. Módulo `core` (`src/trading_engine/core/`)

Contiene las funciones *controladoras* que son llamadas en cada tick o barra de precio.

| Archivo | Interfaz Clave | Responsabilidad |
| :--- | :--- | :--- |
| `Logica_Trading.py` | `check_buy_signal(strategy_self)` | Determina la señal de **Entrada**. |
| `Logica_Trading.py` | `manage_existing_position(strategy_self)` | Gestiona el **Riesgo** y la **Salida** (SL/TP/Trailing). |

> **IMPORTANTE:** Estas funciones deben ser **puras** en cuanto a la lógica de negocio. No deben contener lógica de ejecución del backtest (ej. `self.buy()`).

### 2.2. Módulo `indicators` (`src/trading_engine/indicators/`)

Contiene la implementación de indicadores técnicos y filtros complejos.

- **Convención:** Los indicadores deben implementarse como clases o funciones que devuelven series de datos (`pd.Series`) o clases *Helper* que facilitan la evaluación (`StochHelper`).

## 3. Interfaz de la Estrategia (Clase `System`)

La clase `System` (ubicada en cada `estrategia_system.py`) es la interfaz de comunicación entre el entorno de ejecución (Backtesting) y el Motor Central.

**Responsabilidades de `System`:**

1.  **Definición de Parámetros:** Declara los atributos de configuración (ej. `ema_slow_period = 50`).
2.  **Inicialización (`init`)**: Calcula todos los indicadores necesarios y los adjunta a `self` (ej. `self.ema_slow = self.I(...)`).
3.  **Delegación (`next`)**: Llama a las funciones del Motor Central:
    ```python
    if self.position:
        manage_existing_position(self)
    else:
        if check_buy_signal(self):
            self.buy()
    ```

---

## 4. Guía para Desarrolladores

Para añadir una nueva funcionalidad (ej. un nuevo filtro de volumen):

1.  **Implementación del Filtro:** Implementar el cálculo en `engines/trading_engine/indicators/`.
2.  **Exposición:** Asegurar que el cálculo se realice y se adjunte a `self` en el método `System.init()`.
3.  **Uso:** Modificar las funciones `check_buy_signal()` o `manage_existing_position()` en `Logica_Trading.py` para utilizar el nuevo filtro.

## 5. Flujo de Datos y Jerarquía de Decisión
El motor utiliza un flujo unidireccional para garantizar que las decisiones sean consistentes y auditables.

# 5.1. Ciclo de Vida de un Tick/Vela
Cada vez que el entorno de ejecución (ej. backtesting.py) procesa una nueva vela, se dispara el siguiente flujo:

Sincronización: La clase System actualiza los punteros de los indicadores (self.I).

Filtrado Técnico: Logica_Trading.py itera sobre los filtros activos (EMA, RSI, BB, MACD, etc.).

Consolidación de Razones: Si un indicador emite una señal, añade su métrica al diccionario technical_reasons.

Ejecución: Solo si se cumplen las condiciones lógicas (AND/OR configurados), el Motor devuelve el control al Escenario para ejecutar la orden.

# 5.2. El Diccionario de Trazabilidad (technical_reasons)
Para evitar el comportamiento de "caja negra", el motor implementa un sistema de inyección de texto dinámico. Esto permite que el registro de operaciones sea humano-legible:

Entrada de Datos: Cada módulo en indicators/ es responsable de redactar su propia justificación técnica (ej. f"Sobreventa (Precio {p} < Banda {b})").

Salida de Datos: Este diccionario se exporta directamente al trades_log.csv, permitiendo una auditoría inmediata de por qué falló o acertó una estrategia.

## 6. Manejo de Errores y Robustez
Seguridad de Atributos: El motor utiliza getattr(strategy_self, 'nombre_parametro', por_defecto) para evitar que la falta de una variable en el archivo .env detenga la ejecución.

Desacoplamiento: Los indicadores devuelven booleanos y cadenas de texto, nunca ejecutan órdenes directamente, lo que permite testear la lógica de compra/venta sin necesidad de un entorno de backtesting activo.