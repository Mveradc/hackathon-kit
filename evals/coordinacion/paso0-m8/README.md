# Paso 0 de M8: lo que ejecuta el usuario

Material de las tareas K-01 a K-06 (`docs/hackathon-os/tareas.md`). Los resultados van a `docs/coordinacion.md`, en «Hallazgos M8.0».

| Fichero | Para qué |
|---|---|
| `juguetes/juguete/` | K-01 y K-02: hooks que vuelcan su entrada, MCP `jugmcp` con `eco`, agentes `orq`, `orqlibre`, `worker` y `workerlibre` |
| `juguetes/jug-nada`, `jug-sync`, `jug-async` | K-06 (P6): emisor de una línea sin hook, con hook síncrono y con hook `async` |
| `juguetes/jug-monitor/` | P13: monitor que lanza un proceso hijo de larga duración |
| `stash_merge_tree.sh` | K-04 (P9, P11): `bash stash_merge_tree.sh`; tiene que acabar en `Fallos: 0` |
| `sse_prueba.py` | K-05 (P14, P15): servidor SSE con la biblioteca estándar y N clientes |

Todo se prueba en `<PROYECTOS>/prueba-m8-paso0/repo` (un repo con un remoto `bare` local, junto al kit), nunca en el repo del kit. Marcadores que hay que rellenar:
- `<KIT>`: ruta del clon de hackathon-kit, con letra de unidad y barras `/` (por ejemplo, `C:/Users/<tu usuario>/Proyectos/hackathon-kit`). Con `--plugin-dir` tiene que ir así: con `/c/…`, el plugin no carga.
- `<PROYECTOS>`: la carpeta que contiene el kit, escrita como en Git Bash (por ejemplo, `/c/Users/<tu usuario>/Proyectos`).

Desde Git Bash:

```bash
KIT=<KIT>; J=$KIT/evals/coordinacion/paso0-m8/juguetes
cd <PROYECTOS>/prueba-m8-paso0/repo
```

---

## 1. P13: ¿un monitor de plugin puede lanzar un demonio? (≈10 min)

Los monitores solo arrancan en sesión interactiva. El monitor `lanzador` lanza un bash que escribe un latido cada 5 s en `~/hk-p13/latido.log` y luego se queda dormido sin imprimir nada.

1. `rm -rf ~/hk-p13` y abre una sesión: `claude --plugin-dir $J/jug-monitor`.
2. Escribe `hola` y espera la respuesta. En otra terminal de Git Bash:
   `cat ~/hk-p13/lanzador.log; tail -3 ~/hk-p13/latido.log`
   - **Anota:** ¿hay «demonio lanzado»? ¿Avanzan los latidos (repítelo a los 20 s)?
3. Espera 2 minutos sin escribir nada en la sesión.
   - **Anota:** ¿se abrió algún turno solo o apareció un aviso de «monitor terminado»? (No debería: el monitor no imprime ni sale.)
4. Cierra la sesión con `/exit`. Espera 15 s y repite el comando del paso 2.
   - **Anota:** ¿siguen avanzando los latidos tras cerrar? ¿Aparece «monitor recibe señal de salida» en `lanzador.log`?
5. Abre otra vez la sesión (mismo comando) y repite el paso 2.
   - **Anota:** ¿dice «demonio ya vivo» (sobrevivió) o lanza otro?
6. Limpieza: `kill $(cat ~/hk-p13/demonio.pid)`. Si `kill` no lo encuentra, en el Administrador de tareas termina los `bash.exe` sobrantes. Después, `rm -rf ~/hk-p13`.

Lo que decide: si el hijo sobrevive al cierre, el monitor puede lanzar el demonio (ADR-0004) y el pid de `agente.pid` evita duplicados. Si muere con la sesión, el demonio vive lo que dura la sesión, y eso también vale. Si el monitor recibe un aviso de terminado o el hijo no llega a arrancar, la persona lanza `hk-os agente` a mano.

## 2. P6, parte interactiva: latencia percibida y cierre con hooks `async` (≈15 min)

Yo ya medí en `-p` el tiempo de pared con 50 herramientas (ver «Hallazgos M8.0»). Falta lo que solo se ve en interactivo.

