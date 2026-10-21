# Game Session Insights 🎮📊

Convierte un CSV de sesiones de videojuego en métricas de actividad y retención por cohortes, con un informe HTML autónomo y JSON listo para otras herramientas.

**Caso de uso:** comprobar si los jugadores vuelven al día siguiente o una semana después, y distinguir una cohorte con baja retención de otra que todavía no ha tenido tiempo de regresar.

Proyecto original creado el **21 de octubre de 2026**. Datos de demostración completamente ficticios.

## Inicio rápido

Requiere **Python 3.10 o posterior**. Dependencias externas: **ninguna**.

```bash
git clone https://github.com/alvaroalcalaa/game-session-insights.git
cd game-session-insights
python insights.py data/demo.csv --as-of 2026-10-08 --html informe.html --json informe.json
python -m unittest -v
```

Abre `informe.html` en tu navegador. No necesita servidor, JavaScript, conexión ni API. En algunos sistemas utiliza `python3` en lugar de `python`. Las carpetas de salida deben existir.

## Resultado esperado de la demo

| Métrica | Resultado |
|---|---:|
| Jugadores distintos | 5 |
| Sesiones completas | 9 |
| Minutos registrados | 225 |
| Mediana de sesión | 25 minutos |
| Retención D1 | 3 / 4 = 75% |
| Retención D7 | 1 / 2 = 50% |

D1 y D7 tienen denominadores diferentes: solo cuentan los jugadores cuyo día de retorno ya se ha observado por completo.

## Formato de entrada

CSV UTF-8, con cabecera y estas columnas:

| Columna | Significado |
|---|---|
| `session_id` | Identificador único de sesión |
| `player_id` | Identificador de jugador; usa datos sintéticos o seudónimos locales |
| `start_at` | Fecha ISO 8601 con zona horaria |
| `end_at` | Fecha ISO 8601 con zona horaria |

Se aceptan `Z` y offsets como `+02:00`. Se normaliza todo a **UTC**. Se rechazan IDs vacíos o duplicados, fechas sin zona y duraciones negativas. Las columnas adicionales se ignoran.

## Definiciones que evitan errores

- **`--as-of`:** último día UTC con captura completa. Debes indicarlo; el programa no supone que la última fila implica un día completo.
- **Sesión incluida:** inicio y fin anteriores a las 00:00 UTC del día siguiente al corte. Una sesión que termina exactamente en ese límite se excluye hasta ampliar el corte.
- **DAU:** jugadores distintos con al menos una sesión incluida que **empieza** ese día. No es presencia minuto a minuto; una sesión que cruza medianoche se asigna íntegra al día de inicio.
- **Cohorte:** fecha UTC de la primera sesión observada de cada jugador en el archivo, que puede diferir de su alta real.
- **D1/D7:** jugador con sesión iniciada exactamente 1/7 días después de su primera sesión observada. No significa «alguna vez durante la semana» ni una ventana móvil de 24 horas.
- **Cohortes inmaduras:** `null` en JSON y «No observable» en HTML; nunca se convierten en 0%.
- **Retención global:** suma de retornos dividida entre jugadores elegibles; no media simple de porcentajes.
- Los días sin sesiones aparecen con cero hasta `--as-of`. Esto supone un registro de actividad completo.

## Qué exporta

JSON: totales, sesiones excluidas, actividad diaria, cohortes, retornos, denominadores y tasas (0–1, redondeadas a 4 decimales).

HTML: tarjetas de métricas y tablas de actividad/cohortes. Todo se genera localmente, sin recursos remotos. El CLI imprime además el JSON por consola y evita usar el CSV de entrada como salida.

## Pruebas

`python -m unittest -v` comprueba resultados numéricos de la demo, cohortes inmaduras, retorno en día exacto, días sin actividad, corte temporal, archivo vacío, offsets UTC, validación, duplicados, límite de medianoche, escape HTML y ejecución real del CLI.

## Límites

El archivo completo se carga en memoria: está pensado para prototipos y conjuntos pequeños. No detecta huecos de captura, sesiones que faltan ni identidad duplicada de un mismo jugador. Los minutos de sesiones simultáneas se suman; no se deduplican intervalos solapados. Un archivo truncado por la izquierda distorsiona la primera sesión observada y la cohorte. No calcula abandono predictivo, causalidad, significación estadística ni ingresos. No conecta con Steam, Unity, SDKs de telemetría o servicios externos.

## Posibles ampliaciones

Filtros por versión/plataforma, retención D30, embudos de tutorial, intervalos de confianza y comparación entre cohortes. La base ya separa carga, análisis y presentación para poder añadir un adaptador MCP o una interfaz sin cambiar las definiciones.
