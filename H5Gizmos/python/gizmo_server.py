
#from . import H5Gizmos
from . import gz_parent_protocol as H5Gizmos
#from . import gz_resources

from aiohttp import web
import aiohttp
import asyncio
#import weakref
import mimetypes
import os
import sys
import contextlib
import socket
#import traceback
import sys
import time

# Max size for posts -- really big
DEFAULT_MAX_SIZE = 1000 * 1000 * 1000 * 1000 * 100

# Packet chunk size limit for both GET and web socket
#DEFAULT_PACKET_SIZE = 1000 * 1000 * 10
DEFAULT_PACKET_SIZE = H5Gizmos.PACKET_LIMIT

PROCESS_SHARED_GIZMO_SERVER = None

# Environment variable used to construct proxied urls.
PREFIX_ENV_VAR = "GIZMO_LINK_PREFIX"

# Environment variable indicating which port to use.
USE_PORT_ENV_VAR = "GIZMO_USE_PORT"

# Environment variable indicating which server address to use (eg, "localhost")
# Setting this variable will disable reachability testing
# because an external server name may not be reachable from within a container, for example.
USE_SERVER_ADDRESS_VAR = "GIZMO_USE_SERVER_ADDRESS"

# set/unset to enable/disable auto detection of prefix
DETECT_PREFIX_ENV_VAR = True

def get_or_create_event_loop0():
    try:
        # xxxx this is deprecated in python 3.10 -- need a workaround that gets an unstarted event loop(?) or something
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

def get_or_create_event_loop1():
    try:
        return asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
    
get_or_create_event_loop = get_or_create_event_loop0

'''
def run(main_awaitable, server=None, run_forever=True, exit_on_disconnect=None, log_messages=False, verbose=True):
    """
    Get a gizmo and run it in an asynchronous run program.
    Start a server if no server is provided.
    """
    server = _check_server(server, verbose=verbose)
    # create and schedule the main task
    gizmo = server.gizmo(exit_on_disconnect=exit_on_disconnect, log_messages=log_messages)
    H5Gizmos.schedule_task(main_awaitable(gizmo))
    if run_forever:
        #get_or_create_event_loop().run_forever()
        run_until_exit()
'''

def serve(coroutine, verbose=False, delay=0.5):
    """
    Set up the global gizmo server and schedule the task, then run the event loop forever.
    """
    # xxx common code refactor?
    _check_server(None, verbose=verbose)

    async def deferred_task():
        # gymnastics to avoid duplicate exceptions....
        await asyncio.sleep(delay)
        task = H5Gizmos.schedule_task(coroutine)
        try:
            await task
        except Exception:
            print("---- Exception in main gizmo task.  Terminating.")
            sys.exit(1)

    H5Gizmos.schedule_task(deferred_task())
    #get_or_create_event_loop().run_forever()
    run_until_exit()

def run_until_exit():
    try:
        get_or_create_event_loop().run_forever()
    except SystemExit as e:
        print ("System exit:")

async def get_gizmo(
        from_server=None, 
        verbose=False, 
        log_messages=False, 
        title="Gizmo",
        template=None,
        ):
    """
    Get a gizmo (the official way).  Set up a server iff needed.
    """
    from_server = _check_server(from_server, verbose=verbose)
    await from_server.check_server_name_is_reachable()
    return from_server.gizmo(log_messages=log_messages, title=title, template=template)

def _check_server(server=None, verbose=False):
    "Make sure the gizmo server is set up."
    global PROCESS_SHARED_GIZMO_SERVER
    out = None  # xxxx
    err = None
    # set up the server
    if server is None:
        server = PROCESS_SHARED_GIZMO_SERVER
        if server is None:
            server = PROCESS_SHARED_GIZMO_SERVER = GzServer(out=out, err=err)
            if not verbose:
                server.capture_stdout()
            else:
                print("Created verbose GzServer")
            # schedule the server task
            server.run_in_task()
        if DETECT_PREFIX_ENV_VAR:
            prefix = os.environ.get(PREFIX_ENV_VAR)
            if prefix is not None:
                # xxxx could sanity check the prefix?
                if verbose:
                    print("setting server prefix", [PREFIX_ENV_VAR, prefix])
                set_url_prefix(prefix, server=server)
        #server.check_server_name_is_reachable() -- but need to await...
    return server

