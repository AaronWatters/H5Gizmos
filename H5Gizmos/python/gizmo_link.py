"""
This module implements a Jupyter server proxy server for connecting
machine-internal gizmo processes to the outside world using a Jupyter server
and its infrastructure as a connector.

This server is plugged in to a Jupyter server using the well known name `GizmoLink`.

# Notebook gizmo connection use case

When a gizmo G starts in a notebook using "proxy=True" for a given PORT
the gizmo looks for a single server data record

```
[x] = notebook.notebookapp.list_running_servers()
BASEURL = x["base_url"]
```

The look up fails or falls back if there is more than one server found.
Otherwise the gizmo G advertises a starting_href of form:

```
/BASEURL/GizmoLink/connect/PORT/some_path
```

And the gizmo waits on the PORT for incoming local HTTP requests

The browser running using the Jupyter context (and authentication, etc)
expands the href to the URL

```
https://external_notebook_address:/BASEURL/GizmoLink/connect/PORT/some_path
```

The Jupyter server connects this request to the GizmoLink server.  The
GizmoLink server connects the request in turn to the internal URL

http://localhost:PORT/some_path

The above path is received and handled by the listening gizmo G.

# Other process connection use case via user cut/paste

When a process starts a Gizmo using the link method it prints an output line
of form:
```
GizmoLink: /PORT/SOME_PATH
```
The user cuts and pastes the line into a form in the GizmoLink server at location

```
https://external_notebook_address:/BASEURL/GizmoLink/start
```

The form submit triggers

```
https://external_notebook_address:/BASEURL/GizmoLink/redirect?Line=/PORT/SOME_PATH
```

Which redirects to

```
https://external_notebook_address:/BASEURL/GizmoLink/connect/PORT/some_path
```

which is handled as described above.

# Demo connection use case

When the GizmoLink server receives a request of form:

```
https://external_notebook_address:/BASEURL/GizmoLink/demo?name=DEMONAME
```

The GizmoLink server looks up a gizmo implementation script associated with the DEMONAME
and executes the script in a subprocess.  The GizmoLink server monitors
the script STDOUT for the line

```
GizmoLink: /PORT/SOME_PATH
```

When the line is detected the GizmoLink server issues a redirect to
```
https://external_notebook_address:/BASEURL/GizmoLink/connect/PORT/some_path
```
which is handled as described above.

The gizmo script subprocess runs to termination via an asynchronous subtask in the 
GizmoLink server.
"""

from pickle import PROTO
from aiohttp import web
import aiohttp
from matplotlib.pyplot import text
from .H5Gizmos import schedule_task
import os

static_folder =  os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '../static')
)

START_PAGE_HTML = """

<!DOCTYPE html>
<html>
<head>
<style>

.gizmobody {
    font-family:Verdana, Arial, Helvetica, sans-serif;
    }

</style>
</head>

SVG_ICON

<h2> Gizmo link starter </h2>

<body id="GIZMO_BODY" class="gizmobody">

    <form action="FORM_ACTION"/>
        <p><label for="convert_text">Attach to gizmo text:</label></p>
        <textarea id="convert_text" name="convert_text" rows="4" cols="50">CONVERT_TEXT</textarea>
        <br/>
        <input type="submit" value="Attach to gizmo"/>
    </form>

</body>
</html>
"""

icon_path = os.path.join(static_folder, "logo.svg")

def setup_gizmo_link():
    assert os.path.isfile(icon_path)
    return {
        'command': ['gizmo_link', '{port}', '{base_url}', "GizmoLink"],
        'environment': {},
        'launcher_entry': {
            'title': 'Gizmo Link',
            'icon_path': icon_path,
        }
    }


def start_script():
    import sys
    port = int(sys.argv[1])
    base_url = sys.argv[2]
    prefix = sys.argv[3]
    server = GizmoLink(port, base_url, prefix)
    app = server.get_app()
    return web.run_app(app, port=port)


PROTOCOLS = ("http", "ws")

