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

# Other process connection use case via environment variable

When a gizmo server starts in a process it looks for a `GIZMO_LINK_PREFIX`
environment variable.  If `GIZMO_LINK_PREFIX` is set for example to
```
    http://127.0.0.1:60327/GizmoLink/
```
Then the process uses the proxy connection URL
```
    http://127.0.0.1:60327/GizmoLink/connect/PORT/some_path
```
which proxies the internal link
```
    http://localhost:PORT/some_path
```

# Gizmo script use case

User goes to main page

```
https://external_notebook_address:/BASEURL/GizmoLink/
```

Main page presents user with a list of modules with "H5Gizmos.script"
entry points.  User selects one of the modules, with URL (URL_PREFIX added by javascript)

```
https://external_notebook_address:/BASEURL/GizmoLink/select_script/MODULE?prefix=URL_PREFIX
```

where URL_PREFIX is `https://external_notebook_address:/BASEURL/`.
Selection page lists the "H5Gizmos.scripts" entry points for MODULE.
User selects entry point NAME with URL

```
https://external_notebook_address:/BASEURL/GizmoLink/launch_script/MODULE/NAME?prefix=URL_PREFIX
```

launch_script looks for a registered entry point EP with that NAME with group "H5Gizmos.script"
and module_name MODULE.  Launch_script launches

```
gizmo_script MODULE/NAME
```

with env variable