def running_under_gizmo_link():
    """
    Detect whether the process was started by the gizmo_link proxy server.
    """
    return os.environ.get(PREFIX_ENV_VAR) is not None

def set_url_prefix(proxy_prefix, server=None):
    """
    Specify the proxy prefix the server should use.

    This overrides localhost URLs and relative links.
    """
    server = _check_server(server)
    server.set_url_prefix(proxy_prefix)

def use_local_gui(server=None):
    "Test whether to try to launch a web browser (gui app) using the local operating system."
    server = _check_server(server)
    return server.use_local_gui()

DEFAULT_PORT = 8675 # 309 https://en.wikipedia.org/wiki/867-5309/Jenny
GET = "GET"
POST = "POST"
WS = "ws"
REQUEST_METHODS = frozenset([GET, POST, WS])
#UTF8 = "utf-8"

# https://stackoverflow.com/questions/2470971/fast-way-to-test-if-a-port-is-in-use-using-python
def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

async def get_reachable_server_name(local_ip, random_port, verbose=True):
    """
    Choose the most useful reachable server name which can be inferred
    from available interfaces.
    For use in external scripts, for example to pass to containers.
    """
    validator = ValidateServerConnection(local_ip, random_port, verbose=verbose)
    await validator.future
    if validator.succeeded:
        return local_ip
    return "localhost" # fall back default

def print_reachable_server_name(verbose=True):
    """
    Print the most useful reachable server name.
    External script entry point.
    """
    # xxxx is this historical?  why is it here?
    import io, sys
    # work around some sort of anomaly with printing for now, ignore stdout...
    stdout = sys.stdout
    if not verbose:
        sys.stdout = io.StringIO()
    local_ip = get_local_ip()
    random_port = choose_port1()
    if verbose:
        print("Validating connection to", repr(local_ip), "port", random_port)
    server = GzServer(server=local_ip, port=random_port)
    server.verbose = verbose
    server.run_in_task(log=True)
    async def print_task():
        # allow server to start
        await asyncio.sleep(0.1)
        if verbose:
            print("print_task started.")
        name = await get_reachable_server_name(local_ip, random_port, verbose=verbose)
        if verbose:
            print("print task got", repr(name))
        sys.stdout = stdout
        print(name)
        if verbose:
            print("print task exitting with name", repr(name))
        sys.stdout = sys.stderr = io.StringIO()
        sys.exit()
    loop = get_or_create_event_loop()
    H5Gizmos.schedule_task(print_task())
    run_until_exit()

def get_local_ip(port=None):
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = socket.gethostbyname("localhost")
    return local_ip


def choose_port0(limit=1000):
    "old version"
    for i in range(limit):
        port = DEFAULT_PORT + i
        if not is_port_in_use(port):
            #print ("CHOSE PORT", port)
            return port
    raise ValueError("Could not find open port: " + repr(
        (DEFAULT_PORT, DEFAULT_PORT+limit)))


def choose_port1():
    """
    Copied from repo2docker...
    Hacky method to get a free random port on local host
    """
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port

def choose_port(verbose=True):
    """
    Try to use port indicated by USE_PORT_ENV_VAR, or fall back to any free port.
    """
    port = None
    port_str = os.environ.get(USE_PORT_ENV_VAR)
    #("DEBUG:", USE_PORT_ENV_VAR, repr(port_str))
    if port_str is not None:
        try:
            port_int = int(port_str)
        except Exception as e:
            if verbose:
                print("Invalid port int ", USE_PORT_ENV_VAR, "value", repr(port_str))
        else:
            if is_port_in_use(port_int):
                if verbose:
                    print("Port int ", USE_PORT_ENV_VAR, "value", repr(port_str), "is not available.")
            else:
                port = port_int
        if verbose and port is None:
            print("Failed to use", USE_PORT_ENV_VAR, "value", repr(port_str), "falling back to random port.")
        else:
            port = port_int
    if port is not None:
        #("DEBUG: using specified port", port)
        return port
    else:
        #("DEBUG: Using random port.")
        return choose_port1()

# use the old version:
#choose_port = choose_port0

def force_print(*args, **kwargs):
    """
    Print to stdout even if it is redirected.
    """
    #print("FORCE PRINT", args, kwargs)
    with contextlib.redirect_stdout(sys.__stdout__):
        print(*args, **kwargs)


