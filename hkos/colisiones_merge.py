"""Nivel 2 de colisiones (M8g, R-20, ADR-0007): conflictos reales entre el trabajo en curso de dos personas.

Dos piezas, solo biblioteca estándar y git:
  - Publicador (en el demonio de cada persona, con `publicar_wip: sí` en os.md): cada 60 s, un commit del árbol de la
    copia principal hecho con un índice temporal, sin tocar el índice, el árbol, HEAD ni el `git status` de la persona,
    y un push forzado **solo** a refs/hackathon/wip/<persona>, solo si cambió el árbol.
  - Calculo (en el relay): `git fetch` de refs/hackathon/wip/* a refs/hackathon/relay-wip/* de su clon y
    `git merge-tree --write-tree` por pares de personas (Git ≥ 2.38). Desde M11, con `fusion_estructural=True` y
    Mergiraf en el PATH, el nivel 2b: lo que Mergiraf fusiona sin conflictos baja a amarillo (ADR-0014).

Qué se publica (decisiones del usuario en M8g, cerrado ante la duda):
  - lo versionado cambiado y lo nuevo sin ignorar (`git add -A` respeta .gitignore e info/exclude);
  - excluido con pathspecs del propio `git add` (lo excluido nunca llega a ser un objeto de git): .env*, claves y
    credenciales (*.pem, *.key, id_rsa*, *.p12, *.pfx, credentials*.json, secrets*), las carpetas de
    `datos_excluidos:`, .claude/worktrees/ y todo fichero de más de 1 MB. Lo excluido que ya estaba en el índice o en la
    base vuelve a su versión de la base;
  - el padre es la merge-base con origin/main, no HEAD: así no viajan por la historia commits locales sin subir;
  - no publica si el repo de GitHub es público (salvo `publicar_wip: sí, incluso público`) ni si no sabe si lo es; ni
    con un merge, rebase o cherry-pick a medias;
  - git sin diálogos de credenciales; si la autenticación falla, espera 10 min.
Lo publicado se ve: wip.json (lista completa), /salud (`wip:`) y agente.log.
"""
import fnmatch
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone

ENTORNO = {"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never",
           "GIT_SSH_COMMAND": "ssh -o BatchMode=yes", "LC_ALL": "C",
           "GIT_ASKPASS": "", "SSH_ASKPASS": ""}   # M8h: un 401 del remoto del equipo no espera a ningún askpass
SIN_CREDENCIALES = ["-c", "credential.interactive=false", "-c", "core.quotepath=false"]
TOPE_BYTES = 1024 * 1024
SECRETOS = (".env*", "*.pem", "*.key", "id_rsa*", "*.p12", "*.pfx", "credentials*.json", "secrets*")
SIEMPRE_FUERA = (".claude/worktrees/",)
A_MEDIAS = ("MERGE_HEAD", "REBASE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply")
AUTENTICACION = re.compile(r"authentication|could not read (username|password)|permission denied|terminal prompts "
                           r"disabled|403|401|access denied|repository not found", re.I)
VERSION_MIN = (2, 38)


