# Manual operativo de mantenimiento y desarrollo seguro de TradingCore

**PowerShell · Git · pruebas · diagnóstico · Copilot**

Manual práctico basado en el flujo de trabajo utilizado durante la revisión, refactorización, integración y saneamiento de la aplicación.

**Última actualización:** 28/09/2026

**Proyecto:** TradingCore

## Cómo utilizar este manual

El objetivo es poder repetir manualmente el proceso que hemos seguido: observar el estado real del repositorio, aislar cambios, hacer modificaciones pequeñas y reversibles, verificar, integrar, documentar y dejar un punto de recuperación claro. Los ejemplos usan las rutas y nombres de TradingCore, pero el método es reutilizable en otros proyectos Python/Git.

> **Regla de oro:** antes de restaurar, limpiar, hacer merge o borrar datos, identifica exactamente qué está modificado y conserva una vía de vuelta. En este proyecto evitamos conscientemente usar `git reset`, `git clean` o `git restore` de forma indiscriminada.

## Flujo de trabajo recomendado

1. Situarse en el repositorio o worktree correcto y comprobar rama/estado.

2. Inspeccionar el cambio antes de editar: `git status`, `git diff`, búsquedas de texto y procesos activos.

3. Hacer una modificación pequeña y concreta. Usar Copilot principalmente para escritura de código; documentación y ajustes puntuales pueden editarse directamente cuando sea más eficiente.

4. Revisar el diff. Si aparecen archivos inesperados, detenerse.

5. Ejecutar compilación y tests. Para TradingCore, usar `scripts\verify.ps1` cuando proceda.

6. Hacer un commit con una única intención.

7. Integrar mediante fast-forward cuando sea posible y volver a verificar.

8. Realizar una prueba funcional sobre una única instancia realmente reiniciada; en cambios web, comprobar antes los procesos que escuchan en el puerto 5000.

9. Documentar, etiquetar y limpiar respaldos temporales solo al final.

## 1. Orientación: carpeta, entorno y rama

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Cambiar carpeta | cd C:\Users\juant\Proyectos\Python\TradingCore | Sitúa PowerShell en el repositorio principal. | Antes de cualquier comando Git o ejecución. |
| Activar venv | .\.venv\Scripts\Activate.ps1 | Activa el entorno virtual del proyecto. | Cuando se van a ejecutar Python, pytest o utilidades del proyecto. |
| Rama actual | git branch --show-current | Muestra la rama activa. | Para evitar editar main cuando se quería trabajar en una rama de mantenimiento. |
| Estado corto | git status --short | Muestra modificaciones, altas, borrados y archivos no trackeados. | Antes y después de cada bloque de trabajo. |
| Último commit | git log -1 --oneline | Muestra HEAD de forma compacta. | Para confirmar que se está en el commit esperado. |
| Últimos commits | git log -3 --oneline | Muestra una pequeña historia reciente. | Al cerrar una fase o revisar integración. |

> **Consejo:** no confíes solo en el prompt de PowerShell. `TradingCore` y `TradingCore.worktrees\web-refactor` son árboles distintos. Comprueba siempre `git branch --show-current` y `git status --short`.

## 2. Inspección de cambios Git

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Diff general | git diff | Muestra cambios no preparados (unstaged). | Antes de guardar o descartar cambios. |
| Nombres/estado | git diff --name-status | Lista solo archivos y tipo de cambio (M, D, A...). | Cuando el diff completo es demasiado largo. |
| Resumen | git diff --stat | Resume número de líneas y archivos afectados. | Para dimensionar un cambio rápidamente. |
| Archivo concreto | git diff -- run_backtest_scheduler.bat | Aísla el diff de un solo archivo. | Después de una edición manual. |
| Comprobar whitespace | git diff --check | Detecta espacios problemáticos y errores de whitespace. | Antes de commit/merge. |
| Comparar ramas | git diff --stat main...maintenance/web-refactor | Resume lo que la rama aporta respecto a main. | Antes de integrar. |
| Archivos entre ramas | git diff --name-status main...maintenance/web-refactor | Lista exactamente qué archivos cambia la rama. | Auditoría previa al merge. |