def get_file_bytes(path):
    # xxxx what about binary files?
    f = open(path, "rb")
    bytes_content = f.read()
    return bytes_content

class WebInterface:
    "External interface encapsulation to help support debugging and testing."

    def __init__(
        self,
        respond = web.Response,
        stream_respond = web.StreamResponse,
        ws_respond = web.WebSocketResponse,
        get_file_bytes = get_file_bytes,
        file_exists = os.path.isfile,
        folder_exists = os.path.isdir,
        app_factory=web.Application,
        async_run=web._run_app,
    ):
        self.respond = respond
        self.stream_respond = stream_respond
        self.ws_respond = ws_respond
        self.get_file_bytes = get_file_bytes
        self.file_exists = file_exists
        self.folder_exists = folder_exists
        self.app_factory = app_factory
        self.async_run = async_run


STDInterface = WebInterface()


def gizmo_task_server(
        prefix="gizmo", 
        server=None, 
        port=None, 
        interface=STDInterface,
        **args,
        ):
    server = server or get_local_ip()
    S = GzServer(
        prefix=prefix,
        server=server,
        port=port,
        interface=interface,
    )
    S.run_in_task(app_factory=interface.app_factory, async_run=interface.async_run, **args)
    return S

def isnotebook():
    # https://stackoverflow.com/questions/15411967/how-can-i-check-if-code-is-executed-in-the-ipython-notebook
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter

TAB_OPENER_TEMPLATE = """
<script>
window.open("{URL}", "_blank").focus();
</script>
"""

async def display_gizmo_in_jupyter_new_tab(url, delay=0.1):
    from IPython.display import HTML, display
    D = dict(URL=url)
    script = TAB_OPENER_TEMPLATE.format(**D)
    print("using script", script)
    await asyncio.sleep(delay)
    display(HTML(script))


