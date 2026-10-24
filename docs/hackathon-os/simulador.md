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
- **Esperado**: lista de `{tras, tareas?, declarado?, activos?, sin_tarea?, discrepancias?}`: los campos que importan del `estado.json` calculado con `ahora` = `tras` (puede ser posterior al último paso, para que pase el tiempo). Desde M8g, también `colisiones?` y `reservas?`; desde M11, `observado_en?` (`{id de colisión: hora}`).
- **Conflictos del nivel 2** (M11, opcional): `conflictos` = `[{t, pares: [{personas, rutas, rutas_2b?}]}]`, lo que daría el `Calculo` del relay en cada ciclo. El simulador pone `desde` y `desde_2b` como el Calculo: la hora del primer ciclo desde el que el par tiene seguidas las mismas rutas.

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
| G13 | Vista de jurado (M10, criterio 2): notas de `criterios.md` y etiquetas `(criterios: …)` del plan y del pitch, con las tareas avanzando hasta `publicada` | R-35, R-28 |
| G14 | Ruta crítica (M10, criterio 3): el plan del reto 03 en sus 39 h, con commits, descansos y un ajuste del plan, en dos ramas (bien y con riesgo) | R-36, R-28 |
| G15 | Nivel 2b (M11, criterio 3): un conflicto que baja a 2b, otro que sigue rojo y uno que pasa de 2b a rojo | R-34, R-28 |

### G13 y G14 (M10, K-105)
Ficheros en `evals/coordinacion/simulador/guiones/` (`G13.json`, `G14.json`, `G14r.json` y las carpetas `g13/` y `g14/`, con las entradas, `hechos.json` y `casos.json`). Lo que tiene que salir son **hechos** por momento (la hora del reloj simulado) y **casos**: cada caso parte de un momento y cambia una entrada con reemplazos de texto `[de, a, veces]`.
- **G13** (jurado): 8 notas de `/hack-note` y de Anotar, cada una en `main` desde su `en_main_desde`: dos en el mismo minuto (el plan las cita con «· quién»), una que corrige a otra, una de fuerza `dato` recogida solo en `pitch.md` y una con texto imperativo. Momentos M1, M2, M2b y M3 del sábado, con T11 publicada que vuelve a `en_curso` y se para (sigue `cubierta`, con «trabajo nuevo desde»), T20 cerrada a mano (⚑: `planificada`, nunca `cubierta`) y persona-c sin señales. Casos: una cita ambigua, un enlace roto (`sin_nota`), una Prueba que falla (se enseña y no cambia la cobertura) y el orden por fuerza.
- **G14** (ruta): `equipo.md` y `plan.md` en dos versiones (el ajuste del sábado a las 09:31 pone el Inicio, cambia plazos y deja T18 con `[SI DA TIEMPO]`). Momentos «inicio» (sin Inicio: «sin plazo» y pocos datos), «mitad bien» (`a_tiempo`) y, en la otra rama, «mitad con riesgo» (`no_llega`: plazos pasados que arrastran por `depende_de` y por el orden del plan, riesgos por estimación, persona-c sin señales). Casos: sin `Entrega:`, dos horas, un desfase que no es una segunda hora, «(confirmar)», un ciclo, el relay caído (estimación vieja, con su dato más viejo), un descanso de «Todos» y otro que cruza la entrega, y la cadena de cada persona.

`evals/coordinacion/simulador/g13_g14.py` los comprueba dos veces:
1. **Con las reglas del contrato escritas otra vez** (sin `hkos/jurado.py` ni `hkos/ruta.py`): que los hechos son lo que dicen `api.md` §11.2–§11.4 y las decisiones del issue #46.
2. **Con el código de verdad** (`m10.py`): los ficheros de cada momento en un repo de git con su historia (un remoto `bare` temporal y el clon del relay), `hkos/relay.py` con `vista_jurado` y `ruta_critica` (lee `origin/main` con `hkos/lecturas.py` y reconstruye la historia de cada tarea desde los eventos) y `proyeccion.vista`. Cada bloque valida contra `$defs/vista_jurado` o `$defs/vista_ruta` y, con la forma de los hechos, coincide con ellos en cada momento y caso: cobertura, tareas, evidencia (sha y hora), orden y cuenta; veredicto, rango, base, plazos pasados y lo que arrastran, sin plazo, fuera de la entrega, riesgos, cadena, descansos y resumen. Lo que el código da distinto por el contrato o por `hkos/ruta.py` va en `CONOCIDAS`, con su porqué: se enseña una a una y falla si deja de salir.