## 3. Commits, ramas, integración y tags

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Preparar archivo | git add run_backtest_scheduler.bat | Añade el archivo al índice. | Cuando el diff ya ha sido revisado. |
| Commit | git commit -m "fix: resolver entorno virtual del scheduler" | Registra una unidad lógica de cambio. | Después de tests satisfactorios. |
| Merge seguro | git merge --ff-only maintenance/web-refactor | Avanza main sin crear merge commit si la historia es lineal. | Integración final de una rama validada. |
| Crear rama archivo | git branch archive/pre-merge-agent-2026-08-13 "stash@{1}" | Conserva un snapshot antiguo bajo un nombre permanente. | Antes de eliminar un stash potencialmente útil. |
| Crear tag anotado | git tag -a prod-refactor-web-2026-09-15 -m "Cierre refactor web, scheduler y limpieza de datos operativos" | Marca un estado estable y documentado. | Al terminar una fase importante. |
| Ver tag | git show --stat --oneline prod-refactor-web-2026-09-15 | Comprueba a qué commit apunta y su mensaje. | Después de crear el tag. |

> **Convención de commits:** usar prefijos sencillos: `fix:` para correcciones, `refactor:` para reorganización sin cambio funcional, `test:` para cobertura, `docs:` para documentación y `chore:` para mantenimiento.

## 4. Stash: conservar estado local sin perderlo

El stash fue útil cuando main tenía borrados operativos y archivos no trackeados que impedían una integración limpia. En PowerShell conviene poner entre comillas referencias como "stash@{0}" para evitar que el intérprete trate las llaves como sintaxis propia.

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Guardar tracked + untracked | git stash push -u -m "estado local usuarios antes de integrar web-refactor" | Guarda cambios tracked y untracked. | Antes de una integración cuando el working tree no puede quedar limpio de otra forma. |
| Listar | git stash list | Enumera stashes disponibles. | Antes de aplicar o borrar cualquiera. |
| Resumen | git stash show --stat "stash@{0}" | Resume lo almacenado. | Para confirmar que el respaldo contiene los cambios esperados. |
| Nombres/estado | git stash show --name-status "stash@{0}" | Lista archivos del stash. | Para revisar borrados, altas y modificaciones. |
| Untracked internos | git show --stat --oneline "stash@{0}^3" | Inspecciona el commit auxiliar de no trackeados creado por stash -u. | Cuando hay directorios no trackeados relevantes. |
| Eliminar stash | git stash drop "stash@{0}" | Borra un stash concreto. | Solo cuando su contenido ya está integrado o respaldado por otra vía. |

> **Precaución:** los índices de stash cambian al borrar uno. Vuelve a ejecutar `git stash list` después de cada `drop`.

## 5. Restaurar o dejar de versionar archivos con seguridad

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Restaurar archivo | git restore --worktree -- run_backtest_scheduler.bat | Devuelve el working tree a la versión del índice/HEAD para ese archivo. | Cuando existe una copia local redundante que ya está committeada en otra rama. |
| Restaurar rutas | git restore --worktree -- Data_files/Backtest_config Data_files/XSTO | Restaura rutas concretas sin afectar el resto. | Usado temporalmente para limpiar main antes del merge. |
| Ver tracked | git ls-files Data_files/Backtest_config | Lista archivos de esa ruta que Git sigue. | Antes de sacarlos del versionado. |
| Quitar solo del índice | git rm -r --cached --ignore-unmatch Data_files/Backtest_config | Deja de versionar la carpeta sin borrar los archivos físicos existentes. | Datos operativos que deben vivir fuera de Git. |
| Ver árbol antiguo | git ls-tree HEAD^ -- Data_files/XSTO | Muestra tipo/hash de un archivo en el commit anterior. | Para investigar un archivo borrado. |
| Ver contenido antiguo | git show HEAD^:Data_files/XSTO | Muestra el contenido del archivo en el commit anterior. | Para decidir si el borrado es seguro. |

