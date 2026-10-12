"""Coste por agente de una sesión del orquestador (M7): sesión principal y cada subagente (worker, revisor…).

Lee el transcript de la sesión y los de `subagents/`, suma el uso de cada respuesta una sola vez (por id)
y lo pasa a USD con los precios de abajo (USD por millón de tokens; comprobados en
platform.claude.com/docs/en/about-claude/pricing el 2026-10-12: actualízalos si cambian).

Uso: python evals/coordinacion/coste.py <sesión.jsonl>
"""
import glob
import json
import os
import sys

# entrada, escritura de caché 5 min, escritura de caché 1 h, lectura de caché, salida
PRECIOS = {
    "opus-5-5": (4, 5, 8, 0.20, 20),
    "sonnet-5-5": (2, 2.5, 4, 0.10, 10),
    "haiku-5-5": (0.10, 0.125, 0.20, 0.01, 0.50),  # prompts de hasta 100 k tokens
}


def precio(modelo):
    return next((p for clave, p in PRECIOS.items() if clave in (modelo or "")), None)


def coste(ruta):
    # Una respuesta puede ocupar varias líneas (una por bloque) con el mismo id: vale la última.
    uso, modelo, inicio, fin = {}, {}, None, None
    for linea in open(ruta, encoding="utf-8"):
        if not linea.strip():
            continue
        e = json.loads(linea)
        t = e.get("timestamp")
        if t:
            inicio, fin = inicio or t, t
        m = e.get("message") or {}
        if e.get("type") == "assistant" and m.get("usage"):
            uso[m.get("id")] = m["usage"]
            modelo[m.get("id")] = m.get("model")
    total, tokens, contexto = 0.0, [0, 0, 0, 0, 0], 0
    for i, u in uso.items():
        cc = u.get("cache_creation") or {}
        c1h = cc.get("ephemeral_1h_input_tokens", 0)
        c5m = cc.get("ephemeral_5m_input_tokens", u.get("cache_creation_input_tokens", 0) - c1h)
        fila = [u.get("input_tokens", 0), c5m, c1h, u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0)]
        tokens = [a + b for a, b in zip(tokens, fila)]
        contexto = fila[0] + fila[1] + fila[2] + fila[3]
        p = precio(modelo[i])
        if p:
            total += sum(n * q for n, q in zip(fila, p)) / 1e6
    return total, tokens, set(modelo.values()), contexto, inicio, fin


def main(sesion):
    filas = [("sesión principal", sesion)]
    for t in sorted(glob.glob(os.path.join(sesion[:-len(".jsonl")], "subagents", "agent-*.jsonl"))):
        meta = t[:-len(".jsonl")] + ".meta.json"
        datos = json.load(open(meta, encoding="utf-8")) if os.path.exists(meta) else {}
        filas.append((f"{datos.get('agentType', '?')} · {datos.get('description', '')}", t))
    suma = 0.0
    print(f"{'agente':55} {'modelo':18} {'USD':>7} {'contexto final':>15} {'entrada/caché 5m/caché 1h/lectura/salida'}")
    for nombre, ruta in filas:
        usd, tok, modelos, ctx, ini, fin = coste(ruta)
        suma += usd
        print(f"{nombre[:55]:55} {','.join(sorted(x or '?' for x in modelos))[:18]:18} {usd:7.3f} {ctx:15,} {'/'.join(f'{n:,}' for n in tok)}  ({(ini or '')[11:19]}–{(fin or '')[11:19]})")
    print(f"{'total':55} {'':18} {suma:7.3f}")


if __name__ == "__main__":
    main(sys.argv[1])