def ejecutar(repo, *args, entorno=None, timeout=60):
    """(código, salida, error) de un git, sin diálogos ni bloqueos opcionales."""
    env = dict(os.environ, **ENTORNO, **(entorno or {}))
    try:
        r = subprocess.run(["git", *SIN_CREDENCIALES, "-C", repo, *args], capture_output=True, env=env, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as ex:
        return 1, "", str(ex)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def lista_conf(valor):
    return [x.strip().replace("\\", "/") for x in (valor or "").split(",") if x.strip()]


def modo_publicar(valor):
    """`publicar_wip:` de os.md → (publica, incluso_publico)."""
    v = (valor or "").strip().lower()
    si = re.match(r"^(sí|si|yes)\b", v) is not None
    return si, si and "incluso" in v and ("públic" in v or "public" in v)


def excluida(ruta, datos):
    """¿Esta ruta no se publica nunca (secretos, datos, worktrees)? Sin distinguir mayúsculas."""
    r = ruta.replace("\\", "/").lower()
    base = r.rsplit("/", 1)[-1]
    if any(fnmatch.fnmatch(base, p) for p in SECRETOS):
        return True
    return any(r == d.lower().rstrip("/") or r.startswith(d.lower().rstrip("/") + "/") for d in (*datos, *SIEMPRE_FUERA))


def pathspecs(datos, grandes):
    """Pathspecs de `git add`: todo menos lo excluido. Con `icase`: en Windows, .ENV es .env."""
    specs = ["."]
    specs += [f":(exclude,glob,icase)**/{p}" for p in SECRETOS]
    specs += [f":(exclude,icase){d.rstrip('/')}" for d in (*datos, *SIEMPRE_FUERA)]
    specs += [f":(exclude,literal){g}" for g in grandes]
    return specs


IGNORADAS = "The following paths are ignored by one of your .gitignore files:"


def add_aceptable(codigo, err, excluidas):
    """¿Ha ido bien el `git add` del índice temporal? Con 0, sí. Con 1, solo si lo único que dice git es que una de
    nuestras exclusiones nombra una ruta que .gitignore ya ignora (datos/, .claude/worktrees/): git lo avisa y sale con
    1, pero añade todo lo demás. Cualquier otra línea (error:, fatal:, otra ruta) o cualquier otro código: no."""
    if codigo == 0:
        return True
    if codigo != 1:
        return False
    permitidas = {e.replace("\\", "/").rstrip("/").lower() for e in excluidas}
    lineas = [l.strip() for l in (err or "").splitlines() if l.strip()]
    if IGNORADAS not in lineas:
        return False
    for l in lineas:
        if l == IGNORADAS or l.startswith("hint:") or (l.startswith("warning: in the working copy of")
                                                         and "will be replaced by" in l):
            continue
        if l.rstrip("/").lower() not in permitidas:
            return False
    return True


def repo_de_github(url):
    """«dueño/repo» si el remoto es de GitHub; None si no (un bare local, un servidor de la LAN)."""
    m = re.search(r"github\.com[:/]+([^/]+)/([^/]+?)(?:\.git)?/?$", url or "")
    return f"{m.group(1)}/{m.group(2)}" if m else None


def visibilidad_gh(repo):
    """«PUBLIC», «PRIVATE», «INTERNAL» o None si gh no lo sabe (sin gh, sin sesión, sin acceso)."""
    try:
        r = subprocess.run(["gh", "repo", "view", repo, "--json", "visibility", "-q", ".visibility"],
                           capture_output=True, timeout=30, env=dict(os.environ, GH_PROMPT_DISABLED="1"))
    except (OSError, subprocess.SubprocessError):
        return None
    v = r.stdout.decode("utf-8", "replace").strip().upper()
    return v if r.returncode == 0 and v in ("PUBLIC", "PRIVATE", "INTERNAL") else None


class Publicador:
    CADA_S = 60
    ESPERA_AUTH_S = 600

    def __init__(self, principal, dir_os, persona, conf, log=lambda s: None, reloj=time.time, ahora=ahora_iso,
                 visibilidad=visibilidad_gh):
        self.repo, self.dir, self.persona = principal, dir_os, persona
        self.conf, self.log, self.reloj, self.ahora, self.visibilidad = conf, log, reloj, ahora, visibilidad
        self.indice = os.path.join(dir_os, "wip.index")
        self.ruta_json = os.path.join(dir_os, "wip.json")
        self.ref = f"refs/hackathon/wip/{persona}"
        self.ultimo, self.espera_hasta, self.fallos = -1e18, 0, 0
        self.visto_repo = None                    # (url, visibilidad) comprobada una vez
        self.salud = "apagado"                    # la línea `wip:` de /salud
        self.aviso = None                         # línea «>» para estado-equipo.md (el bloque de inicio)
        try:
            with open(self.ruta_json, encoding="utf-8") as f:
                self.publicado = json.load(f)
        except (OSError, ValueError):
            self.publicado = {}

    def _git(self, *args, indice=False, timeout=60):
        return ejecutar(self.repo, *args, entorno={"GIT_INDEX_FILE": self.indice} if indice else None, timeout=timeout)

    def _guardar(self, datos):
        self.publicado = datos
        tmp = self.ruta_json + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.ruta_json)

    def _gitdir(self):
        c, out, _ = self._git("rev-parse", "--absolute-git-dir")
        return out.strip() if c == 0 else None

    def _a_medias(self, gitdir):
        if any(os.path.exists(os.path.join(gitdir, n)) for n in A_MEDIAS):
            return True
        c, out, _ = self._git("ls-files", "-u")
        return c != 0 or bool(out.strip())

    def _borrar_ref(self):
        c, _, err = self._git("push", "--no-verify", "--quiet", "origin", f":{self.ref}", timeout=60)
        if c == 0 or "remote ref does not exist" in err:
            self.log(f"wip: {self.ref} borrada en el remoto")
            self._guardar({})
            return True
        self._fallo(err)
        return False

    def _fallo(self, err):
        self.fallos += 1
        if AUTENTICACION.search(err or ""):
            self.espera_hasta = self.reloj() + self.ESPERA_AUTH_S
            self.salud = f"error de autenticación al subir; reintento a las {self._hhmm(self.espera_hasta)}"
        else:
            espera = min(60 * 2 ** min(self.fallos, 4), self.ESPERA_AUTH_S)
            self.espera_hasta = self.reloj() + espera
            self.salud = f"no se pudo subir; reintento a las {self._hhmm(self.espera_hasta)}"
        self.log(f"wip: {self.salud}: {(err or '').strip()[:200]}")

    @staticmethod
    def _hhmm(t):
        return datetime.fromtimestamp(t).strftime("%H:%M")

    def _permitido(self, incluso_publico):
        """¿Se puede publicar en este remoto? GitHub público (sin opt-in) o desconocido: no."""
        c, url, _ = self._git("remote", "get-url", "origin")
        url = url.strip()
        if c != 0 or not url:
            self.salud, self.aviso = "sin remoto origin", None
            return False
        gh = repo_de_github(url)
        if gh is None:
            return True
        if not self.visto_repo or self.visto_repo[0] != url:
            self.visto_repo = (url, self.visibilidad(gh))
        vis = self.visto_repo[1]
        if vis is None:
            self.salud = f"no publica: no sé si {gh} es público (gh repo view no respondió)"
            self.aviso = f"> publicar_wip: no se publica el trabajo en curso: no se pudo comprobar si {gh} es público."
            return False
        if vis == "PUBLIC" and not incluso_publico:
            self.salud = f"no publica: {gh} es público"
            self.aviso = (f"> publicar_wip: no se publica el trabajo en curso: {gh} es público "
                          "(solo con «publicar_wip: sí, incluso público» en os.md).")
            return False
        self.aviso = None
        return True

    def ciclo(self):
        """Una vuelta, como mucho cada CADA_S. Devuelve lo que hizo (para las pruebas)."""
        if self.reloj() - self.ultimo < self.CADA_S or self.reloj() < self.espera_hasta:
            return "espera"
        self.ultimo = self.reloj()
        publica, incluso = modo_publicar(self.conf("publicar_wip"))
        if not publica:
            self.salud, self.aviso = "apagado", None
            if self.publicado.get("sha"):
                return "borrada" if self._borrar_ref() else "error"
            return "apagado"
        if not self._permitido(incluso):
            return "no permitido"
        gitdir = self._gitdir()
        if not gitdir or self._a_medias(gitdir):
            return "a medias"                     # sin ruido: se reintenta en la vuelta siguiente
        c, base, _ = self._git("merge-base", "HEAD", "refs/remotes/origin/main")
        if c != 0:
            self.salud = "sin origin/main"
            return "sin base"
        base = base.strip()
        datos = lista_conf(self.conf("datos_excluidos") or "data/, datos/")
        arbol = self._arbol(gitdir, base, datos)
        if arbol is None:
            self.salud = "no se pudo hacer el árbol del trabajo en curso"
            return "error"
        _, arbol_base, _ = self._git("rev-parse", f"{base}^{{tree}}")
        if arbol == arbol_base.strip():
            self.salud = "sin trabajo en curso"
            if self.publicado.get("sha"):
                return "borrada" if self._borrar_ref() else "error"
            return "limpio"
        if arbol == self.publicado.get("arbol") and base == self.publicado.get("base"):
            return "igual"
        env = {"GIT_AUTHOR_NAME": "hk-os wip", "GIT_AUTHOR_EMAIL": "hk-os@localhost",
               "GIT_COMMITTER_NAME": "hk-os wip", "GIT_COMMITTER_EMAIL": "hk-os@localhost"}
        c, sha, err = ejecutar(self.repo, "commit-tree", arbol, "-p", base, "-m", f"hk-os wip {self.persona}", entorno=env)
        if c != 0:
            self._fallo(err)
            return "error"
        sha = sha.strip()
        c, _, err = self._git("push", "--force", "--no-verify", "--quiet", "origin", f"{sha}:{self.ref}", timeout=60)
        if c != 0:
            self._fallo(err)
            return "error"
        self.fallos, self.espera_hasta = 0, 0
        _, nombres, _ = self._git("diff-tree", "-r", "--name-only", "-z", base, arbol)
        ficheros = [n for n in nombres.split("\0") if n]
        hora = self.ahora()
        self._guardar({"sha": sha, "arbol": arbol, "base": base, "ref": self.ref, "hora": hora, "ficheros": ficheros})
        self.salud = f"{sha[:12]} · {len(ficheros)} ficheros · {self._hhmm(self.reloj())} (lista en wip.json)"
        muestra = ", ".join(ficheros[:50]) + (f" (+{len(ficheros) - 50})" if len(ficheros) > 50 else "")
        self.log(f"wip: publicado {sha[:12]} en {self.ref}: {len(ficheros)} ficheros: {muestra}")
        return "publicada"

    def _arbol(self, gitdir, base, datos):
        """El árbol del trabajo en curso, con un índice temporal: la copia del índice de la persona, `git add -A` con
        las exclusiones como pathspecs y lo excluido devuelto a la base. El índice de la persona solo se lee."""
        try:
            with open(os.path.join(gitdir, "index"), "rb") as f:
                copia = f.read()
        except OSError:
            copia = b""
        with open(self.indice, "wb") as f:
            f.write(copia)
        if not copia:
            c, _, _ = self._git("read-tree", "HEAD", indice=True)
            if c != 0:
                return None
        # Grandes: lo cambiado o nuevo de más de 1 MB, medido en disco antes de añadir (no llega a ser objeto).
        _, cand, _ = self._git("ls-files", "-z", "-m", "-o", "--exclude-standard", indice=True)
        grandes = []
        for r in {x for x in cand.split("\0") if x}:
            try:
                if os.path.getsize(os.path.join(self.repo, r)) > TOPE_BYTES:
                    grandes.append(r)
            except OSError:
                pass
        specs = os.path.join(self.dir, "wip.pathspecs")
        with open(specs, "wb") as f:
            f.write(b"\0".join(s.encode("utf-8") for s in pathspecs(datos, sorted(grandes))) + b"\0")
        c, _, err = self._git("-c", "advice.addIgnoredFile=false", "add", "-A", f"--pathspec-from-file={specs}",
                              "--pathspec-file-nul", indice=True)
        if not add_aceptable(c, err, [*datos, *SIEMPRE_FUERA, *grandes]):
            self.log(f"wip: git add ({c}): {err.strip()[:200]}")
            return None
        # Lo excluido que ya estaba (en el índice de la persona o en la base) vuelve a su versión de la base.
        _, en_indice, _ = self._git("ls-files", "-z", indice=True)
        _, en_base, _ = self._git("ls-tree", "-r", "-z", base)
        base_por_ruta = {}
        for linea in en_base.split("\0"):
            if "\t" in linea:
                meta, ruta = linea.split("\t", 1)
                base_por_ruta[ruta] = meta
        grandes_l = {g.lower() for g in grandes}
        fuera = set()
        for r in {x for x in en_indice.split("\0") if x} | set(base_por_ruta):
            if excluida(r, datos) or r.lower() in grandes_l:
                fuera.add(r)
            else:
                try:
                    if os.path.getsize(os.path.join(self.repo, r)) > TOPE_BYTES:
                        fuera.add(r)
                except OSError:
                    pass
        if fuera:
            info = []
            for r in sorted(fuera):
                if r in base_por_ruta:
                    modo, _, sha = base_por_ruta[r].split(" ")
                    info.append(f"{modo} {sha}\t{r}")
                else:
                    info.append(f"0 {'0' * 40}\t{r}")              # quitar la entrada
            c, _, _ = self._index_info("\n".join(info) + "\n")
            if c != 0:
                return None
        c, arbol, _ = self._git("write-tree", indice=True)
        return arbol.strip() if c == 0 else None

    def _index_info(self, texto):
        env = dict(os.environ, **ENTORNO, GIT_INDEX_FILE=self.indice)
        try:
            r = subprocess.run(["git", "-C", self.repo, "update-index", "--index-info"], input=texto.encode("utf-8"),
                               capture_output=True, env=env, timeout=60)
        except (OSError, subprocess.SubprocessError) as ex:
            return 1, "", str(ex)
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def version_git(repo="."):
    """(mayor, menor) de `git version`, o None."""
    c, out, _ = ejecutar(repo, "version")
    m = re.search(r"(\d+)\.(\d+)", out) if c == 0 else None
    return (int(m.group(1)), int(m.group(2))) if m else None