## 6. .gitignore y diagnóstico de archivos ignorados

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Buscar reglas | Select-String -Path .\.gitignore -Pattern 'Data_files','Data_Files','Backtest_config','\.json' | Localiza reglas relevantes del .gitignore. | Antes de modificar reglas. |
| Por qué está ignorado | git check-ignore -v .\scripts\Data_files\MSFT_1d_MAX.csv | Indica la regla exacta que ignora un archivo. | Cuando git status no muestra un archivo existente. |
| Comprobar carpeta | git check-ignore -v .\scripts\Data_files | Comprueba si el directorio en sí coincide con una regla. | Diagnóstico de cachés o salidas generadas. |

En TradingCore la regla existente Data_files/Backtest_config/**/*.json ya ignoraba JSON nuevos, pero los antiguos seguían apareciendo porque Git ya los tenía trackeados. Por eso fue necesario git rm --cached.

## 7. PowerShell para inspeccionar archivos y respaldos

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Existe ruta | Test-Path .\scripts\Data_files | Devuelve True/False. | Comprobación rápida antes/después de mover o borrar. |
| Listar recursivo | Get-ChildItem .\scripts\Data_files -Recurse -File | Enumera archivos de forma recursiva. | Auditar caché o respaldos. |
| Contar | $files = Get-ChildItem .\scripts\Data_files -Recurse -File; $files.Count | Cuenta archivos. | Dimensionar un árbol grande. |
| Tamaño total | "{0:N2} GB" -f (($files \| Measure-Object Length -Sum).Sum / 1GB) | Calcula tamaño agregado. | Valorar coste de una caché. |
| Más recientes | Get-ChildItem .\Data_files -Recurse -File \| Sort-Object LastWriteTime -Descending \| Select-Object -First 10 FullName, Length, LastWriteTime \| Format-List | Muestra actividad reciente. | Determinar cuál de dos cachés está activa. |
| Hash | Get-FileHash .\Data_files\MSFT_1d_MAX.csv | Calcula SHA256 por defecto. | Comparar archivos homónimos. |
| Copiar respaldo | $backup="C:\Users\juant\Proyectos\Python\TradingCore_BacktestConfig_backup_20260915"; Copy-Item .\Data_files\Backtest_config $backup -Recurse -Force | Copia datos operativos fuera del repo. | Antes de cambiar tracking Git. |
| Mover archivo/caché | Move-Item .\scripts\Data_files "C:\Users\juant\Proyectos\Python\TradingCore_scripts_Data_files_backup_20260915" | Saca una caché histórica del repositorio sin destruirla. | Limpieza reversible. |

## 8. Comparar dos árboles de archivos

Este patrón permitió comprobar que scripts\Data_files era casi un superconjunto de Data_files y que, además, tenía fechas más antiguas.

```powershell
$rootA = (Resolve-Path .\Data_files).Path
$rootB = (Resolve-Path .\scripts\Data_files).Path

$a = Get-ChildItem $rootA -Recurse -File | ForEach-Object {
    [PSCustomObject]@{
        Rel = $_.FullName.Substring($rootA.Length).TrimStart('\')
    }
}

$b = Get-ChildItem $rootB -Recurse -File | ForEach-Object {
    [PSCustomObject]@{
        Rel = $_.FullName.Substring($rootB.Length).TrimStart('\')
    }
}

Compare-Object $a.Rel $b.Rel |
Group-Object SideIndicator |
Select-Object Name, Count
```

Interpretación de Compare-Object: => significa que existe solo en el segundo conjunto; <= significa que existe solo en el primero.

## 9. Buscar referencias en el código sin ripgrep

Cuando rg no estaba instalado, usamos Select-String, que viene con PowerShell.

```powershell
Get-ChildItem scripts,scenarios,trading_engine -Recurse -File -Include *.py,*.bat,*.ps1 |
Select-String -Pattern 'Data_files','Data_Files' |
ForEach-Object {
    "{0}:{1}: {2}" -f $_.Path, $_.LineNumber, $_.Line.Trim()
}
```

```powershell
Get-ChildItem scripts,scenarios,trading_engine -Recurse -File -Include *.py,*.bat,*.ps1 |
Select-String -Pattern 'chdir','getcwd','Path.cwd','__file__' |
ForEach-Object {
    "{0}:{1}: {2}" -f $_.Path, $_.LineNumber, $_.Line.Trim()
}
```

> **Patrón reutilizable:** cambia la lista de carpetas, extensiones y patrones. Es una alternativa muy útil a `rg`/`grep` en instalaciones Windows estándar.

