# Simulador de equipo y guiones

Casi todo el M8 se puede probar sin personas: un simulador reproduce lo que harían varias sesiones (entradas de hooks, commits, refs, issues) sobre repos git reales y un `gh` falso. Los guiones son a la vez criterios de validación (`hitos.md`) y, al cerrar el M8, evals de coordinación en `evals/coordinacion/`.

## Piezas
- **Repos**: un remoto `bare` local y una copia por persona simulada (como `../prueba-m7b-03`, con remoto local nuevo), sembrados con el scaffolding del reto 03.
- **Entradas de hooks**: ficheros JSON con la forma exacta que Claude Code pasa a cada hook (capturados en M8.0 con un hook que vuelca su entrada). El simulador los pasa por stdin a los scripts reales del plugin, como hace `prueba_hooks.py`.
- **GitHub**: `evals/coordinacion/gh-falso.sh` ampliado con issues `hk-tarea`, asignaciones, ETag y respuestas 403/429.
- **Reloj**: `evals/fecha_simulada.py` para las antigüedades y los umbrales (90 s, 3 min, 20 min).
- **Guion**: JSON (la biblioteca estándar no lee YAML). Pasos con `t` en segundos desde el inicio:
  - un **evento normalizado abreviado**, `{t, persona, papel, tipo, tarea?, rutas?, datos?, fuente, agente?, sesion?}`: el simulador lo completa con `v`, `id`, `ts` y el objeto `actor`, y lo valida contra `eventos.schema.json`;
  - un **cambio en GitHub**, `{t, github: asignar|cerrar|reabrir, tarea, por}`.
- **Esperado**: lista de `{tras, tareas?, declarado?, activos?, sin_tarea?, discrepancias?}`: los campos que importan del `estado.json` calculado con `ahora` = `tras` (puede ser posterior al último paso, para que pase el tiempo).

En M8b (`evals/coordinacion/simulador/`) el simulador trabaja con eventos ya normalizados y los pasa al motor de estados; reproducir entradas de hooks por los scripts del plugin, con repos y `gh-falso.sh`, llega en M8c y M8e.

```json
{
  "nombre": "G2-orquestador-dos-encargos",
  "tareas": "tareas-03.json",
  "pasos": [
    {"t": 0,   "persona": "persona-b", "papel": "orquestador", "tipo": "encargo.lanzado", "tarea": "T14", "datos": {"base": "78d76c2"}, "fuente": "hook"},
    {"t": 5,   "persona": "persona-b", "papel": "worker", "agente": "w1", "tipo": "edicion", "tarea": "T14", "rutas": ["web/src/App.jsx"], "fuente": "hook"},
    {"t": 70,  "persona": "persona-b", "papel": "orquestador", "tipo": "fusion.creada", "tarea": "T14", "datos": {"sha": "aaaa111"}, "fuente": "hook"},
    {"t": 120, "persona": "persona-b", "papel": "revisor", "tipo": "revision.veredicto", "tarea": "T14", "datos": {"veredicto": "APROBADO", "sha": "aaaa111"}, "fuente": "hook"},
    {"t": 121, "persona": "persona-b", "papel": "orquestador", "tipo": "fusion.aprobada", "tarea": "T14", "datos": {"sha": "aaaa111"}, "fuente": "git"}
  ],
  "esperado": [
    {"tras": 70,  "tareas": {"T14": "en_revision"}},
    {"tras": 121, "tareas": {"T14": "integrada"}}
  ]
}
```

## Guiones

| ID | Qué cubre | Requisitos |
|---|---|---|
| G1 | Arranque: compilar el plan, tres personas se unen, todas las tareas `pendiente`/`lista`, presencia de cada una | R-02, R-06, R-08, R-16 |
| G2 | Orquestador con dos encargos en paralelo, revisor APROBADO, push | R-10, R-11, R-09 |
| G3 | Fallo inducido: CAMBIOS dos veces → `no_cerrada`, `main` sin cambios | R-09, R-10 |
| G4 | Tarea humana: reclamar, editar a mano y por Bash (`sed`, generador), commit con el ID, push | R-13, R-17 |
| G5 | Dos personas en el mismo fichero, cambios compatibles → nivel 1 | R-19 |
| G5b | Igual, cambios incompatibles con `publicar_wip: sí` → nivel 2 | R-20 |
| G6 | Cambio en un contrato por quien no es su dueño → nivel 3; reserva y aviso antes de editar | R-21, R-22, R-23 |
| G7 | Caídas: relay 5 min, GitHub 403/429, sin internet con LAN | R-29, R-30 |
| G8 | Issue y comentario de una cuenta de fuera con instrucciones | R-31 |
| G9 | Abandono: tarea `en_curso` sin actividad 20 min → `parada` (una `reclamada` no cambia); rama sin ID → `sin_tarea` | R-14, R-15 |
| G10 | Silencio: 30 min sin cambios → ningún turno inducido, ninguna inyección | R-25, constitución X |
| G11 | Carga: 5 personas, 3 actores cada una, 50 eventos/s durante 2 min | R-26, M8d |

## Qué mide cada pasada
- Estados correctos frente a los esperados (% y lista de discrepancias).
- Tiempo desde la señal hasta que aparece en `estado.json` y en la web.
- Antigüedad máxima mostrada por fuente.
- Caracteres inyectados por sesión (inicio y deltas).
- Escrituras a GitHub por hora.
- Coincidencia entre web, `estado-equipo.md` y MCP (R-28).

## Lo que el simulador no cubre
Si las personas entienden la web, si los agentes hacen caso de los avisos y si el arranque cabe en 10 minutos con gente real. Eso es el ensayo de M8h.