class GzServer:

    verbose = False

    # The URL prefix to use for fully specified links. If set this overrides other options.
    # should be of form:
    #   http://127.0.0.1:60327/GizmoLink/
    #   https://notebooks.gesis.org/binder/jupyter/user/aaronwatters-h5gizmos-6f2q3jdf/GizmoLink/
    # 
    url_prefix = None

    def __init__(
            self, 
            prefix="gizmo", 
            server=None, 
            port=None,  # Choose an available port.
            interface=STDInterface,
            out=None,  # context redirect (like widgets.Output) or None
            err=None,  # context redirect (like widgets.Output) or None
            ):
        if port is None:
            port = choose_port()
        server = server or get_local_ip(port)
        self.prefix = prefix
        self.server = server
        self.port = port
        self.interface = interface
        self.status = "initialized"
        self.task = None
        self.app = None
        self.stopped = False
        self.cancelled = False
        self.identifier_to_manager = {}
        #self.counter = 0
        self.out = out
        self.err = err
        self.captured_stdout = None
        self.validator = None

    async def check_server_name_is_reachable(self):
        """
        Adjust server address.
        Use environment override if set.
        Otherwise if the current choice is not reachable use "localhost".
        """
        # Override server address and don't test reachability
        # if the USE_SERVER_ADDRESS_VAR environment variable is set.
        server_str = os.environ.get(USE_SERVER_ADDRESS_VAR)
        if server_str is not None and len(server_str) > 0:
            self.server = server_str
            return True
        validator = self.validator
        if validator is None:
            server = self.server
            port = self.port
            validator = ValidateServerConnection(server, port)
            self.validator = validator
        await validator.future
        if not validator.succeeded:
            # fall back to localhost
            #print("server", server, "is not reachable -- using localhost.")
            self.server = "localhost"
        else:
            #print("server", server, "reachable")
            pass
        return validator.succeeded

    def set_url_prefix(self, url_prefix):
        self.url_prefix = url_prefix

    def use_local_gui(self):
        "Test whether to try to launch a web browser (gui app) using the local operating system."
        # If the url prefix is set then only launch via browser link mechanisms
        if self.url_prefix is not None:
            return False
        return True

    def capture_stdout(self):
        import contextlib
        import io
        self.captured_stdout = io.StringIO()
        self.out = contextlib.redirect_stdout(self.captured_stdout)

    def my_stdout(self):
        if self.out:
            return self.out
        return contextlib.redirect_stdout(sys.stdout)

    def my_stderr(self):
        if self.err:
            return self.err
        return contextlib.redirect_stderr(sys.stderr)

    def gizmo(
            self, 
            title="Gizmo",
            packet_limit=DEFAULT_PACKET_SIZE, 
            auto_flush=True,
            entry_filename="index.html",
            poll_for_exceptions=True,
            exit_on_disconnect=False,
            log_messages=False,
            template=None,
            ):
        result = H5Gizmos.Gizmo(
            server=self, 
            exit_on_disconnect=exit_on_disconnect, 
            log_messages=log_messages,
            template=template,
            )
        handler = GizmoPipelineSocketHandler(result, packet_limit=packet_limit, auto_flush=auto_flush)
        result._set_pipeline(handler.pipeline)
        mgr = self.get_new_manager(websocket_handler=handler)
        result._set_manager(self, mgr)
        result._configure_entry_page(title=title, filename=entry_filename)
        if poll_for_exceptions:
            result._start_report_error_task()
        return result

    def get_new_manager(self, websocket_handler=None):
        from H5Gizmos import new_identifier
        #c = self.counter
        #self.counter = c + 1
        #identifier = "MGR" + str(c)
        identifier = new_identifier("MGR")
        result = GizmoManager(identifier, self, websocket_handler)
        self.identifier_to_manager[identifier] = result
        return result

    def run_standalone(self, app_factory=web.Application, sync_run=web.run_app, **args):
        # used in test case only
        app = self.get_app(app_factory=app_factory)
        self.status = "running standalone"
        result = sync_run(app, port=self.port, **args)
        self.status = "done standalone"
        return result

    def run_in_task(self, app_factory=web.Application, async_run=web._run_app, log=True, **args):
        loop = get_or_create_event_loop()
        app = self.get_app(app_factory=app_factory)
        self.status = "making runner"
        if self.verbose:
            print("making runner")
        runner = self.make_runner(app, async_run=async_run, log=log, **args)
        if self.verbose:
            print("creating task")
        task = loop.create_task(runner)
        self.task = task
        return task

    def get_app(self, app_factory=web.Application):
        self.app = app_factory(client_max_size=DEFAULT_MAX_SIZE)
        self.add_routes()
        self.app.on_shutdown.append(self.on_shutdown)
        return self.app

    async def on_shutdown(self, app):
        global PROCESS_SHARED_GIZMO_SERVER
        # https://docs.aiohttp.org/en/v0.22.4/web.html#aiohttp-web-graceful-shutdown
        #("SERVER IS SHUTTING DOWN!!", self.port)
        if self is PROCESS_SHARED_GIZMO_SERVER:
            # In tests, create a new server...
            PROCESS_SHARED_GIZMO_SERVER = None
        with self.my_stderr():
            with self.my_stdout():
                for mgr in self.identifier_to_manager.values():
                    h = mgr.web_socket_handler
                    if h is not None:
                        ws = h.ws
                        if ws is not None:
                            await ws.close(code=999, message='Server shutdown')

    def my_print(self, *args, **kwargs):
        with self.my_stderr():
            with self.my_stdout():
                print(*args, **kwargs)
          
    async def make_runner(self, app, async_run=web._run_app, log=True, **args):
        self.status = "starting runner"
        #app = self.get_app()
        try:
            port = self.port
            if port is None:
                port = choose_port()
                #print("chose port", port)
                self.port = port
            else:
                #raise ValueError("didn't choose port???")
                pass
            #self.my_print ("runner using port", port)
            if "print" not in args:
                args["print"] = self.my_print
            # Start the validator (which delays immediately to permit server start)
            #H5Gizmos.schedule_task(self.check_server_name_is_reachable())
            if log:
                if self.verbose:
                    print("running with log")
                await async_run(app, port=port, **args)
            else:
                if self.verbose:
                    print("running with no log")
                def ignore_print(*args, **kwargs):
                    pass
                await async_run(
                    app, port=port, 
                    access_log=None, print=ignore_print, **args)
        except asyncio.CancelledError:
            self.status = "app has been cancelled,"
            #pr(self.status)
            self.cancelled = True
        finally:
            self.status = "app has stopped."
            #pr(self.status)
            self.stopped = True

    secret = bytes(str(time.time()), "utf8")

    def add_routes(self):
        app = self.app
        prefix = "/" + self.prefix
        app.router.add_route(GET, prefix + '/http/{tail:.*}', self.handle_http_get)
        app.router.add_route(POST, prefix + '/http/{tail:.*}', self.handle_http_post)
        app.router.add_route(GET, prefix + '/ws/{tail:.*}', self.handle_web_socket)
        app.router.add_route(GET, "/ping", self.handle_ping)

    async def handle_ping(self, request):
        message = b'pong ' + self.secret
        http_response = web.Response(body=message, content_type="text/plain")
        return http_response

    async def handle(self, request, method="GET", interface=None):
        if interface is None:
            interface = self.interface
        #pr(" ... server handling", request.path)
        i2m = self.identifier_to_manager
        try:
            info = RequestUrlInfo(request, self.prefix)
            identifier = info.identifier
            mgr = i2m.get(identifier)
            assert mgr is not None, "could not resolve " + repr(identifier)
            #pr(" ... delegate handle to mgr", mgr)
            return await mgr.handle(method, info, request, interface=interface)
        except AssertionError as e:
            #pr("... 404 for assertion failure: ", e)
            return interface.stream_respond(status=404, reason=repr(e))

    async def handle_http_get(self, request, interface=None):
        #pr(" ... server get", request.path)
        with self.my_stderr():
            with self.my_stdout():
                if interface is None:
                    interface = self.interface
                return await self.handle(request, method=GET, interface=interface)

    async def handle_http_post(self, request, interface=None):
        with self.my_stderr():
            with self.my_stdout():
                #pr(" ... server post", request.path)
                if interface is None:
                    interface = self.interface
                return await self.handle(request, method=POST, interface=interface)

    async def handle_web_socket(self, request, interface=None):
        with self.my_stderr():
            with self.my_stdout():
                #pr(" ... server socket", request.path)
                if interface is None:
                    interface = self.interface
                return await self.handle(request, method=WS, interface=interface)

    async def shutdown(self):
        with self.my_stderr():
            with self.my_stdout():
                app = self.app
                if self.task is not None:
                    self.task.cancel()
                if app is not None:
                    # https://stackoverflow.com/questions/55236254/cant-stop-aiohttp-websocket-server
                    await app.shutdown()
                    await app.cleanup()
                    # should also clean up any outstanding web sockets xxxx ????

