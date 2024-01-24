
from H5Gizmos import Html, do, serve, wait_for, get, unname, js_await
import json

async def task():
    G = Html("<h1>", "JSON downloaded asynchronously")
    G.serve_folder("local", ".")
    await G.browse()
    log = G.window.console.log
    f = await wait_for(G.window.fetch("local/example.json"))
    do(log("fetched", f))
    data = await js_await(f.json(), to_depth=5)
    fmt = json.dumps(data, indent=4)
    pre = Html('<pre>\n%s\n</pre>' % fmt)
    G.add(pre)
    # clean up reference
    unname(f)

serve(task())