## 10. Diagnóstico de procesos, puertos y servicios

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Puerto 5000 | $pid5000 = (Get-NetTCPConnection -LocalPort 5000 -State Listen).OwningProcess | Obtiene PID del proceso que escucha el puerto web. | Evitar instancias duplicadas. |
| Proceso por PID | Get-CimInstance Win32_Process -Filter "ProcessId=$pid5000" \| Select-Object ProcessId, ExecutablePath, CommandLine | Muestra ejecutable y línea de comandos. | Confirmar qué aplicación ocupa el puerto. |
| Comando completo | Get-CimInstance Win32_Process -Filter "ProcessId=6716" \| Select-Object -ExpandProperty CommandLine | Evita truncado de CommandLine. | Ver módulo/script exacto lanzado. |
| Matar árbol | taskkill /PID 6716 /T /F | Finaliza proceso y descendientes. | Solo después de confirmar el PID. |
| Comprobar puerto libre | Get-NetTCPConnection -LocalPort 5000 -State Listen -ErrorAction SilentlyContinue | No devuelve nada si el puerto está libre. | Antes de reiniciar la web. |
| Buscar scheduler | Get-CimInstance Win32_Process \| Where-Object { $_.CommandLine -match "backtest_scheduler.py" } \| Select-Object ProcessId, ParentProcessId, CommandLine | Localiza procesos del scheduler. | Diagnóstico de duplicados/huérfanos. |
| PID file | Test-Path .\logs\backtest_scheduler.pid | Comprueba si existe el PID persistido. | Después de detener el scheduler. |

## 11. Arranque y verificación de TradingCore

La operación normal de la aplicación web se realiza con `.\start_web.bat` y `.\stop_web.bat`. El arranque comprueba PostgreSQL y el puerto 5000 antes de crear una nueva instancia.

`start_web.bat` trabaja desde la raíz del proyecto, comprueba PostgreSQL e identifica el PID, proceso y línea de comandos del listener del puerto 5000. Si el puerto ya está ocupado, no lanza una segunda instancia. Tras el arranque valida `/login` y devuelve un código de salida coherente con el resultado.

`stop_web.bat` obtiene primero el PID propietario del puerto 5000 y comprueba que corresponda a `scenarios.BacktestWeb.app`. Si el puerto pertenece a otro programa, no termina ese proceso ni detiene PostgreSQL. Si reconoce TradingCore, libera el puerto y después detiene PostgreSQL.

`scripts\verify.ps1` tiene cuatro pasos: `[1/4]` sintaxis Python, `[2/4]` tests base, `[3/4]` estado del servidor web y `[4/4]` estado Git. En `[3/4]` muestra PID, proceso, línea de comandos y si el listener activo se reconoce como TradingCore Web.

| Objetivo | Comando | Qué hace | Cuándo usarlo |
| --- | --- | --- | --- |
| Arrancar web | .\start_web.bat | Comprueba PostgreSQL, puerto 5000 y lanza BacktestWeb si procede. | Prueba funcional o arranque normal. |
| Arrancar scheduler | .\run_backtest_scheduler.bat | Ejecuta el scheduler con el Python configurado. | Validar jobs y operación programada. |
| Suite de verificación | `.\scripts\verify.ps1` | Ejecuta 4 pasos: sintaxis Python, tests base, estado del servidor web y estado Git. | Antes de un commit importante y después de un merge. |
| Import NumPy | .\.venv\Scripts\python.exe -c "import sys; print(sys.executable); import numpy; print(numpy.__version__)" | Comprueba intérprete y NumPy. | Si el arranque parece bloquearse durante imports. |
| Import Backtest | .\.venv\Scripts\python.exe -c "from scenarios.BacktestWeb.Backtest import ejecutar_backtest; print(\'IMPORT OK\')" | Aísla la cadena de importación del backtest. | Distinguir problema de entorno de problema del scheduler. |

> **Validación del endurecimiento operativo (28/09/2026):** `51 passed`; `stop_web.bat` liberó el puerto 5000; `start_web.bat` levantó de nuevo PostgreSQL y la web; `/login` devolvió HTTP 200; y `git diff --check` quedó limpio salvo avisos CRLF benignos.