class RequestUrlInfo:

    request_methods = ("http", "ws")

    def __init__(self, request, prefix):
        self.request = request
        path = self.path = request.path
        sp = self.splitpath = path.split("/")
        ln = len(sp)
        # ??? xxx eventually allow mounting directories?
        assert 4 <= ln, "expected 4 or more components to path: " + repr(sp)
        assert sp[0] == "", "path should start with slash: " + repr(path)
        assert sp[1] == prefix, "path should have prefix: " + repr((prefix, path))
        method = self.method = sp[2]
        assert method in self.request_methods, "unknown request method: " + repr((method, path))
        self.identifier = sp[3]
        self.filename = None
        self.additional_path = None
        if ln > 4:
            self.filename = sp[4]
            self.additional_path = sp[5:]

class GizmoManager:

    def __init__(self, identifier, server, websocket_handler=None):
        #self.server = server  # xxx maybe make this a weak ref?
        self.identifier = identifier
        #self.web_socket = None
        self.web_socket_handler = websocket_handler
        self.filename_to_http_handler = {}
        #self.url_path = "/%s/%s" % (server.prefix, identifier)
        self.prefix = server.prefix
        #pr(self.identifier, "manager init with socket handler", self.web_socket_handler)

    def add_file(self, at_path, filename=None, content_type=None, interface=STDInterface):
        if filename is None:
            filename = os.path.split(at_path)[-1]
        handler = FileGetter(at_path, filename, self, content_type, interface=interface)
        return self.add_http_handler(filename, handler)

    def serve_folder(self, full_path, url_file_name, interface=STDInterface):
        #print("\n making folder getter for", full_path)
        handler = FolderGetter(full_path, url_file_name, self, interface=interface)
        return self.add_http_handler(url_file_name, handler)

    def add_http_handler(self, filename, handler):
        self.filename_to_http_handler[filename] = handler
        return handler

    def remove_http_handler(self, filename):
        if filename in self.filename_to_http_handler:
            del self.filename_to_http_handler[filename]

    def validate_relative_path(self, path):
        """
        Check that relative path will resolve.
        """
        if path.startswith("./"):
            path = path[2:]
        components = path.split("/")
        if not components:
            raise NoSuchRelativePath("no components in relative path: " + repr(path))
        filename = components[0]
        remainder = components[1:]
        f2h = self.filename_to_http_handler
        handler = f2h.get(filename)
        if handler is None:
            raise NoSuchRelativePath("no handler for filename " + repr([filename, remainder]))
        return handler.validate_relative_path(remainder)

    async def handle(self, method, info, request, interface=STDInterface):
        #pr("... mgr handling", request.path, "method", method)
        filename = info.filename
        f2h = self.filename_to_http_handler
        if method == WS:
            assert filename is None, "WS request should have no filename " + repr(info.splitpath)
            result = await self.handle_ws(info, request, interface)
            #pr("... handle_ws returning", result)
        else:
            assert filename is not None, "HTTP requests should have a filename " + repr(info.splitpath)
            handler = f2h.get(filename)
            assert handler is not None, "No handler for filename " + repr(info.splitpath)
            #pr("... mgr delegating to handler", handler)
            if method == GET:
                result = await handler.handle_get(info, request, interface=interface)
            elif method == POST:
                result = await handler.handle_post(info, request, interface=interface)
            else:
                raise AssertionError("unknown http method: " + repr(method))
        #pr("... mgr handled", request.path, "method", method)
        #pr("... returning", result)
        return result

    async def handle_ws(self, info, request, interface=STDInterface):
        handler = self.web_socket_handler
        #pr("delegating web socket handling to", handler)
        assert handler is not None, "No web socket handler for id " + repr(self.identifier)
        result = await handler.handle(info, request, interface)
        return result

    def jupyter_url_suffix(
            self,
            for_gizmo,
            method,
            filename=None,
            action="connect",
    ):
        # eg: GizmoLink/connect/54211/gizmo/http/MGR_1702579977573_3/index.html
        from .gizmo_link import JUPYTER_SERVER_PLUGIN_NAME
        port = for_gizmo._port
        prefix = self.prefix
        identifier = self.identifier
        components = [
            JUPYTER_SERVER_PLUGIN_NAME,
            action,
            str(port),
            prefix,
            method,
            identifier,
        ]
        if filename is not None:
            components.append(filename)
        result = "/".join(components)
        return result

    def local_url(
            self, 
            for_gizmo, 
            method,
            protocol="http", 
            server=None,
            port=None,
            prefix=None,
            identifier=None,
            filename=None,
            #gizmo_link_reference=False,  # xxxx not used?
            gizmo_link=None,  # like "GizmoLink" url fragment if set
            verbose=False,
            strict=True,   # raise if gizmo_link url inference fails
            ):
        "Get the URL for connecting to for_gizmo."
        assert method in ("http", "ws"), "method should be http or ws: " + repr(method)
        server = server or for_gizmo._server
        url_prefix = for_gizmo._url_prefix
        port = port or for_gizmo._port
        prefix = prefix or self.prefix
        identifier = identifier or self.identifier
        path_components = [prefix, method, identifier]
        if filename is not None:
            path_components.append(filename)
        path = "/".join(path_components)
        # if the server url_prefix is provided, use it to make a fully specified URL
        if url_prefix is not None:
            # for example
            #    url_prefix = "http://127.0.0.1:60327/GizmoLink/""
            #    port = 50109
            #    path = gizmo/http/MGR_1653322541609_2/index.html
            # fully_specified_url =
            #  "http://127.0.0.1:60327/GizmoLink/connect/50109/gizmo/http/MGR_1653322541609_2/index.html"
            fully_specified_url = "%sconnect/%s/%s" % (url_prefix, port, path)
            if verbose:
                print("using full url from prefix", (url_prefix, fully_specified_url))
            return fully_specified_url
        if gizmo_link is not None:
            # Try to make a relative link like:
            #   BASEURL/GizmoLink/connect/PORT/SOME_PATH
            # for use in Jupyter servers.  This will only work if we
            # can find the right server base url.
            from notebook.notebookapp import list_running_servers
            L = list(list_running_servers())
            server_info = None
            if len(L) == 1:
                # if there is only one server, use that one.
                server_info = L[0]
            else:
                # infer the server if it is the parent of this process
                ppid = os.getppid()
                for info in L:
                    if info["pid"] == ppid:
                        if verbose:
                            print("found parent server pid", ppid)
                        server_info = info
            if server_info is not None:
                base_url = server_info["base_url"]
                relative_url = "%s%s/connect/%s/%s" % (base_url, gizmo_link, port, path)
                #print ("relative_url is", relative_url)
                if verbose:
                    print("using relative url", relative_url)
                return relative_url
            else:
                if verbose:
                    print("Too many notebook servers for relative proxy link", len(L))
                if strict:
                    raise NoSuchRelativePath(
                        "Cannot infer relative gizmo link path: " +
                        repr([len(L), gizmo_link, port, path])
                        )
            # xxxx otherwise fall back to fully specified local url?
        # default or fallback: fully specified local url.
        url = "%s://%s:%s/%s" % (protocol, server, port, path)
        if verbose:
            print ("fallback fully specified url", url)
        return url

