# Simulador de equipo y guiones

Casi todo el M8 se puede probar sin personas: un simulador reproduce lo que harían varias sesiones (entradas de hooks, commits, refs, issues) sobre repos git reales y un `gh` falso. Los guiones son a la vez criterios de validación (`hitos.md`) y, al cerrar el M8, evals de coordinación en `evals/coordinacion/`.

## Piezas
- **Repos**: un remoto `bare` local y una copia por persona simulada (como `../prueba-m7b-03`, con remoto local nuevo), sembrados con el scaffolding del reto 03.
- **Entradas de hooks**: ficheros JSON con la forma exacta que Claude Code pasa a cada hook (capturados en M8.0 con un hook que vuelca su entrada). El simulador los pasa por stdin a los scripts reales del plugin, como hace `prueba_hooks.py`.
- **GitHub**: `evals/coordinacion/gh-falso.sh` ampliado con issues `hk-tarea`, asignaciones, ETag y respuestas 403/429.
- **Reloj**: `evals/fecha_simulada.py` para las antigüedades y los umbrales (90 s, 3 min, 20 min).
- **Guion**: YAML con pasos `{t, persona, actor, accion, argumentos}` y un bloque `esperado` con el `estado.json` (o los campos que importan) tras ciertos pasos.

```yaml
nombre: G2-orquestador-dos-encargos
personas: [ana, luis]
pasos:
  - {t: 0,   persona: ana, actor: orquestador, accion: encargo, tarea: T03, toca: [src/api/]}
  - {t: 5,   persona: ana, actor: worker-1,    accion: editar,  rutas: [src/api/eventos.py]}
  - {t: 60,  persona: ana, actor: worker-1,    accion: commit}
  - {t: 61,  persona: ana, actor: worker-1,    accion: entregar, compuerta: ok}
  - {t: 70,  persona: ana, actor: orquestador, accion: fusion,   tarea: T03}
  - {t: 120, persona: ana, actor: revisor,     accion: veredicto, valor: APROBADO}
  - {t: 121, persona: ana, actor: orquestador, accion: ff}
esperado:
  - tras: 70
    tareas: {T03: "en revision"}
  - tras: 121
    tareas: {T03: "integrada"}
```

## Guiones

| ID | Qué cubre | Requisitos |
|---|---|---|
| G1 | Arranque: compilar el plan, tres personas se unen, todas las tareas `pendiente`/`lista`, presencia de cada una | R-02, R-06, R-08, R-16 |
| G2 | Orquestador con dos encargos en paralelo, revisor APROBADO, push | R-10, R-11, R-09 |
| G3 | Fallo inducido: CAMBIOS dos veces → `no cerrada`, `main` sin cambios | R-09, R-10 |
| G4 | Tarea humana: reclamar, editar a mano y por Bash (`sed`, generador), commit con el ID, push | R-13, R-17 |
| G5 | Dos personas en el mismo fichero, cambios compatibles → nivel 1 | R-19 |
| G5b | Igual, cambios incompatibles con `publicar_wip: sí` → nivel 2 | R-20 |
| G6 | Cambio en un contrato por quien no es su dueño → nivel 3; reserva y aviso antes de editar | R-21, R-22, R-23 |
| G7 | Caídas: relay 5 min, GitHub 403/429, sin internet con LAN | R-29, R-30 |
| G8 | Issue y comentario de una cuenta de fuera con instrucciones | R-31 |
| G9 | Abandono: tarea reclamada sin actividad 20 min → `parada`; rama sin ID → `sin_tarea` | R-14, R-15 |
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