## 12. Pruebas Python y validación mínima

Aunque normalmente usamos scripts\verify.ps1, estas son las piezas básicas que hay debajo y resultan útiles para aislar fallos.

```powershell
python -m compileall -q scenarios trading_engine scripts tests
python -m pytest tests/web/test_routes.py -q
python -m pytest tests/unit/test_technical_signals.py -q
```

El principio es ejecutar primero la prueba más específica del cambio y después la suite base. Un test nuevo debe fallar por la causa esperada antes del arreglo y pasar después.

## 13. Manejo seguro de archivos de texto y codificación

> **Lección aprendida:** evitar reescribir archivos fuente con tuberías del tipo `(Get-Content ...) | Set-Content` sin controlar la codificación. En una sesión anterior esto corrompió UTF-8. Para cambios simples, editar manualmente o usar herramientas que preserven la codificación.

Para un archivo .bat corto usamos una here-string y Out-File -Encoding ascii, porque el contenido era ASCII puro:

```powershell
@'
@echo off
setlocal
...
'@ | Out-File -FilePath .\run_backtest_scheduler.bat -Encoding ascii
```

No extrapoles este método a Python, Markdown o JSON con acentos sin elegir explícitamente una codificación adecuada.

## 14. Patrón de trabajo con worktrees

El worktree permitió modificar y probar una rama de mantenimiento sin interferir con la copia principal en producción. El patrón práctico fue: desarrollar y verificar en TradingCore.worktrees\web-refactor, hacer commits pequeños, volver al repo principal y realizar git merge --ff-only.

> **Control visual:** cuando cambies de terminal o carpeta, vuelve a ejecutar `git branch --show-current` y `git status --short`. Fue la forma más eficaz de evitar confundir `main` con `maintenance/web-refactor`.

## 15. Plantillas de prompts para GitHub Copilot

Copilot se utiliza principalmente como escritor de código bajo instrucciones muy acotadas. Para documentación, correcciones pequeñas o cambios mecánicos claramente controlados, es preferible editar directamente si evita consumo innecesario de cuota. El objetivo es que Copilot haga una transformación concreta, no que decida la arquitectura, ejecute comandos o mezcle tareas. Después de cada uso, comprobar git status y git diff para confirmar que realmente modificó el workspace esperado.

### 15.1 Plantilla: extracción de helper sin cambio funcional

Quiero hacer una refactorización mecánica y de bajo riesgo.

Contexto:
- Archivo actual: [RUTA_ARCHIVO_ORIGEN]
- Función/ruta afectada: [FUNCIÓN_O_BLOQUE]
- Nuevo módulo: [RUTA_NUEVO_MÓDULO]

Objetivo:
Extrae [RESPONSABILIDAD_CONCRETA] a una función helper llamada [NOMBRE_HELPER] en [NUEVO_MÓDULO].

Restricciones:
- No cambies comportamiento ni mensajes visibles.
- No cambies firmas públicas salvo lo imprescindible para pasar dependencias explícitas.
- No reorganices código no relacionado.
- Mantén los mismos fallbacks, excepciones y valores de retorno.
- Actualiza imports de forma mínima.
- No ejecutes tests ni comandos.

Entrega:
1. Haz solo los cambios necesarios.
2. Resume qué moviste y qué quedó deliberadamente sin tocar.

Ejemplo aplicado: extraer renderizado nativo de gráficos desde main_bp.py a graph_render.py.

### 15.2 Plantilla: corregir un bug puntual preservando comportamiento

Corrige únicamente este problema:
[DESCRIPCIÓN DEL BUG]

Archivos relevantes:
[ARCHIVOS]

Comportamiento esperado:
[RESULTADO ESPERADO]

Restricciones:
- Mantén intactos los casos que ya funcionan.
- No hagas refactor adicional.
- Conserva compatibilidad con [CONDICIÓN/ENTORNO].
- Añade o ajusta solo el test mínimo que demuestre el bug y la corrección.
- No ejecutes comandos ni tests.

Antes de editar, identifica brevemente la causa en el código actual. Después realiza el parche mínimo.