class NoSuchRelativePath(ValueError):
    "The manager doesn't know how to resolve this path."

class FileGetter:

    "Serve the contents of a file from the file system."

    def __init__(self, fs_path, filename, mgr, content_type=None, interface=STDInterface):
        assert self.path_ok(fs_path, interface), "Bad path: " + repr(fs_path)
        self.fs_path = fs_path
        self.get_url_info(filename, mgr, content_type)

    def path_ok(self, fs_path, interface):
        return interface.file_exists(fs_path)

    def validate_relative_path(self, remainder):
        if remainder:
            raise NoSuchRelativePath("File is not a folder: " + repr([self.fs_path, remainder]))

    def get_url_info(self, filename, mgr, content_type):
        self.prefix = mgr.prefix
        self.identifier = mgr.identifier
        self.filename = filename
        self.encoding = None
        if content_type is None:
            (content_type, encoding) = mimetypes.guess_type(filename)
            self.encoding = encoding # not used... xxx
        self.content_type = content_type

    def method_path(self, method=GET):
        # only used in testing...
        # xxxx duplicated code with local_url above
        mprefix = None
        if method == GET:
            mprefix = "http"
        elif method == POST:
            mprefix = "http"
        elif method == WS:
             mprefix = "ws"
        else:
            raise ValueError("unknown method: " + repr(method))
        components = ["", self.prefix, mprefix, self.identifier, self.filename]
        return "/".join(components)

    async def handle_get(self, info, request, interface=STDInterface):
        path = self.fs_path
        apath = info.additional_path
        assert not apath, "File is not a folder: " + repr((path, apath))
        assert interface.file_exists(path)
        bytes = interface.get_file_bytes(path)
        return interface.respond(body=bytes, content_type=self.content_type)

    async def handle_post(self, info, request, interface=STDInterface):
        return await self.handle_get(info, request, interface=interface)

