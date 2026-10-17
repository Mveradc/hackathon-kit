"""Ficheros privados del OS (issue #15, hallazgo 12): token, relay.url, web.token y web.html. Solo biblioteca estándar
(ADR-0005).

En Linux y macOS, 0600 desde que existen: O_EXCL en un temporal y os.replace, sin la ventana de umask de open(…, "w")
ni el modo de un fichero anterior. En Windows el modo no cuenta: el fichero hereda el ACL de su carpeta y, con el repo
fuera del perfil (C:\\dev\\…, D:\\…), «Usuarios autentificados» lo lee y lo modifica. Allí el temporal nace (CreateFileW
con su descriptor, no después) con un DACL protegido, sin herencia, y una sola entrada: control total para el usuario
del proceso, por su SID (no por su nombre: no depende del idioma del sistema). os.replace conserva ese DACL, así que un
fichero de antes con el ACL heredado queda corregido al reescribirse.
"""
import os

WINDOWS = os.name == "nt"


def escribe_privado(ruta, texto, tmp=None):
    """Escribe `texto` en `ruta`, atómico y solo para el usuario actual. `tmp`: el temporal (por defecto ruta.tmp)."""
    tmp = tmp or ruta + ".tmp"
    try:
        os.remove(tmp)
    except OSError:
        pass
    fd = _crea_windows(tmp) if WINDOWS else os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
        f.write(texto)
    os.replace(tmp, ruta)


def es_privado(ruta):
    """True si solo el usuario actual puede leer y escribir `ruta` (en POSIX, suyo y sin bits de grupo ni de otros; en
    Windows, DACL protegido con solo entradas que permiten al SID del proceso)."""
    if not WINDOWS:
        st = os.stat(ruta)
        return st.st_uid == os.getuid() and not st.st_mode & 0o077
    protegido, entradas = acl(ruta)
    return protegido and bool(entradas) and all(t == 0 and sid == sid_propio() for t, _, _, sid in entradas)