Ejemplos: preservar HTTPException en una ruta que tenía un except Exception demasiado amplio; limpiar un PID huérfano sin confundir reutilización de PID.

### 15.3 Plantilla: añadir tests de caracterización

Necesito ampliar cobertura sin cambiar código de producción salvo que aparezca un bug real.

Módulo bajo prueba: [MÓDULO]
Archivo de tests: [ARCHIVO_TEST]

Casos que quiero cubrir:
- [CASO 1]
- [CASO 2]
- [CASO 3]

Requisitos:
- Usa pytest.
- Pruebas pequeñas y deterministas.
- Evita red, base de datos real o reloj real cuando se pueda simular.
- Reutiliza fixtures existentes si son adecuadas.
- Comprueba resultados observables, no detalles internos innecesarios.
- No ejecutes los tests; solo escribe/modifica el código de pruebas.
- No cambies producción para “hacer pasar” un test incorrecto.

Ejemplo aplicado: ampliar cobertura de señales EMA, RSI, MACD, Stochastic, ATR, Bollinger, MoS y Volumen.

### 15.4 Plantilla: modernización de API sin cambio semántico

Actualiza usos obsoletos de [API/FRAMEWORK] en [ARCHIVOS].

Sustituciones deseadas:
- [PATRÓN ANTIGUO] -> [PATRÓN NUEVO]

Restricciones:
- Conserva exactamente el comportamiento de 404/None/excepciones.
- No cambies consultas no relacionadas.
- No modifiques modelos ni esquema de base de datos.
- Haz el cambio más pequeño posible.
- No ejecutes tests.

Al final enumera las ocurrencias modificadas.

Ejemplo aplicado: sustituir Query.get / get_or_404 legacy de SQLAlchemy por db.session.get / db.get_or_404.

### 15.5 Plantilla: launcher o script operativo

Modifica [SCRIPT] para que funcione correctamente en estos dos contextos:
1. Repositorio principal: [RUTA/CONDICIÓN]
2. Worktree: [RUTA/CONDICIÓN]

Objetivo:
[OBJETIVO, por ejemplo resolver el Python del entorno virtual]

Reglas:
- Primero intenta la ruta local/canónica.
- Solo si no existe, usa el fallback.
- Si ninguna existe, muestra un error claro y termina con código distinto de cero.
- No cambies otros comportamientos del script.
- Mantén compatibilidad con Windows cmd/batch.
- No ejecutes el script.

Ejemplo aplicado: run_backtest_scheduler.bat con .venv local y fallback al repo principal cuando se lanza desde un worktree.

### 15.6 Plantilla: documentación técnica después de cambios

Actualiza [DOCUMENTO] para reflejar el estado real actual del proyecto.

Cambios que deben documentarse:
- [CAMBIO 1]
- [CAMBIO 2]
- [CAMBIO 3]

Restricciones:
- No describas funcionalidades futuras como si ya existieran.
- Distingue claramente “estado actual” de “trabajo previsto”.
- Mantén la terminología y rutas reales del repositorio.
- Conserva la estructura general del documento salvo que sea confusa.
- Actualiza la línea “Última actualización” a [FECHA].
- No ejecutes comandos.

### 15.7 Plantilla: revisión/auditoría antes de editar

Revisa [ÁREA/MÓDULO] con el objetivo de detectar [TIPO DE PROBLEMA].

Quiero únicamente análisis, sin modificar archivos todavía.

Busca específicamente:
- [RIESGO 1]
- [RIESGO 2]
- [RIESGO 3]

Devuelve:
1. Hallazgos confirmados con archivo y función/línea aproximada.
2. Falsos positivos o cosas que parecen problemas pero no lo son.
3. Propuesta de cambios ordenada de menor a mayor riesgo.
4. Tests que faltan para poder refactorizar con seguridad.

No escribas código y no ejecutes comandos.

Ejemplo aplicado: auditoría de señales técnicas y revisión del flujo de fundamentales antes de decidir su rediseño.

## 16. Cómo pedir cambios a Copilot sin gastar contexto innecesario

- Indica un solo objetivo por prompt. Si hay dos responsabilidades distintas, sepáralas en dos commits y dos prompts.

- Da rutas y nombres exactos. “Arregla los gráficos” es peor que “extrae _render_native_backtest_html de main_bp.py a graph_render.py”.