class GizmoLink:

    def __init__(self, port, base_url, prefix, verbose=True):
        self.port = port
        self.base_url = base_url
        self.prefix = prefix
        self.verbose = verbose
        if self.verbose:
            print("GizmoLink created.")

    def get_app(self):
        app = web.Application()
        app.router.add_route('GET', '/', self.start)
        app.router.add_route('GET', '/start', self.start)
        app.router.add_route('GET', '/redirect', self.redirect)
        app.router.add_route('GET', '/connect/{tail:.*}', self.connect_get)
        app.router.add_route('POST', '/connect/{tail:.*}', self.connect_post)
        app.router.add_route('GET', '/demo', self.demo)
        app.router.add_route('GET', '/test', self.test)
        if self.verbose:
            print("GizmoLink app created.")
        return app

    async def start(self, request):
        "Top level entry page.  Show gizmo starter form."
        self.verbose_check("start", request)
        txt = START_PAGE_HTML
        svg = open(icon_path).read()
        txt = txt.replace("SVG_ICON", svg)
        action = self.make_url("redirect")
        txt = txt.replace("FORM_ACTION", action)
        return self.respond_bytes(txt)

    async def redirect(self, request):
        "Redirect Line to a connecting page."
        self.verbose_check("redirect", request)
        return await self.test(request)

    async def connect_get(self, request):
        "Connect HTTP GET or web socket to underlying gizmo"
        self.verbose_check("connect_get", request)
        (prefix, port, protocol, target_path) = self.parse_connect_path(request)
        assert prefix == "connect", "bad prefix: " + repr(prefix)
        target_url = "http://localhost:%s/%s" % (port, target_path)
        if self.verbose:
            print("forwarding GET to target", repr(target_url))
        if protocol == "http":
            # get request
            # xxxx kiss for now.
            async with aiohttp.ClientSession() as session:
                async with session.get(target_url) as resp:
                    status = resp.status
                    content_type = resp.content_type
                    # xxxx should probably stream this?
                    bytes = await resp.read()
                    # forward....
                    # xxxx should use streaming?
                    return self.respond_bytes(bytes, content_type, status)
        else:
            assert protocol == "ws", (
                "For GET protocol must be ws or http: " + repr(protocol))
            # ws connection
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            if self.verbose:
                print("ws attached.")
            connector = WebSocketConnector(ws, port, target_path, self.verbose)
            await connector.get_server_ws()
            connector.start_listener_tasks()
            await connector.server_listener_task

    async def connect_post(self, request):
        "Connect HTTP POST to underlying gizmo"
        self.verbose_check("connect_post", request)
        (prefix, port, protocol, target_path) = self.parse_connect_path(request)
        assert prefix == "connect", "bad prefix: " + repr(prefix)
        target_url = "http://localhost:%s/%s" % (port, target_path)
        if self.verbose:
            print("forwarding POST to target", repr(target_url))
        if protocol == "http":
            # post request
            # xxxx kiss for now.
            post_bytes = await request.read()
            async with aiohttp.ClientSession() as session:
                # xxxx should stream post data (?)
                async with session.post(target_url, data=post_bytes) as resp:
                    status = resp.status
                    content_type = resp.content_type
                    # xxxx should probably stream this?
                    bytes = await resp.read()
                    # forward....
                    # xxxx should use streaming?
                    return self.respond_bytes(bytes, content_type, status)
        else:
            assert protocol == "http", "POST expects 'http' protocol marker: " + repr(protocol)
        #return await self.test(request)

    def parse_connect_path(self, request):
        try:
            # use the path with query string to pass on parameters...
            path = request.path_qs
            spath = path.split("/")
            assert spath[0] == "", "path should start with slash: " + repr(path)
            prefix = spath[1]
            port = int(spath[2])
            marker = spath[3]
            assert marker == "gizmo", "path marker should be 'gizmo': " + repr(path)
            protocol = spath[4]
            assert protocol in PROTOCOLS, "Bad protocol indicator: " + repr((path, PROTOCOLS))
            target_path = "/".join(spath[3:])
            return (prefix, port, protocol, target_path)
        except Exception as e:
            print("path parse failed:", e)
            raise

    async def demo(self, request):
        "Start a registered demo gizmo and redirect to its start URL."
        self.verbose_check("demo", request)
        return await self.test(request)

    async def test(self, request):
        "Server test page."
        self.verbose_check("test", request)
        path = request.path
        txt = """
        <h1>Hello world</h1>

        <p> Port is %s </p>
        <p> base_url is %s </p>
        <p> path is %s </p>
        """ % (self.port, self.base_url, path)
        return self.respond_bytes(txt)

    def respond_bytes(self, txt, content_type="text/html", status=200):
        if type(txt) is bytes:
            b_body = txt
        else:
            b_body = txt.encode("utf-8")
        self.http_response = web.Response(
            body=b_body, content_type=content_type, status=status)
        return self.http_response

    def verbose_check(self, info, request):
        if self.verbose:
            print("GizmoLink:", info, request.path)

    def make_url(self, *path_components):
        path_components = [self.prefix] + list(path_components)
        return self.base_url + ("/".join(path_components))


class WebSocketConnector:

    def __init__(self, ws, server_port, server_path, verbose=False):
        self.from_client_ws = ws
        self.from_server_ws = None
        self.session = None
        self.server_port = server_port
        self.server_path = server_path
        self.verbose = verbose

    async def get_server_ws(self):
        session = self.session = aiohttp.ClientSession()
        server_url = "http://localhost:%s/%s" % (self.server_port, self.server_path)
        if self.verbose:
            print ("Connecting session to server URL", server_url)
        self.from_server_ws = await session.ws_connect(server_url)

    def start_listener_tasks(self):
        self.server_listener_task = schedule_task(self.listen_to_server())
        self.client_listener_task = schedule_task(self.listen_to_client())

    async def listen_to_server(self, from_ws=None, to_ws=None):
        if from_ws is None:
            from_ws = self.from_server_ws
            to_ws = self.from_client_ws
        async for msg in from_ws:
            typ = msg.type
            if typ == aiohttp.WSMsgType.text:
                # pass the message on the the client
                txt = msg.data
                #print ("got", repr(txt), "from websocket", from_ws)
                await to_ws.send_str(txt)
            else:
                #print("unexpected message type", typ)
                break
        if self.verbose:
            print("Server listener stopping.")
        schedule_task(self.terminate_listeners())

    async def listen_to_client(self):
        return await self.listen_to_server(self.from_client_ws, self.from_server_ws)
    
    async def terminate_listeners(self):
        if self.verbose:
            print("terminating listeners.")
        for ws in [self.from_client_ws, self.from_server_ws]:
            try:
                await ws.close()
            except Exception:
                pass
        try:
            if self.verbose:
                print("closing session", self.session)
            await self.session.close()
        except Exception:
            pass
        for task in [self.server_listener_task, self.client_listener_task]:
            if not task.done():
                print("cancelling task", task)
                task.cancel()


if __name__ == "__main__":
    start_script()