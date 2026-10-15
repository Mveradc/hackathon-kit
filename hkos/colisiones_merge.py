"""Nivel 2 de colisiones (M8g, R-20, ADR-0007): conflictos reales entre el trabajo en curso de dos personas.

Dos piezas, solo biblioteca estándar y git:
  - Publicador (en el demonio de cada persona, con `publicar_wip: sí` en os.md): cada 60 s, un commit del árbol de la
    copia principal hecho con un índice temporal, sin tocar el índice, el árbol, HEAD ni el `git status` de la persona,
    y un push forzado **solo** a refs/hackathon/wip/<persona>, solo si cambió el árbol.
  - Calculo (en el relay): `git fetch` de refs/hackathon/wip/* a refs/hackathon/relay-wip/* de su clon y
    `git merge-tree --write-tree` por pares de personas (Git ≥ 2.38).

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
import subprocess
import time
from datetime import datetime, timezone

ENTORNO = {"GIT_OPTIONAL_LOCKS": "0", "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never",
           "GIT_SSH_COMMAND": "ssh -o BatchMode=yes", "LC_ALL": "C"}
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


class Calculo:
    """El nivel 2 en el relay: trae las refs WIP y calcula los conflictos por pares. `conflictos` =
    [{personas, rutas, desde}], lo que recibe modelo.calcular."""
    CADA_S = 30

    def __init__(self, repo, equipo, aviso=print, ahora=ahora_iso, version=None):
        self.repo, self.equipo, self.aviso, self.ahora = repo, set(equipo), aviso, ahora
        v = version if version is not None else version_git(repo)
        self.activo = v is not None and v >= VERSION_MIN
        if not self.activo:
            texto = f"{v[0]}.{v[1]}" if v else "desconocida"
            aviso(f"Nivel 2 desactivado: git {texto} < 2.38 (merge-tree --write-tree). Siguen los niveles 1 y 3.")
        self.conflictos, self._cache, self._desde = [], {}, {}

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
        for i, a in enumerate(personas):
            for b in personas[i + 1:]:
                clave = (refs[a], refs[b])
                if clave not in self._cache:
                    self._cache[clave] = self._merge_tree(refs[a], refs[b])
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