Cada parte tiene sus controles: con un hecho cambiado, el script tiene que fallar.

`igualdad.py` (criterio 4) corre G13 y G14 con los dos interruptores por el mismo camino: los bloques `jurado` y `ruta` enteros, iguales en la vista del relay, en la del demonio y en el MCP (con la misma hora), y la línea de `## Jurado y ruta` de `estado-equipo.md` de cada persona, el `resumen` de cada bloque con su hora, su fuente y «viejo». En G1–G6 y G12, sin los bloques: ni la sección ni las firmas, y `tools/list` del MCP es el de la 0.4.0.

G10 ampliado (criterio 6 de M10) está en `hkos/pruebas/test_proyeccion_m10.py`: 30 minutos con el reloj corriendo, la hora estimada y el margen moviéndose y ni la cobertura ni el veredicto cambiando, `delta.sh` no inyecta nada.

### G15 (M11, K-112)
`guiones/G15.json`, con `fusion_estructural: sí` en el relay: los `conflictos` de cada ciclo del nivel 2 llegan escritos en el guion con la forma de ADR-0014 (`[{personas, rutas, rutas_2b, desde, desde_2b}]`), sin Mergiraf ni el Calculo de verdad (los prueba `test_colisiones_2b.py`, K-111). Tres personas:
- A y B tocan `motor/imports.py`, `motor/config.json`, `web/src/App.jsx` y `README.md`. En el primer ciclo, los tres primeros en rojo (`2:`); en el segundo, Mergiraf resuelve los dos de `motor/` (`2b:` amarillo) y `App.jsx` sigue rojo. `README.md`, sin conflicto, se queda en el nivel 1; lo del 2 y el 2b, no.
- A y C chocan en `datos/carga.py`: baja a 2b y, cuando C vuelve a cambiar una línea de A, vuelve a rojo.
- `desde_2b` no se mueve mientras el conjunto de rutas no cambia, aunque llegue en otro orden (`observado_en` en el esperado).

`simula.py` y `prueba_simulador.py` lo corren con los demás. `igualdad.py` (criterio 3 de M11) lo pasa por el relay de verdad, con un Calculo fijo que devuelve los `conflictos` del ciclo: la colisión `2b` es la misma en la vista del relay, en la del demonio y en el MCP, y en `estado-equipo.md` de cada persona sale como `- AMARILLO · nivel 2b · fusión estructural sin conflictos · …`. En G1–G6 y G12–G14, ninguna `2b`. El caso del issue #77, A3, que `igualdad.py` llamaba G15, pasa a llamarse «#77, A3».

El criterio 4 de M11 (delta y monitor, con `delta.sh` y `escucha.sh` tal como están) y el 1 sin relay vivo (apagado, byte a byte como en la 0.5.0) están en `hkos/pruebas/test_proyeccion_m11.py`.

## Qué mide cada pasada
- Estados correctos frente a los esperados (% y lista de discrepancias).
- Tiempo desde la señal hasta que aparece en `estado.json` y en la web.
- Antigüedad máxima mostrada por fuente.
- Caracteres inyectados por sesión (inicio y deltas).
- Escrituras a GitHub por hora.
- Coincidencia entre web, `estado-equipo.md` y MCP (R-28).

## Lo que el simulador no cubre
Si las personas entienden la web, si los agentes hacen caso de los avisos y si el arranque cabe en 10 minutos con gente real. Eso es el ensayo de M8h.