- Incluye restricciones explícitas: sin cambio funcional, sin modificar otros archivos, sin ejecutar tests.

- Pide tests solo para el comportamiento que quieres proteger. Evita “añade todos los tests posibles”.

- Revisa siempre git diff después. Copilot escribe; Git y los tests verifican.

- Si Copilot propone una refactorización mayor que la pedida, recházala y vuelve a acotar el prompt.

- Reservar Copilot para cambios de código con valor real; no consumir cuota en documentación que pueda editarse y revisar directamente.

- Si Copilot no modifica archivos, no repetir prompts largos de forma indefinida: verificar primero el modo de edición/Agent y el workspace activo.

## 17. Checklist antes de un commit

- ☐ ¿Estoy en la rama y carpeta correctas?

- ☐ ¿git status muestra únicamente archivos esperados?

- ☐ ¿He leído git diff de los archivos modificados?

- ☐ ¿git diff --check está limpio?

- ☐ ¿La prueba específica pasa?

- ☐ ¿La suite base/verify pasa?

- ☐ ¿El commit tiene una sola intención?

- ☐ ¿Los datos operativos, cachés o secretos han quedado fuera del commit?

## 18. Checklist antes de integrar en main

- ☐ Working tree de main limpio o cambios locales conscientemente respaldados.

- ☐ Diff rama...main revisado por nombre y tamaño.

- ☐ Verificación completa pasada en la rama.

- ☐ Merge con --ff-only siempre que sea posible.

- ☐ Verificación repetida después del merge.

- ☐ Prueba funcional usando una instancia reiniciada con el código nuevo.

- ☐ Solo después: restaurar estado operativo, limpiar stashes y crear tag.

## 19. Checklist de diagnóstico cuando algo “no cuadra”

- ☐ Confirmar cwd con el prompt y rama con git branch --show-current.

- ☐ Confirmar intérprete con sys.executable.

- ☐ Confirmar proceso/CommandLine si hay un puerto ocupado.

- ☐ Comparar timestamps si hay dos carpetas de caché similares.

- ☐ Usar git check-ignore -v si un archivo existe pero no aparece en status.

- ☐ Usar hashes cuando dos archivos con el mismo nombre podrían contener datos diferentes.

- ☐ No borrar nada hasta saber si es código, dato de usuario, caché regenerable o respaldo.

## 20. Secuencia resumida reutilizable

```powershell
# 1) Orientación
git branch --show-current
git status --short
git log -1 --oneline

# 2) Inspección
git diff --name-status
git diff --check

# 3) Editar / Copilot
# ... cambio pequeño ...

# 4) Revisar y probar
git diff -- archivo_modificado
.\scripts\verify.ps1

# 5) Commit
git add archivo_modificado
git commit -m "tipo: descripción breve"

# 6) Integración
git merge --ff-only rama_validada
.\scripts\verify.ps1

# 7) Prueba funcional
.\start_web.bat
# login -> backtest pequeño -> gráfico -> scheduler

# 8) Cierre
git status --short
git tag -a nombre-del-tag -m "Descripción del cierre"
```

## 21. Validación visual de la aplicación web

En cambios de plantillas Jinja/HTML, la prueba visual debe hacerse contra una única instancia recién iniciada. Una instancia antigua puede mantener en memoria templates anteriores y hacer que el navegador muestre un comportamiento que ya no corresponde a los archivos del workspace.

`.\scripts\verify.ps1`

Comprobar el paso `[3/4] Web server state` y confirmar qué PID, proceso y línea de comandos están escuchando en el puerto 5000. Para reiniciar la aplicación utilizar `.\stop_web.bat` y después `.\start_web.bat`. `stop_web.bat` verifica previamente que el listener corresponda a TradingCore y no termina procesos ajenos. Después realizar `Ctrl+F5` en el navegador.

- ☐ Una única instancia TradingCore identificada como listener del puerto 5000.

- ☐ Rama y cwd confirmados antes de arrancar.

- ☐ Subpestañas de configuración muestran un único panel activo.

- ☐ Botones Ayuda abren y cierran el modal correspondiente.