if WINDOWS:
    import ctypes
    import msvcrt
    from ctypes import wintypes

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _a32 = ctypes.WinDLL("advapi32", use_last_error=True)
    _P = ctypes.c_void_p

    def _f(dll, nombre, res, *args):
        fn = getattr(dll, nombre)
        fn.restype, fn.argtypes = res, args
        return fn

    _GetCurrentProcess = _f(_k32, "GetCurrentProcess", wintypes.HANDLE)
    _CloseHandle = _f(_k32, "CloseHandle", wintypes.BOOL, wintypes.HANDLE)
    _LocalFree = _f(_k32, "LocalFree", _P, _P)
    _CreateFileW = _f(_k32, "CreateFileW", wintypes.HANDLE, wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, _P,
                      wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    _OpenProcessToken = _f(_a32, "OpenProcessToken", wintypes.BOOL, wintypes.HANDLE, wintypes.DWORD,
                           ctypes.POINTER(wintypes.HANDLE))
    _GetTokenInformation = _f(_a32, "GetTokenInformation", wintypes.BOOL, wintypes.HANDLE, ctypes.c_int, _P,
                              wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
    _ConvertSidToStringSidW = _f(_a32, "ConvertSidToStringSidW", wintypes.BOOL, _P, ctypes.POINTER(wintypes.LPWSTR))
    _ConvertSddl = _f(_a32, "ConvertStringSecurityDescriptorToSecurityDescriptorW", wintypes.BOOL, wintypes.LPCWSTR,
                      wintypes.DWORD, ctypes.POINTER(_P), ctypes.POINTER(wintypes.ULONG))
    _GetNamedSecurityInfoW = _f(_a32, "GetNamedSecurityInfoW", wintypes.DWORD, wintypes.LPCWSTR, ctypes.c_int,
                                wintypes.DWORD, _P, _P, ctypes.POINTER(_P), _P, ctypes.POINTER(_P))
    _GetSecurityDescriptorControl = _f(_a32, "GetSecurityDescriptorControl", wintypes.BOOL, _P,
                                       ctypes.POINTER(wintypes.WORD), ctypes.POINTER(wintypes.DWORD))
    _GetAclInformation = _f(_a32, "GetAclInformation", wintypes.BOOL, _P, _P, wintypes.DWORD, ctypes.c_int)
    _GetAce = _f(_a32, "GetAce", wintypes.BOOL, _P, wintypes.DWORD, ctypes.POINTER(_P))

    class _Atributos(ctypes.Structure):
        _fields_ = [("nLength", wintypes.DWORD), ("lpSecurityDescriptor", _P), ("bInheritHandle", wintypes.BOOL)]

    class _TamanoAcl(ctypes.Structure):
        _fields_ = [("AceCount", wintypes.DWORD), ("AclBytesInUse", wintypes.DWORD), ("AclBytesFree", wintypes.DWORD)]

    class _Ace(ctypes.Structure):           # ACE_HEADER + Mask; el SID empieza justo detrás (ACCESS_ALLOWED_ACE)
        _fields_ = [("AceType", ctypes.c_ubyte), ("AceFlags", ctypes.c_ubyte), ("AceSize", wintypes.WORD),
                    ("Mask", wintypes.DWORD)]

    TOKEN_QUERY, TOKEN_USER = 0x0008, 1
    GENERIC_WRITE, CREATE_NEW, FILE_ATTRIBUTE_NORMAL = 0x40000000, 1, 0x80
    SE_FILE_OBJECT, DACL_SECURITY_INFORMATION, SE_DACL_PROTECTED = 1, 0x4, 0x1000
    INVALIDO = wintypes.HANDLE(-1).value
    _sid = None

    def _error():
        return ctypes.WinError(ctypes.get_last_error())

    def _cadena_sid(psid):
        s = wintypes.LPWSTR()
        if not _ConvertSidToStringSidW(psid, ctypes.byref(s)):
            raise _error()
        try:
            return s.value
        finally:
            _LocalFree(ctypes.cast(s, _P))

    def sid_propio():
        """El SID del usuario del proceso, en texto (S-1-5-21-…)."""
        global _sid
        if _sid is None:
            h = wintypes.HANDLE()
            if not _OpenProcessToken(_GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(h)):
                raise _error()
            try:
                n = wintypes.DWORD()
                _GetTokenInformation(h, TOKEN_USER, None, 0, ctypes.byref(n))
                buf = ctypes.create_string_buffer(n.value)
                if not _GetTokenInformation(h, TOKEN_USER, buf, n, ctypes.byref(n)):
                    raise _error()
                _sid = _cadena_sid(ctypes.cast(buf, ctypes.POINTER(_P))[0])    # TOKEN_USER.User.Sid
            finally:
                _CloseHandle(h)
        return _sid

    def descriptor(sddl):
        """Un descriptor de seguridad desde SDDL; se libera con LocalFree."""
        sd = _P()
        if not _ConvertSddl(sddl, 1, ctypes.byref(sd), None):
            raise _error()
        return sd

    def _crea_windows(ruta):
        """Un fichero nuevo (como O_EXCL) que nace con «D:P(A;;FA;;;<SID>)»: sin herencia, solo el usuario."""
        sd = descriptor(f"D:P(A;;FA;;;{sid_propio()})")
        try:
            atr = _Atributos(ctypes.sizeof(_Atributos), sd, False)
            h = _CreateFileW(ruta, GENERIC_WRITE, 0, ctypes.byref(atr), CREATE_NEW, FILE_ATTRIBUTE_NORMAL, None)
            if h in (None, INVALIDO):
                raise _error()
        finally:
            _LocalFree(sd)
        try:
            return msvcrt.open_osfhandle(h, os.O_WRONLY)
        except OSError:
            _CloseHandle(h)
            raise

    def acl(ruta):
        """(protegido, [(tipo, banderas, máscara, SID)]) del DACL de `ruta`. Tipo 0 = permitir, 1 = denegar; en
        banderas, 0x10 = heredada. Sin DACL (todo el mundo, control total): (False, [])."""
        dacl, sd = _P(), _P()
        err = _GetNamedSecurityInfoW(ruta, SE_FILE_OBJECT, DACL_SECURITY_INFORMATION, None, None, ctypes.byref(dacl),
                                     None, ctypes.byref(sd))
        if err:
            raise ctypes.WinError(err)
        try:
            control, revision = wintypes.WORD(), wintypes.DWORD()
            if not _GetSecurityDescriptorControl(sd, ctypes.byref(control), ctypes.byref(revision)):
                raise _error()
            if not dacl.value:
                return False, []
            tam = _TamanoAcl()
            if not _GetAclInformation(dacl, ctypes.byref(tam), ctypes.sizeof(tam), 2):    # AclSizeInformation
                raise _error()
            entradas = []
            for i in range(tam.AceCount):
                p = _P()
                if not _GetAce(dacl, i, ctypes.byref(p)):
                    raise _error()
                ace = _Ace.from_address(p.value)
                sid = _cadena_sid(p.value + ctypes.sizeof(_Ace)) if ace.AceType in (0, 1) else None
                entradas.append((ace.AceType, ace.AceFlags, ace.Mask, sid))
            return bool(control.value & SE_DACL_PROTECTED), entradas
        finally:
            _LocalFree(sd)