```
GIZMO_LINK_PREFIX = URL_PREFIX (= `https://external_notebook_address:/BASEURL/`)
```

And awaits a stdout line of form 
```
GIZMO_LINK: START_URL
```
where START_URL is a connect URL of form:
```
https://external_notebook_address:/BASEURL/GizmoLink/connect/PORT/some_path
```
Launch_script redirects to START_URL (?or opens?) the start_url and awaits gizmo_script subprocess
completion in a subtask.

"""

from aiohttp import web
import aiohttp
import asyncio
#from .H5Gizmos import schedule_task
from .gz_parent_protocol import schedule_task
from .gizmo_script_support import GIZMO_SCRIPT
import os
import json
from . import gizmo_script_support

# refs
# https://stackoverflow.com/questions/62355732/python-package-discovery-for-entry-points-subgroups
# https://docs.python.org/3/library/asyncio-subprocess.html#asyncio-subprocess
# 

static_folder =  os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '../static')
)

LINK_PREFIX = "GIZMO_LINK:"

JUPYTER_SERVER_PLUGIN_NAME = "GizmoLink"

REDIRECT_AUTOMATICALLY = True

icon_path = os.path.join(static_folder, "logo.svg")
start_html_path = os.path.join(static_folder, "gizmo_link_start.html")

def setup_gizmo_link():
    "Jupyter server plugin setup callback."
    assert os.path.isfile(icon_path)
    return {
        'command': ['gizmo_link', '{port}', '{base_url}', JUPYTER_SERVER_PLUGIN_NAME],
        'environment': {},
        'launcher_entry': {
            'title': 'Gizmo Link',
            'icon_path': icon_path,
        }
    }


def start_script():
    "Start link web server."
    import sys
    argv = ["prog", "port", "/", "GizmoLink"]
    ln = len(sys.argv)
    argv[:ln] = sys.argv
    port = int(argv[1])
    base_url = argv[2]
    prefix = argv[3]
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

    def json_parameters(self, module_name=None, script_name=None, prefix=None, redirect=False):
        result = dict(
            port=self.port,
            base_url=self.base_url,
            prefix=self.prefix,
            launch=False, # default
            redirect=redirect,
        )
        result["module_name"] = module_name
        result["script_name"] = script_name
        result["prefix"] = prefix
        if module_name is None:
            result["modules_and_scripts"] = gizmo_script_support.modules_and_scripts_json()
        elif script_name is None:
            result["module_detail"] = gizmo_script_support.module_detail_json(module_name)
        else:
            result["launch"] = (prefix is not None)
        return result

    def get_app(self):
        app = web.Application()
        app.router.add_route('GET', '/', self.start)
        #app.router.add_route('GET', '/start', self.start)
        #app.router.add_route('GET', '/redirect', self.redirect)
        app.router.add_route('GET', '/connect/{tail:.*}', self.connect_get)
        app.router.add_route('POST', '/connect/{tail:.*}', self.connect_post)
        #app.router.add_route('GET', '/demo', self.demo)
        app.router.add_route('GET', '/test', self.test)
        app.router.add_route('GET', '/icon', self.icon)
        app.router.add_static("/static", static_folder, show_index=True)
        if self.verbose:
            print("GizmoLink app created.")
        return app

    async def icon(self, request):
        bytes = open(icon_path, "rb").read()
        return self.respond_bytes(bytes, content_type="image/svg+xml")

    async def start(self, request):
        "Top level entry page.  Show gizmo starter form."
        self.verbose_check("start", request)
        template = open(start_html_path).read()
        headers = request.headers
        headerlist = []
        for (name, value) in headers.items():
            headerlist.append( "<div>%s :: %s</div>" % (name, value))
        headerstr = "\n".join(headerlist)
        query = request.rel_url.query
        module = query.get("module")
        script = query.get("script")
        prefix = query.get("prefix")
        server = query.get("server")
        port = query.get("port")
        # Try to infer the prefix if possible.
        if prefix is None and server is not None and port is not None:
            prefix = "http://%s:%s/" % (server, port)
        json_parameters = self.json_parameters(
            module_name=module, 
            script_name=script, 
            prefix=prefix,
            redirect=REDIRECT_AUTOMATICALLY,
        )
        #if self.verbose:
        #    print("Start parameters:", json_parameters)
        if json_parameters["launch"]:
            watcher = ScriptWatcher(module, script, prefix)
            try:
                link_url = await watcher.start_script_and_get_start_url()
            except Exception as e:
                json_parameters["launch_exception"] = repr(e)
            else:
                json_parameters["link_url"] = link_url
        json_parameter_str = json.dumps(json_parameters, indent=4)
        formatted = template.format(
            JSON_PARAMETERS=json_parameter_str,
            HEADERS=headerstr
        )
        return self.respond_bytes(formatted)

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
            print("forwarding POST to target", repr(protocol), repr(target_url))
        if protocol == "http":
            # Streaming uploads
            # https://docs.aiohttp.org/en/stable/client_quickstart.html
            content = request.content
            async def content_sender():
                chunk = await content.readany()
                while chunk:
                    yield chunk
                    chunk = await content.readany()
            async with aiohttp.ClientSession() as session:
                # stream post data
                async with session.post(target_url, data=content_sender()) as resp:
                    status = resp.status
                    content_type = resp.content_type
                    # xxxx should probably stream this?
                    bytes = await resp.read()
                    #print("    got post response", len(bytes), status, content_type)
                    #if len(bytes) < 1000:
                    #    print (repr(bytes))
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
            # permit ping requests, for connection testing
            marker0 = marker.split("?")[0]
            acceptible_markers = ("gizmo", "ping")
            assert marker0 in acceptible_markers, "path marker %s should be in %s: %s" % (
                marker0, acceptible_markers, repr(path))
            if marker0 == "ping":
                protocol = "http"
                target_path = marker
            else:
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

class LinkNotFound(ValueError):

    "The link line was not found in the subprocess."

class ScriptWatcher:

    """
    Manage a gizmo script as a subprocess.
    Identify the "GIZMO_LINK:" start URL when the script is ready
    to handle the start page access.
    """

    def __init__(
        self, 
        module_name, 
        script_name,
        server_prefix,
        starter=GIZMO_SCRIPT,
        look_for=b"GIZMO_LINK:",
        capture=True,
        link_timeout=10,
        verbose=True,
        ):
        #from .H5Gizmos import make_future
        from .gz_parent_protocol import make_future
        self.module_name = module_name
        self.script_name = script_name
        self.server_prefix = server_prefix
        self.starter = starter
        self.look_for = look_for
        self.link_timeout = link_timeout
        self.capture = capture
        self.verbose = verbose
        self.captured_stdout = []
        self.captured_stderr = []
        self.link_future = make_future(link_timeout, on_timeout=self.on_timeout)
        self.process = None
        self.command = "%s %s/%s" % (self.starter, self.module_name, self.script_name)

    async def start_script_and_get_start_url(self, delay=0.1):
        """
        Start the script and await/return the start url after a short delay to make sure the script is ready.
        """
        #from .H5Gizmos import schedule_task
        schedule_task(self.run_script())
        url = await self.link_future
        if delay is not None:
            await asyncio.sleep(delay)
        # return url encoded as string (not bytes)
        return url.decode("utf-8") 

    def html(self):
        from cgi import escape
        L = ["<pre>\n"]
        def add(t):
            r = repr(t)
            e = escape(r) + "\n"
            L.append(e)
        L.append("    Standard input captured:\n")
        for x in self.captured_stdout:
            add(x)
        L.append("\n    Standard error captured:\n")
        for x in self.captured_stderr:
            add(x)
        L.append("\n</pre>\n")
        return "".join(L)

    async def run_script(self):
        #from .H5Gizmos import schedule_task
        from .gizmo_server import PREFIX_ENV_VAR
        env = os.environ.copy()
        env[PREFIX_ENV_VAR] = self.server_prefix
        verbose = self.verbose
        if self.verbose:
            print("starting command", repr(self.command))
            print("prefix is", repr(env[PREFIX_ENV_VAR]))
        self.process = await asyncio.create_subprocess_shell(
            self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        # read stderr in other task
        schedule_task(self.readall(self.process.stderr, self.captured_stderr))
        # look for pattern in stdout line
        found = False
        while not found:
            line = await self.process.stdout.readline()
            if len(line) < 1:
                break
            if verbose:
                print("got line", repr(line))
            if self.capture:
                self.captured_stdout.append(line)
            sline = line.strip()
            if sline.startswith(self.look_for):
                if verbose:
                    print("Found pattern:", repr(sline))
                remainder = sline[len(self.look_for):]
                remainder = remainder.strip()
                print("Setting value", remainder)
                self.link_future.set_result(remainder)
                found = True
            else:
                if verbose:
                    print(" & pattern not found in line", repr(sline))
        # read the rest of stdout
        await self.readall(self.process.stdout, self.captured_stdout)
        if not self.link_future.done():
            self.link_future.set_exception(LinkNotFound("Did not find %s in stdout." % repr(self.look_for)))

    async def readall(self, reader, accumulator, blocksize=20):
        while True:
            block = await reader.read(blocksize)
            #print("got block", repr(block))
            if self.capture:
                accumulator.append(block)
            if len(block) < 1:
                break

    def on_timeout(self):
        if self.verbose:
            print("process timeout")
        self.process.terminate()

if __name__ == "__main__":
    start_script()
