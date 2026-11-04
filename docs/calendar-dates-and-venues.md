# Fechas y sedes dentro de una jornada

Los partidos conservan su jornada deportiva y pueden tener fechas y sedes distintas. `game_date` es una fecha de calendario (sin zona horaria) y `venue` una etiqueta de sede; la hora sigue siendo local.

## Activación

Aplica Alembic `upgrade head` con la cuenta propietaria de la base, o ejecuta [activate-game-dates-and-venues.sql](sql/activate-game-dates-and-venues.sql) desde el editor SQL de Supabase. El script es idempotente, no asigna fechas a los partidos históricos y no altera IDs, resultados, estadísticas ni planillas.

La aplicación sigue leyendo la base anterior y permite operaciones antiguas que no escriben fecha/sede. Una escritura con esos datos exige la migración y responde con un conflicto controlado si falta; nunca los descarta silenciosamente. `GET /api/games/calendar-capabilities` informa si la base ya tiene activados ambos campos, sin exponer datos de la base.

## Subir el archivo original

- XLSX: cada encabezado `Sede:` / `Fecha:` define el contexto de su bloque, aunque varios bloques pertenezcan a la misma jornada.
- Una fecha inválida, por ejemplo `#REF!`, no hereda la del bloque anterior. Las filas quedan pendientes de revisión.
- En la revisión se puede completar una fecha por fila o usar **Completar fechas vacías**. Solo modifica las vacías: conserva las fechas válidas del archivo.
- CSV: las columnas opcionales `fecha` / `date` / `game_date` y `sede` / `venue` transportan el mismo contexto. Se aceptan fechas ISO y día/mes/año.
- Los archivos sin esos datos siguen siendo válidos. No se infiere una fecha a partir de la jornada.
- La importación de oficiales también conserva o reconoce este contexto para distinguir encuentros entre los mismos rivales.

## Reimportaciones y cambios

Un espacio del calendario se identifica por jornada, fecha, sede, campo y hora. Volver a confirmar el mismo rol no duplica sus espacios. Para enriquecer un registro antiguo sin fecha/sede solo se reutiliza una coincidencia inequívoca con los mismos equipos; las ambigüedades se rechazan.

Para **reprogramar** un partido ya registrado usa el tablero o su editor: conserva su ID y su planilla. Un archivo que mueve fecha/hora/sede/campo puede describir un espacio nuevo; no debe suponerse que siempre identifica el encuentro antiguo. Cambiar enfrentamientos en un espacio existente sigue requiriendo que no tenga resultados, estadísticas ni captura asociada.

El tablero agrupa por fecha y sede. Arrastrar entre grupos cambia también ese contexto. Las colisiones se comprueban en el servidor y todos los movimientos conservan la identidad del partido.