class FolderGetter(FileGetter):

    """
    Serve files under folder, guessing content types.
    """

    def path_ok(self, fs_path, interface):
        #print ("\n checking folder", fs_path, "\n")
        return interface.folder_exists(fs_path)

    async def handle_get(self, info, request, interface=STDInterface):
        path = self.fs_path
        apath = info.additional_path
        assert apath, "Folder requires sub-path: " + repr((path))
        all = [path] + list(apath)
        full_os_path = "/".join(all)
        assert interface.file_exists(full_os_path), "No such file found: " + repr(full_os_path)
        bytes = interface.get_file_bytes(full_os_path)
        (content_type, encoding) = mimetypes.guess_type(full_os_path)
        return interface.respond(body=bytes, content_type=content_type)

    def validate_relative_path(self, remainder, interface=STDInterface):
        path = self.fs_path
        if not remainder:
            raise NoSuchRelativePath("Cannot serve folder root: " + repr(path))
        all = [path] + list(remainder)
        full_os_path = "/".join(all)
        assert interface.file_exists(full_os_path), "No such file found: " + repr(full_os_path)

class BytesGetter(FileGetter):

    """
    Serve bytes.
    """

    def __init__(self, filename, byte_content, mgr, content_type, chunksize=DEFAULT_PACKET_SIZE):
        self.chunksize = chunksize
        self.get_url_info(filename, mgr, content_type)  # xxxx remove mgr someday (only for testing?)
        self.set_content(byte_content)

    def validate_relative_path(self, remainder):
        if remainder:
            raise NoSuchRelativePath("Bytes is not a folder: " + repr([self.filename, remainder]))

    def set_content(self, byte_content, content_type=None, check_sane=True):
        if check_sane and self.get_sanity_limit and len(byte_content) > self.get_sanity_limit:
            raise ValueError("transfers larger than %s not yet supported (%s)" %
                (self.get_sanity_limit, len(byte_content)))
        if content_type is not None:
            self.content_type = content_type
        self.bytes = bytes(byte_content)

    #get_sanity_limit = 1590000000
    get_sanity_limit = None  # no limit

    async def handle_get(self, info, request, interface=STDInterface):
        # based on https://gist.github.com/buxx/d0a749b6673a18a90b47464b79254124
        bytes = self.bytes
        ln = len(bytes)
        chunksize = self.chunksize
        content_type = self.content_type
        if ln < chunksize:
            return interface.respond(body=bytes, content_type=content_type)
        elif (self.get_sanity_limit is None) or (ln < self.get_sanity_limit):
            response = web.StreamResponse(
                status=200,
                reason='OK',
                headers={'Content-Type': content_type},
            )
            await response.prepare(request)
            cursor = 0
            while cursor < ln:
                #print("cursor", cursor)
                end = cursor + chunksize
                chunk = bytes[cursor : end]
                await response.write(chunk)
                cursor = end
            await response.write_eof()
            return response
        else:
            raise ValueError("transfers larger than %s not yet supported" %
                self.get_sanity_limit)

