# Convenciones de Documentacion

Este documento define el formato recomendado para mantener uniformidad en todos los archivos `.md` de `docs/`.

## 1. Estructura base

Cada documento debe seguir, cuando aplique, esta estructura:

1. Titulo (`# ...`) claro y sin emojis.
2. Objetivo o alcance (`## Objetivo`).
3. Contenido principal en secciones numeradas o por bloques funcionales.
4. Pasos de uso o validacion (si es guia operativa).
5. Referencias o enlaces relacionados.

## 2. Titulos y secciones

- Usar `#`, `##`, `###` en orden jerarquico.
- Evitar estilos visuales decorativos (ASCII art, separadores excesivos).
- Evitar prefijos con iconos en cabeceras.
- Mantener nombres cortos y descriptivos.

## 3. Bloques de codigo

- Usar bloques fenced con lenguaje:
  - `powershell` para comandos Windows.
  - `bash` para comandos shell genericos.
  - `python` para ejemplos de codigo.
  - `text` para salidas esperadas o URLs.
- No envolver documentos completos en bloques ` ```markdown `.
- Incluir solo comandos validos en el repo actual.

## 4. Tono y redaccion

- Tono tecnico, directo y consistente.
- Evitar lenguaje ambiguo o excesivamente promocional.
- Usar terminologia estable del proyecto:
  - `trading_engine/`
  - `scenarios/BacktestWeb/`
  - `launch_strategy()`
  - `ejecutar_backtest()`

## 5. Enlaces y rutas

- Preferir enlaces relativos dentro de `docs/`.
- Verificar que los enlaces apunten a archivos existentes.
- Usar rutas reales del proyecto (evitar rutas antiguas o movidas).

## 6. Documentos historicos

Cuando un archivo sea historico (snapshot, plan viejo, resumen cerrado), incluir al inicio:

```markdown
> Documento historico (fecha/contexto).
> Ver estado actual en `docs/ARCHITECTURE.md`.
```

## 7. Plantillas recomendadas

### 7.1 Guia operativa

```markdown
# Titulo de la guia

## Objetivo
...

## Requisitos
...

## Pasos
1. ...
2. ...

## Validacion
...

## Problemas frecuentes
...
```

### 7.2 Diagnostico/Fix

```markdown
# Titulo del diagnostico o fix

## Problema
...

## Causa raiz
...

## Solucion aplicada
...

## Validacion
...

## Conclusion
...
```

## 8. Archivo canonico de referencia

- Arquitectura vigente: `docs/ARCHITECTURE.md`
- Flujo web vigente: `docs/Architecture/FLUJO_ARQUITECTURA_MEJORADO.md`
- Navegacion general: `docs/Index/00_INDEX_DOCUMENTACION.md`