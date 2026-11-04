# Crédito excepcional de puntos a favor: partido 258

El administrador confirmó que Vikingos debe conservar **solo los 42 puntos a favor** del partido `/games/258`, sin victoria ni partido jugado. BlackMamba no debe recibir derrota ni puntos en contra. Las estadísticas individuales publicadas deben mantenerse.

Antes de la eliminación se verificó en producción BlackMamba (equipo 62) 0–42 Vikingos (61), jornada 4, U12, resultado oficial finalizado. Durante la revisión el partido fue eliminado en producción: el detalle pasó de 200 a 404 y no apareció ningún reemplazo de esos equipos en la jornada 4. El equipo 61 quedó con 146 PF, 19 PC, 3 PJ y 3 victorias. El equipo 62 quedó con 40 PF, 18 PC, 2 PJ, 1 victoria y 1 derrota.

`services/standings_adjustments.py` registra la excepción aprobada: +42 PF al equipo 61 únicamente en U12. Sus totales pasan a **188 PF, 19 PC, diferencia +169**, manteniendo 3 PJ y 3 victorias. Los totales de BlackMamba y de todos los demás equipos no cambian. La diferencia de puntos incluye el crédito, igual que cualquier punto a favor. Por esta excepción, la suma global de PF puede diferir de la de PC.

El cálculo añade el crédito una sola vez a cada lectura de los resultados base. No inserta partidos ni estadísticas, no modifica la base, no concede victorias ni altera el borrado normal. Las estadísticas individuales existentes quedan intactas. El historial de captura que hubiera borrado la eliminación previa no se reconstruye.

Para evitar duplicaciones, el crédito no se aplica si reaparece el ID de origen o un resultado oficial finalizado equivalente en la misma jornada, incluso con los rivales invertidos. No se aplica a otra categoría ni a otro equipo, y exige que el ID siga correspondiendo al nombre aprobado. Si se vuelve a importar el encuentro eliminado, se deberá revisar su efecto normal sobre el rival; este crédito no cambia las reglas de las importaciones.

Para revertir el ajuste, eliminar la entrada explícita y desplegar. No requiere migración ni credenciales de escritura de producción.