class GizmoPipelineSocketHandler:

    def __init__(self, gizmo, packet_limit=DEFAULT_PACKET_SIZE, auto_flush=True):
        pipeline = H5Gizmos.GZPipeline(gizmo, packet_limit=packet_limit, auto_flush=auto_flush)
        self.pipeline = pipeline
        self.ws = None

    async def handle(self, info, request, interface):
        #print("**** pipeline handler started")
        #pr("pipeline", self.pipeline)
        return await self.pipeline.handle_websocket_request(request)

class ValidateServerConnection:

    "Check that the web server '/ping' is reachable using the current port and server name."

    def __init__(self, server, port, delay=0.1, wait=0.2, verbose=False):
        self.succeeded = False
        self.status = "initialized"
        self.verbose = verbose
        self.server = server
        self.port = port
        self.delay = delay
        self.wait = wait
        self.loop = get_or_create_event_loop()
        self.future = self.loop.create_future()
        self.task = self.loop.create_task(self.validate())

    def __repr__(self) -> str:
        return "V" + repr([self.server, self.port, self.status, self.succeeded])

    async def validate(self, verbose=False):
        from contextlib import redirect_stderr
        import io
        verbose = verbose or self.verbose
        if verbose:
            print("starting connection validation")
        future = self.future
        now = str(time.time())
        server = self.server
        port = self.port
        url = "http://%s:%s/ping?now=%s" % (server, port, now)
        self.my_stderr = io.StringIO()
        with redirect_stderr(self.my_stderr):
            try:
                self.status = "delaying"
                await asyncio.sleep(self.delay)  # allow time for server to start (?)
                self.status = "preparing"
                self.timer = self.loop.create_task(self.timeout())
                # https://www.twilio.com/blog/asynchronous-http-requests-in-python-with-aiohttp
                # https://docs.aiohttp.org/en/stable/client_reference.html
                self.status = "requesting"
                async with aiohttp.ClientSession() as client:
                    async with client.get(url) as resp:
                        status = resp.status
                        bytes = await resp.read()
                        text = bytes.decode("utf-8")
                        self.status = "responded"
                        future.set_result((status, text))
                        if verbose:
                            print("validation succeeded")
                        self.succeeded = True
                        self.response = resp
            except asyncio.CancelledError:
                if verbose:
                    print("validation cancelled.")
                self.status = "cancelled"
            except Exception as e:
                self.status = repr(e)
                if verbose:
                    print("validation exception", e)
            if not future.done():
                if verbose:
                    print("validation defaults to fail.")
                future.set_result(False)

    async def timeout(self, verbose=False):
        future = self.future
        await asyncio.sleep(self.wait)
        self.task.cancel()
        if not future.done():
            if verbose:
                print("validation future timeout.")
            future.set_result(False)  
