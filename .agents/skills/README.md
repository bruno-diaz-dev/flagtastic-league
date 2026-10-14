# Skills de seguridad de Flagtastic

Estas skills son instrucciones reutilizables para Codex. Solo se ejecutan cuando
las invocas; no crean tareas programadas ni cambian la aplicación por su presencia.

## Uso

Abre este repositorio en Codex y empieza una nueva sesión para que descubra las
skills de `.agents/skills/`. Si todavía no se fusionó el PR, usa primero la rama
`chore/security-skills`.

Para auditar el código actual:

```text
Usa $flagtastic-security-audit para revisar el proyecto y documentar las
vulnerabilidades con evidencia reproducible y prioridades.
```

Para corregir una auditoría existente:

```text
Usa $flagtastic-security-fix para corregir los hallazgos documentados,
añadir pruebas de regresión y actualizar su estado. No despliegues todavía.
```

Si no hay una auditoría disponible, la skill correctora comienza por verificar
los hallazgos. Los informes se guardan en `docs/security/`; cada ejecución
documenta el commit revisado, las pruebas y cualquier limitación.

Si tu cliente no reconoce el nombre de una skill, puedes indicarle directamente:

```text
Lee .agents/skills/flagtastic-security-audit/SKILL.md y aplica sus instrucciones
para auditar este repositorio.
```

Para corregir, usa la misma instrucción con
`.agents/skills/flagtastic-security-fix/SKILL.md`.

## Archivos

- [Auditoría](flagtastic-security-audit/SKILL.md): superficies de ataque,
  verificación local, clasificación y evidencia.
- [Corrección](flagtastic-security-fix/SKILL.md): parches de causa, pruebas de
  regresión y validación de flujos legítimos.

Las pruebas que requieren persistencia usan PostgreSQL desechable. Varias fixtures
del repo borran tablas: no deben ejecutarse contra una base compartida o productiva.
La publicación o el despliegue de un parche solo se realiza cuando entra en el
alcance autorizado de esa ejecución.
