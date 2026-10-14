---
name: flagtastic-security-fix
description: Corrige vulnerabilidades documentadas de Flagtastic o de una aplicación web autorizada; reproduce cada hallazgo, aplica defensas en el servidor o sink correcto y añade pruebas de regresión. Úsala para remediar una auditoría, cerrar brechas o aplicar parches de seguridad.
---

# Corrección de vulnerabilidades

Úsala cuando se solicite reparar hallazgos. Crea cambios revisables y pruebas;
no marques un hallazgo corregido sin validar tanto el ataque como el uso legítimo.
La solicitud de reparar autoriza cambios locales y pruebas con datos sintéticos.
Respeta autorizaciones previas; no inventes pasos de aprobación. Publicar,
desplegar o migrar producción requiere estar dentro del alcance autorizado.

## Flujo

1. Lee las instrucciones del repo, su estado Git y el informe de auditoría.
   En Flagtastic busca informes en `docs/security/`. Si no hay un informe o los
   hallazgos no son reproducibles, aplica primero `$flagtastic-security-audit`.
   Verifica el SHA actual; reproduce y descarta hallazgos obsoletos antes de parchear.
2. Prioriza XSS y apropiación de identidad, después sesiones y abuso de login.
   Atiende hallazgos condicionados según las precondiciones reales del despliegue.
3. Usa una rama aislada, conserva cambios existentes y una DB desechable.
   Nunca ejecutes fixtures destructivas contra una DB compartida. Registra si
   una prueba usa mocks en vez de PostgreSQL o un navegador real.
4. Convierte cada reproducción en una prueba que exija el comportamiento seguro
   y demuestre fallo ANTES del parche. Las pruebas de caracterización de una brecha pueden pasar
   cuando existe; no copiarlas sin invertir sus expectativas.
5. Corrige la causa en el límite que controla el efecto, no solo en el formulario.
6. Ejecuta regresiones de seguridad y los flujos legítimos afectados; revisa
   móviles, roles acumulativos, importaciones, caché y recuperación de cuentas.
7. Actualiza el informe con ID, archivos, pruebas, estado y riesgos restantes.
   Un workaround parcial es mitigado; una reproducción que no pudo ejecutarse
   está pendiente de verificación. No la presentes como corregida.

## Guía de corrección por superficie

### XSS por atributos

Prefiere crear nodos y asignar `textContent`, `.value`, `.alt` y atributos seguros
mediante DOM. Si conservas plantillas HTML, el helper debe codificar `& < > " '`.
Mantén validación independiente de URLs y atributos: escapar texto no vuelve
seguro `javascript:` ni handlers de evento. Revisa todos los consumidores del
helper y no solo los dos demostrados. No rechaces caracteres normales de nombres
como sustituto del escape contextual.

Prueba el helper REAL en un DOM/browser, los renders de roster y admin, y nombres
legítimos con comillas, apóstrofes, `&` y acentos. No debe aparecer ningún atributo
`on*` creado por el alias. Una CSP compatible es defensa adicional.

### Reclamación de perfil

Exige una invitación aleatoria de un solo uso emitida por responsable autorizado
para ese `player_id`, o una aprobación verificable antes de vincular el usuario.
Guarda el hash del token, destinatario, expiración y consumo atómico en una
transacción con locks/constraints. Nombre, edad, CURP y documento no son secretos.
Verificar el correo del solicitante por sí solo tampoco acredita al jugador.
Evita modificar AKA/foto antes de validar titularidad. No abras duplicados de
identidad para conservar el formulario antiguo; define errores compatibles y
actualiza UI/móvil. Si cambia la política de altas, solicita solo esa decisión
de producto mientras completas los cambios independientes ya autorizados.

Prueba reclamación sin invitación, token vencido/ajeno/reutilizado, consumo
concurrente y alta legítima. La vía anónima no debe apropiarse de un perfil existente.

### Sesiones tras cambio de contraseña

Revoca sesiones anteriores e invalida tokens de reset pendientes en la misma
transacción que cambia la contraseña. Decide entre cerrar todas las sesiones
o rotar y conservar únicamente la actual, sin mantener su token anterior.
Propaga la nueva cookie y/o estado de login a web y móvil. Comprueba que las
sesiones del navegador y Bearer robadas fallan, mientras el flujo de recuperación
y el cambio obligatorio siguen funcionando. Prueba rollback y concurrencia en DB.

### Abuso de login

Implementa límites atómicos compartidos entre workers/instancias, por identidad
normalizada e IP de una fuente confiable, antes de trabajo caro de hash.
No confíes directamente en `X-Forwarded-For` ni en un diccionario por proceso para
serverless. Comparte presupuesto entre login web/móvil e incluye registro/reset
según su costo. Evita bloqueo permanente de cuentas provocado por terceros.
Define `429`, `Retry-After`, ventanas y recuperación; conserva errores genéricos.
El cooldown de emails de reset no sustituye límites de login.

Prueba con reloj/control de estado, concurrencia, dos instancias, recuperación
de ventana, normalización y proxies confiables. Si se usa WAF, verifica reglas
reales y ambos endpoints; no supongas que existen por el proveedor.

### CSRF

Verifica topología de subdominios, cookies SameSite y peticiones simples.
Para mutaciones con cookie, aplica validación de origen confiable y/o token CSRF.
Compara orígenes completos (esquema/host/puerto) con allowlist explícita; rechaza
`null`, desconocidos y casos ausentes según la política elegida. No desactives
login móvil con Bearer ni resuelvas el problema abriendo CORS con credenciales.
Prueba logout por formulario desde un subdominio same-site y uploads POST
afectados en navegador. TestClient no reproduce políticas del navegador.

## Finalización

Para dependencias, consulta o genera una auditoría de los pins/lockfiles,
deduplica avisos por ID y verifica aplicabilidad: no todos los avisos de un paquete
afectan sus consumidores FastAPI. Actualiza el pin vulnerable a una versión
compatible que cubra los avisos actuales y valida todas las rutas Form/File.
Reejecuta auditoría directa y transitiva; incluye el lock móvil cuando cambie.
Los límites dentro de `file.read()` no protegen el parsing previo de cuerpos.

Ejecuta primero los tests específicos, luego las suites afectadas. La suite
completa de Flagtastic requiere DB desechable y migraciones; su CI documenta
la configuración. Verifica diff, sintaxis, contratos y que no se añadieron
secretos ni se degradaron controles de autorización o caché pública.
Documenta cómo desplegar el parche y las migraciones reversibles si corresponden.
Termina indicando IDs corregidos, pruebas, pendientes y archivos. No despliegues
ni cambies credenciales como efecto implícito de crear esta skill.