- ☐ Tildes, eñes, símbolos e iconos se muestran correctamente.

## 22. Documentación y ayuda contextual

Las ayudas de configuración forman parte del comportamiento visible del producto y deben revisarse cuando cambie la lógica de un indicador. Actualmente Global, EMA, RSI, MACD, ATR, Estocástico, Bollinger y Volumen/MoS disponen de ayuda contextual.

La documentación web se filtra por rol: el usuario normal accede únicamente al Manual de Usuario y a las ayudas contextuales de la interfaz; el administrador puede consultar toda la documentación técnica y operativa. La autorización se mantiene también en backend.

## 23. Definition of Done de cambios funcionales

- ☐ Código implementado.

- ☐ Tests añadidos o actualizados cuando proceda.

- ☐ Tests existentes superados.

- ☐ Ayuda contextual añadida o actualizada si existe interfaz.

- ☐ Manual de usuario actualizado.

- ☐ Documentación admin/técnica actualizada si procede.

- ☐ README actualizado si cambia arquitectura o navegación.

- ☐ Verificación funcional y visual realizada.

- ☐ Commit realizado con una única intención.

- ☐ Tag/checkpoint creado cuando corresponda.

## 24. Estado validado de la auditoría de indicadores

A 20/09/2026 se ha completado la auditoría UI -> configuración -> motor de los indicadores principales. El objetivo de este checkpoint es que mantenimiento, tests y documentación describan el mismo contrato funcional.

- Persistencia: corregidos booleanos de ATR, MoS mínimo y Volumen mínimo; stoploss_swing_enabled se renderiza de forma explícita.

- MACD: cruce e histograma de compra/venta consumen directamente la opción elegida; None desactiva ese lado.

- Stochastic: Fast/Mid/Slow consumen sus lógicas mínimo/ascendente y máximo/descendente; N/A no genera señal.

- Bollinger: la compra requiere bb_buy_crossover activo y cruce alcista de la banda inferior; no existe compra alternativa por simple toque cuando está desactivado.

- MoS: umbral, mínimo y ascendente se aplican con las confirmaciones activas en lógica AND.

- Volumen: la referencia es una SMA de volumen; volume_ascendente representa la tendencia real de esa SMA y ya no un contador oculto de overshoots.

- Validación del último bloque: 49 tests unitarios de señales y 42 tests web superados.

Commits de referencia: b933e2c (persistencia), 6ad2d9e (MACD), 5a79719 (Stochastic), 277a831 (Bollinger), da92dd7 (MoS) y 8809036 (Volumen).

Regla operativa: antes de cerrar un cambio de indicador, revisar conjuntamente plantilla UI, carga/persistencia, atributos de estrategia, consumidor del motor, tests, ayuda contextual, Manual de Usuario y documentación técnica.

## Apéndice A. Comandos que conviene evitar por defecto

No son “malos”, pero son peligrosos si se usan sin inspección previa:

- git reset --hard: puede destruir modificaciones locales.

- git clean -fd: borra archivos/directorios no trackeados.

- git restore .: puede descartar trabajo de muchos archivos a la vez.

- git stash pop sin revisar: puede reintroducir datos, conflictos o estados antiguos.

- Remove-Item -Recurse sobre datos operativos o cachés sin respaldo.

- Reescrituras masivas con Set-Content sin controlar codificación.

## Apéndice B. Qué pertenece a Git y qué no

| Tipo | Ejemplos TradingCore | Tratamiento recomendado |
| --- | --- | --- |
| Código | scenarios/, trading_engine/, scripts/ | Versionado, revisado con diff, tests y commits. |
| Tests | tests/ | Versionados; deben acompañar comportamiento importante. |
| Documentación | docs/README.md, guías | Versionada y actualizada con el estado real. |
| Estrategias de usuario | Data_files/Backtest_config/*.json | No versionarlas; son datos operativos del usuario. |
| Caché de mercado | Data_Files/*.csv, Fundamentals/ | Regenerable; normalmente ignorada por Git. |
| Logs/PID | Backtesting/logs/, logs/*.pid | Operativos; fuera del versionado. |
| Respaldos temporales | carpetas backup, stashes | Conservar solo mientras aporten una vía de recuperación; limpiar al cierre. |