1. `rm -rf ~/hk-p6` y abre una sesión con el emisor `async`: `claude --plugin-dir $J/jug-async --model haiku`.
2. Pega este prompt:
   `Ejecuta con Bash el comando "echo N" para N de 1 a 50: diez mensajes seguidos, cada uno con 5 llamadas Bash en paralelo. No escribas nada entre mensajes. Al final responde solo «hecho».`
3. **Anota:** ¿notas algún retraso entre herramientas o un aviso de hooks en la pantalla? Cronometra de enviar a «hecho».
4. Justo al ver «hecho», escribe `/exit`. Luego:
   `wc -l ~/hk-p6/*.jsonl; grep -o '"tipo":"[A-Za-z]*"' ~/hk-p6/*.jsonl | sort | uniq -c`
   - **Anota** las cuentas. Si está todo, deberían salir 50 PreToolUse, 50 PostToolUse, unas 10 PostToolBatch, 1 UserPromptSubmit, 1 Stop, 1 SessionStart y 1 SessionEnd. Si falta alguna de las últimas, el cierre corta los hooks `async` en curso.
5. Repite los pasos 1 a 3 con `jug-sync` y luego con `jug-nada` (en `jug-nada` no se escribe nada). **Anota** los tres tiempos.

## 3. P14: runtime en un Windows limpio (Windows Sandbox, ≈30 min)

Windows Sandbox viene en Windows 10 y 11 Pro, Enterprise y Education (no en Home), pero desactivado.

1. Actívalo una vez, en PowerShell **como administrador**:
   `Enable-WindowsOptionalFeature -Online -FeatureName Containers-DisposableClientVM -All`
   Te pedirá reiniciar. Si sale que la virtualización está desactivada, hay que activarla en la BIOS; en ese caso, dímelo y lo hacemos en el portátil de otra persona.
2. Edita `<KIT>/evals/coordinacion/paso0-m8/sandbox.wsb`: en `<HostFolder>`, cambia `<KIT>` por la ruta del clon del kit con barras de Windows (por ejemplo, `C:\Users\<tu usuario>\Proyectos\hackathon-kit`). Ábrelo con doble clic: monta esta carpeta en el sandbox, en solo lectura, como `C:\paso0`.
3. Dentro del sandbox, en PowerShell (no hay Git Bash), **anota** qué responde cada uno:
   `python --version` · `py --version` · `node --version` · `git --version` · `uv --version`
4. Git Bash, que el kit ya exige: descarga e instala Git for Windows desde https://git-scm.com/download/win con el navegador del sandbox. **Anota** el tiempo y si hizo falta algo más.
5. uv (opción de ADR-0005), en PowerShell:
   `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
   Abre una **Git Bash nueva** y ejecuta:
   `cd /c/paso0 && time uv run --no-project sse_prueba.py --segundos 30`
   **Anota** el tiempo total (incluye la descarga de Python) y si acaba en `OK`.
6. Solo con la biblioteca estándar y sin uv: `python sse_prueba.py --segundos 30`. **Anota** qué pasa. Lo esperado es que no haya Python o que se abra la Microsoft Store.
7. Cierra el sandbox: se borra todo.

## 4. Mensaje para el equipo (P11 y parte de P14)

> ¡Hola! Para preparar la coordinación del hackathon necesito saber qué tenéis instalado. ¿Me pegáis lo que sale de estos comandos? En Windows, desde Git Bash si lo tenéis.
> ```
> git --version
> python --version
> python3 --version
> uv --version
> ```
> Y decidme también el sistema operativo y la versión (Windows 10/11, macOS 14…, Linux y distribución). Si algún comando da error, pegad el error tal cual. ¡Gracias!

## 5. P15: SSE por Tailscale y la red de un evento

Queda pendiente: se prueba en el ensayo de M8h. Cuando toque, en el portátil que haga de relay: `python sse_prueba.py --solo-servidor --host <ip-tailnet> --puerto 7777`; en el otro: `python sse_prueba.py --solo-clientes --url http://<ip-tailnet>:7777 --clientes 1 --ritmo 1 --segundos 1800`. Si hay cortes, la alternativa ya prevista es sondear `GET /v1/estado` con ETag cada 3 s.
