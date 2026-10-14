import sys, json
# Servidor MCP stdio mínimo con una herramienta «eco»
def out(o): sys.stdout.write(json.dumps(o)+"\n"); sys.stdout.flush()
for line in sys.stdin:
    try: m = json.loads(line)
    except Exception: continue
    i, meth = m.get("id"), m.get("method")
    if meth == "initialize":
        out({"jsonrpc":"2.0","id":i,"result":{"protocolVersion":m["params"].get("protocolVersion","2025-06-18"),"capabilities":{"tools":{}},"serverInfo":{"name":"jugmcp","version":"0"}}})
    elif meth == "tools/list":
        out({"jsonrpc":"2.0","id":i,"result":{"tools":[{"name":"eco","description":"Devuelve PONG-M8","inputSchema":{"type":"object","properties":{}}},{"name":"eco2","description":"Devuelve PONG2-M8","inputSchema":{"type":"object","properties":{}}}]}})
    elif meth == "tools/call":
        out({"jsonrpc":"2.0","id":i,"result":{"content":[{"type":"text","text":"PONG2-M8" if m["params"].get("name")=="eco2" else "PONG-M8"}]}})
    elif i is not None:
        out({"jsonrpc":"2.0","id":i,"result":{}})