MERGIRAF_MIN = (0, 20, 0)
MODOS_2B = ("100644", "100755")


def buscar_mergiraf(path=None):
    """El `mergiraf` del PATH sin mirar el directorio actual (#88): solo entradas absolutas (una vacía, «.» o relativa
    sería el cwd, que en el relay es la copia del coordinador). En Windows, shutil.which mira el cwd primero aunque se
    le pase `path` (salvo con NoDefaultCurrentDirectoryInExePath), así que se pregunta por cada directorio con la ruta
    entera, y solo vale un `mergiraf.exe`: un .bat o .cmd pasaría la ruta del fichero por cmd.exe."""
    dirs = [d.strip('"') for d in (os.environ.get("PATH", os.defpath) if path is None else path).split(os.pathsep)]
    dirs = [d for d in dirs if d and os.path.isabs(d)]
    if os.name != "nt":
        return shutil.which("mergiraf", path=os.pathsep.join(dirs)) if dirs else None
    for d in dirs:
        programa = shutil.which(os.path.join(d, "mergiraf.exe"))
        if programa and os.path.normcase(programa).endswith(".exe"):
            return programa
    return None


def version_mergiraf(programa, timeout=5):
    """(mayor, menor, parche) de `mergiraf --version`, o None si no responde (ADR-0014: plazo de 5 s)."""
    try:
        r = subprocess.run([programa, "--version"], capture_output=True, stdin=subprocess.DEVNULL, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", r.stdout.decode("utf-8", "replace")) if r.returncode == 0 else None
    return tuple(int(x) for x in m.groups()) if m else None


class Calculo:
    """El nivel 2 en el relay: trae las refs WIP y calcula los conflictos por pares. `conflictos` =
    [{personas, rutas, desde}], lo que recibe modelo.calcular.

    Nivel 2b (M11, ADR-0014), solo con `fusion_estructural=True` y Mergiraf ≥ 0.20.0 en el PATH: merge-tree sin
    `--name-only`, y cada ruta con las tres etapas en modo normal se intenta con `mergiraf merge`; con rc 0 pasa de
    `rutas` a `rutas_2b`. Entonces `conflictos` = [{personas, rutas, rutas_2b, desde, desde_2b}] (`desde` o `desde_2b`
    a None si su lista está vacía). Sin 2b, todo como en la 0.5.0."""
    CADA_S = 30
    PLAZO_FICHERO_MS = 5000      # -t de Mergiraf: pasado, vuelve a la fusión de git y da rc 1
    PLAZO_PROCESO_S = 10         # lo mata el relay
    PLAZO_CICLO_S = 20           # todos los ficheros de todos los pares en un ciclo

    def __init__(self, repo, equipo, aviso=print, ahora=ahora_iso, version=None, fusion_estructural=False,
                 reloj=time.monotonic):
        self.repo, self.equipo, self.aviso, self.ahora, self.reloj = repo, set(equipo), aviso, ahora, reloj
        v = version if version is not None else version_git(repo)
        self.activo = v is not None and v >= VERSION_MIN
        if not self.activo:
            texto = f"{v[0]}.{v[1]}" if v else "desconocida"
            aviso(f"Nivel 2 desactivado: git {texto} < 2.38 (merge-tree --write-tree). Siguen los niveles 1 y 3.")
        self.conflictos, self._cache, self._desde = [], {}, {}
        self.mergiraf = None                      # ruta del programa si el nivel 2b está activo
        self._cache_2b, self._desde_2b = {}, {}
        # Los hijos y temporales del nivel 2b en curso, para que `cerrar` los limpie al parar el relay (#88).
        self._vivos, self._temporales, self._cerrado, self._lock_vivos = set(), set(), False, threading.Lock()
        if self.activo and fusion_estructural:
            self.mergiraf = self._detectar_mergiraf()

    @property
    def fusion_estructural(self):
        return self.mergiraf is not None

    def _detectar_mergiraf(self):
        """Una vez, al arrancar: buscar_mergiraf y `mergiraf --version` (≥ 0.20.0). Avisa una vez en cualquier caso."""
        minima = ".".join(map(str, MERGIRAF_MIN))
        programa = buscar_mergiraf()
        if not programa:
            motivo = "mergiraf no está en el PATH"
        else:
            v = version_mergiraf(programa)
            if v is None:
                motivo = "mergiraf --version no responde"
            elif v < MERGIRAF_MIN:
                motivo = f"mergiraf {'.'.join(map(str, v))} < {minima}"
            else:
                self.aviso(f"Nivel 2b activo: mergiraf {'.'.join(map(str, v))}")
                return programa
        self.aviso(f"Nivel 2b desactivado: {motivo}. Sigue el nivel 2.")
        return None

    def sondear(self):
        """True si cambió la lista de conflictos."""
        if not self.activo:
            return False
        ejecutar(self.repo, "fetch", "--quiet", "--prune", "--no-write-fetch-head", "origin",
                 "+refs/hackathon/wip/*:refs/hackathon/relay-wip/*", timeout=60)
        c, out, _ = ejecutar(self.repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/hackathon/relay-wip/")
        refs = {}
        for linea in out.splitlines() if c == 0 else []:
            nombre, _, sha = linea.partition(" ")
            persona = nombre.rsplit("/", 1)[-1].lower()
            if persona in self.equipo and re.fullmatch(r"[0-9a-f]{40}", sha):
                refs[persona] = sha
        nuevos = []
        personas = sorted(refs)
        self._inicio_2b = None                    # el plazo del ciclo empieza con la primera llamada a Mergiraf
        for i, a in enumerate(personas):
            for b in personas[i + 1:]:
                clave = (refs[a], refs[b])
                if clave not in self._cache:
                    self._cache[clave] = self._merge_tree(refs[a], refs[b]) if self.mergiraf is None \
                        else self._etapas(refs[a], refs[b])
                if self.mergiraf is not None:
                    conflicto = self._con_2b(a, b, self._cache[clave])
                    if conflicto:
                        nuevos.append(conflicto)
                    continue
                rutas = self._cache[clave]
                if rutas:
                    previo = self._desde.get((a, b))
                    desde = previo[1] if previo and previo[0] == rutas else self.ahora()
                    self._desde[(a, b)] = (rutas, desde)
                    nuevos.append({"personas": [a, b], "rutas": rutas, "desde": desde})
                else:
                    self._desde.pop((a, b), None)
        if len(self._cache) > 500:
            self._cache = {k: v for k, v in list(self._cache.items())[-100:]}
        if len(self._cache_2b) > 500:                # LRU: _resuelve pone al final lo que consulta (#88)
            self._cache_2b = {k: v for k, v in list(self._cache_2b.items())[-100:]}
        cambio = nuevos != self.conflictos
        self.conflictos = nuevos
        return cambio

    def _merge_tree(self, a, b):
        """Ficheros en conflicto al fusionar a y b (sobre su base común); [] si no hay conflicto o si git falla."""
        c, out, _ = ejecutar(self.repo, "merge-tree", "--write-tree", "--name-only", "--no-messages", a, b)
        if c != 1:
            return []
        rutas = []
        for linea in out.splitlines()[1:]:
            if not linea.strip():
                break
            if linea not in rutas:
                rutas.append(linea)
        return sorted(rutas, key=str.lower)

    def _etapas(self, a, b):
        """Como _merge_tree, sin `--name-only`: {ruta: {etapa: (modo, blob)}} de los ficheros en conflicto."""
        c, out, _ = ejecutar(self.repo, "merge-tree", "--write-tree", "--no-messages", a, b)
        if c != 1:
            return {}
        etapas = {}
        for linea in out.splitlines()[1:]:
            if not linea.strip():
                break
            meta, _, ruta = linea.partition("\t")
            partes = meta.split(" ")
            if len(partes) == 3 and ruta:
                etapas.setdefault(ruta, {})[partes[2]] = (partes[0], partes[1])
        return dict(sorted(etapas.items(), key=lambda x: x[0].lower()))

    def _con_2b(self, a, b, etapas):
        """El conflicto del par con el nivel 2b: las rutas que Mergiraf resuelve (rc 0) van a `rutas_2b`."""
        if not etapas:
            self._desde.pop((a, b), None)
            self._desde_2b.pop((a, b), None)
            return None
        rutas, rutas_2b = [], []
        for ruta, e in etapas.items():
            (rutas_2b if self._resuelve(ruta, e) else rutas).append(ruta)
        desdes = []
        for lista, memoria in ((rutas, self._desde), (rutas_2b, self._desde_2b)):
            previo = memoria.get((a, b))
            if not lista:
                memoria.pop((a, b), None)
                desdes.append(None)
                continue
            desde = previo[1] if previo and previo[0] == lista else self.ahora()
            memoria[(a, b)] = (lista, desde)
            desdes.append(desde)
        return {"personas": [a, b], "rutas": rutas, "rutas_2b": rutas_2b, "desde": desdes[0], "desde_2b": desdes[1]}

    def _resuelve(self, ruta, etapas):
        """¿Resuelve Mergiraf esta ruta sin conflictos? Solo con las tres etapas en modo normal; si no, ni se intenta.
        Caché por (blobs, ruta), también para el «no». Lo que no cabe en el plazo del ciclo sigue rojo y no se guarda."""
        if set(etapas) != {"1", "2", "3"} or any(etapas[n][0] not in MODOS_2B for n in "123"):
            return False
        clave = (etapas["1"][1], etapas["2"][1], etapas["3"][1], ruta)
        if clave in self._cache_2b:
            self._cache_2b[clave] = self._cache_2b.pop(clave)      # la usada, al final: el recorte la conserva
            return self._cache_2b[clave]
        if self._inicio_2b is None:
            self._inicio_2b = self.reloj()
        queda = self.PLAZO_CICLO_S - (self.reloj() - self._inicio_2b)
        if queda <= 0:
            return False                          # se intenta en el ciclo siguiente
        plazo = min(self.PLAZO_PROCESO_S, queda)
        resultado = self._mergiraf(ruta, [etapas[n][1] for n in "123"], plazo)
        if resultado is None or (resultado == "plazo" and plazo < self.PLAZO_PROCESO_S):
            return False                          # no se pudo lanzar, o lo cortó el plazo del ciclo: no se guarda
        self._cache_2b[clave] = resultado is True
        return resultado is True

    def _mergiraf(self, ruta, blobs, plazo):
        """True (rc 0), False (otro rc), «plazo» (lo mata el relay) o None (no se pudo crear el temporal, lanzarlo o leer
        un blob; o el relay está parando). Los blobs van a un directorio temporal fuera del clon, con XDG_DATA_HOME y
        APPDATA allí (las copias de Mergiraf, P12 y P17), que se borra siempre. Mergiraf corre con ese directorio de cwd
        y con `--allow-parse-errors=false`: así ningún atributo de git (`.gitattributes`, `.git/info/attributes`,
        `core.attributesFile`) cambia el resultado (#88). La salida no se lee."""
        with self._lock_vivos:
            if self._cerrado:
                return None
            try:
                tmp = tempfile.mkdtemp(prefix="hk-2b-")
            except OSError:
                return None                       # sin temporal, rojo y sin caché; el ciclo sigue (constitución VIII)
            self._temporales.add(tmp)
        try:
            nombres = []
            for n, blob in zip("123", blobs):
                nombre = os.path.join(tmp, n)
                if not self._blob(blob, nombre):
                    return None
                nombres.append(nombre)
            env = dict(os.environ, XDG_DATA_HOME=tmp, APPDATA=tmp)
            rc = self._proceso([self.mergiraf, "merge", *nombres, f"--path-name={ruta}", "--allow-parse-errors=false",
                                "-t", str(self.PLAZO_FICHERO_MS), "-o", os.path.join(tmp, "salida")], plazo,
                               stdout=subprocess.DEVNULL, cwd=tmp, env=env)
            return rc if rc in (None, "plazo") else rc == 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
            with self._lock_vivos:
                self._temporales.discard(tmp)

    def _blob(self, blob, destino):
        """`git cat-file blob` a un fichero, en bytes."""
        env = dict(os.environ, **ENTORNO)
        try:
            with open(destino, "wb") as f:
                rc = self._proceso(["git", *SIN_CREDENCIALES, "-C", self.repo, "cat-file", "blob", blob], 60, stdout=f,
                                   env=env)
        except OSError:
            return False
        return rc == 0

    def _proceso(self, args, plazo, **kw):
        """Un hijo del nivel 2b, apuntado mientras vive para que `cerrar` lo mate: su rc, «plazo» (lo mata) o None (no
        se pudo lanzar, o el relay está parando)."""
        with self._lock_vivos:
            if self._cerrado:
                return None
            try:
                p = subprocess.Popen(args, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
            except (OSError, ValueError, subprocess.SubprocessError):
                return None
            self._vivos.add(p)
        try:
            rc = p.wait(timeout=plazo)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()
            rc = "plazo"
        finally:
            with self._lock_vivos:
                self._vivos.discard(p)
        return None if self._cerrado else rc

    def cerrar(self):
        """Al parar el relay (#88): mata los hijos del nivel 2b que sigan vivos y borra sus temporales (ADR-0014: «se
        borra después, pase lo que pase»). Después no se lanza ninguno más."""
        with self._lock_vivos:
            self._cerrado = True
            vivos, temporales = list(self._vivos), list(self._temporales)
        for p in vivos:
            try:
                p.kill()
            except OSError:
                pass
        for p in vivos:
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                pass
        for tmp in temporales:
            shutil.rmtree(tmp, ignore_errors=True)
