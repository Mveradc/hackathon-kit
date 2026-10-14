# /// script
# requires-python = ">=3.10"
# ///
"""Demonio de juguete: el bloqueo es el puerto (si está ocupado, ya hay otro y sale). Se apaga tras --inactivo s."""
import socket, sys, time, os
puerto, inactivo, log = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
s = socket.socket()
try:
    s.bind(("127.0.0.1", puerto)); s.listen()
except OSError:
    open(log, "a").write(f"{time.strftime('%T')} puerto {puerto} ocupado: ya hay demonio, salgo (pid {os.getpid()})\n"); sys.exit(0)
open(log, "a").write(f"{time.strftime('%T')} demonio vivo en {puerto} (pid {os.getpid()})\n")
s.settimeout(2); fin = time.time() + inactivo
while time.time() < fin:
    try:
        c, _ = s.accept(); c.close(); fin = time.time() + inactivo   # cada conexión cuenta como actividad
    except socket.timeout:
        pass
open(log, "a").write(f"{time.strftime('%T')} sin actividad {inactivo} s: me apago\n")
