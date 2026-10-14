---
name: flagtastic-security-audit
description: Audita la seguridad de Flagtastic o de una aplicación web propia; revisa autenticación, permisos, sesiones, XSS, CSRF, cargas y dependencias, verifica hallazgos localmente y entrega evidencia y un plan de corrección. Úsala ante solicitudes de hacking ético, brechas, pentest o revisión de seguridad del código.
---

# Auditoría de seguridad

Actúa cuando se solicite auditar código propio o autorizado. Entrega un informe
reproducible; no declares segura una aplicación por pasar un escáner.
La petición de auditar autoriza lectura y reproducciones locales con datos ficticios.
Trabaja sin tocar producción salvo que el usuario haya autorizado ese alcance.
No vuelvas a pedir autorización ya concedida. Si falta el repositorio, búscalo en
el workspace y las conexiones disponibles y solicita únicamente el dato faltante.

## Flujo

1. Lee `AGENTS.md`, las instrucciones aplicables y el estado de Git. Conserva los
   cambios del usuario. Registra repositorio, rama, SHA, fecha y alcance.
2. Identifica tecnologías y configura un entorno aislado. No leas valores de
   secretos ni imprimas variables de entorno. Usa una base desechable para pruebas
   de persistencia; las fixtures de Flagtastic borran tablas. No las conectes a
   desarrollo compartido ni producción. Si solo hay mocks, decláralo expresamente.
3. Traza entrada → validación → autorización → consulta/efecto → salida. Revisa
   rutas web y móviles, middleware, dependencias, repositorios, modelos, migraciones,
   templates, JavaScript, configuración de hosting y CI. No confíes en controles UI.
4. Construye una matriz de permisos: anónimo, jugador, representante propio/ajeno,
   árbitro asignado/no asignado, administrador y cuenta inactiva. Incluye roles
   acumulativos y `must_change_password`. Prueba accesos con y sin cookie/Bearer.
   No uses overrides globales que conviertan una prueba de permisos en admin.
5. Comprueba estas superficies:
   - Identidad y registro: vinculación de perfiles existentes, invitaciones,
     verificación de titularidad y correo, enumeración y concurrencia.
   - Login y recuperación: límites compartidos entre instancias, mensajes/tiempos,
     expiración, tokens de un uso, carreras y costo de hash antes de aplicar límites.
   - Sesiones: entropía, hash en DB, caducidad, revocación tras cambios de credenciales,
     cookies Secure/HttpOnly/SameSite, almacenamiento móvil y caché privada.
   - Autorización por objeto: equipos, roster, resultados, eventos y asistencia;
     prueba IDs de otra cuenta y no solo el rol.
   - XSS: revisa TODOS los sinks (`innerHTML`, atributos, URLs, SVG y scripts).
     Ejecuta la función de escape real; no sustituyas el helper por uno más seguro.
     Prueba comillas, ampersands y etiquetas en nombre, AKA y archivos importados.
   - CSRF: distingue same-origin de same-site; cookies y Bearer; formularios simples
     de peticiones con preflight. Ausencia de middleware no prueba un ataque viable.
   - SQL, archivos y recursos: parámetros frente a interpolación de datos,
     traversal, URL fetching, formatos reales, dimensiones, ZIP descomprimido,
     límites de cuerpo, filas, tiempo y procesos OCR.
   - Exposición de PII, menores, secretos en logs y respuestas, cachés y headers.
   - Dependencias: usa versiones bloqueadas y avisos actuales verificables. No
     inventes CVEs ni equipares versiones antiguas con vulnerabilidades explotables.
6. Reproduce con el mínimo efecto observable. Para XSS basta asignar una marca
   local; no extraigas cookies ni datos. Para login usa pocos intentos sintéticos;
   no hagas fuerza bruta ni estrés contra servicios reales.
7. Guarda informe y reproducciones en el repo. Incluye también controles que
   funcionaron, áreas no verificadas y requisitos para validación posterior.

## Entrega y clasificación

Para cada hallazgo incluye ID estable, título, severidad razonada, CWE si aplica,
estado (confirmado, condicionado o hipótesis), archivo/línea y SHA, entrada
controlable, precondiciones, pasos locales, observado/esperado, impacto,
corrección propuesta y criterio de aceptación. Separa endurecimiento de brechas.
No atribuyas escalada o filtración a una prueba que solo creó un atributo.

En Flagtastic guarda los informes en `docs/security/audit-AAAA-MM-DD.md` y
las reproducciones locales mínimas en una ubicación documentada del repositorio.
Si existe una auditoría previa, úsala como punto de partida y vuelve a comprobar
la evidencia contra el SHA actual. Un script que caracteriza un comportamiento
vulnerable puede pasar cuando el problema existe: documenta esa diferencia y
no lo uses como gate de seguridad sin invertir sus expectativas.

## Comandos de referencia

Desde la raíz del repo, con un entorno Python aislado y sin credenciales productivas:

```bash
python -m pytest -q tests/test_web_pages.py tests/test_ui_contract.py tests/test_roster_deadline.py
node --test tests/js/*.test.cjs
```

Añade reproducciones para los hallazgos del código actual; no presupongas que
ya existen scripts de auditoría. Para pruebas DOM instala jsdom o Playwright en
un entorno aislado y registra la versión. Las suites de integración completas
requieren PostgreSQL desechable migrado; consulta `.github/workflows/ci.yml`.
Registra resultados y bloqueos reales.

Termina con los riesgos prioritarios, enlaces al informe, las pruebas ejecutadas
y los límites de la revisión. Para reparar, usa `$flagtastic-security-fix`.
