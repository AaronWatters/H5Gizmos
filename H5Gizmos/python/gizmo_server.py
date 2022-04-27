
from . import H5Gizmos
#from . import gz_resources

from aiohttp import content_disposition_filename, web
#import aiohttp
import asyncio
#import weakref
import mimetypes
import os
import sys
import contextlib
import socket
import traceback
import sys

# Max size for posts -- really big
DEFAULT_MAX_SIZE = 1000 * 1000 * 1000 * 1000 * 100

# Packet chunk size limit for both GET and web socket
DEFAULT_PACKET_SIZE = 1000 * 1000 * 10

PROCESS_SHARED_GIZMO_SERVER = None

def get_or_create_event_loop():
    try:
        # xxxx this is deprecated in python 3.10 -- need a workaround that gets an unstarted event loop(?) or something
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop

def run(main_awaitable, server=None, run_forever=True, exit_on_disconnect=None, log_messages=False, verbose=True):
    """
    Get a gizmo and run it in an asynchronous run program.
    Start a server if no server is provided.
    """
    #if exit_on_disconnect is None:
    #    # If not specified exit on disconnect when not in notebook.
    #    exit_on_disconnect = not isnotebook()
    #print("Running.  Exit on disconnect", exit_on_disconnect)
    server = _check_server(server, verbose=verbose)
    # create and schedule the main task
    gizmo = server.gizmo(exit_on_disconnect=exit_on_disconnect, log_messages=log_messages)
    H5Gizmos.schedule_task(main_awaitable(gizmo))
    if run_forever:
        #get_or_create_event_loop().run_forever()
        run_until_exit()

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
            #traceback.print_exc(file=sys.stdout)
            #print("---- Terminating")
            # prevent duplicate exception
            #try:
            #    task.result()
            #except:
            #    pass
            sys.exit(1)

    H5Gizmos.schedule_task(deferred_task())
    #get_or_create_event_loop().run_forever()
    run_until_exit()

def run_until_exit():
    try:
        get_or_create_event_loop().run_forever()
    except SystemExit as e:
        print ("System exit:")

async def get_gizmo(from_server=None, verbose=False, log_messages=False, title="Gizmo"):
    """
    Get a gizmo (the official way).  Set up a server iff needed.
    """
    from_server = _check_server(from_server, verbose=verbose)
    return from_server.gizmo(log_messages=log_messages, title=title)

def _check_server(server, verbose=False):
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
            # schedule the server task
            server.run_in_task()
    return server


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

def get_local_ip():
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = socket.gethostbyname("localhost")
    return local_ip

def choose_port(limit=1000):
    for i in range(limit):
        port = DEFAULT_PORT + i
        if not is_port_in_use(port):
            return port
    raise ValueError("Could not find open port: " + repr(
        (DEFAULT_PORT, DEFAULT_PORT+limit)))


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

# https://blog.addpipe.com/camera-and-microphone-access-in-cross-oirigin-iframes-with-feature-policy/
# https://stackoverflow.com/questions/9162933/make-iframe-height-dynamic-based-on-content-inside-jquery-javascript
# https://stackoverflow.com/questions/22086722/resize-cross-domain-iframe-height

IFRAME_TEMPLATE = """
<script>
(function () {{
    var identifier = "{IDENTIFIER}";
    window.addEventListener("message", function(e) {{
        var this_frame = document.getElementById(identifier);
        var margin = {MARGIN};
        var min_height = {MIN_HEIGHT};
        if ((this_frame) && (this_frame.contentWindow === e.source)) {{
            //console.log("processing message", e.data.height);
            var height = Math.max(min_height, e.data.height + margin)
            var height_px = (height) + "px";
            this_frame.height = height_px;
            this_frame.style.height = height_px;
        }}
    }});
}}) ();
</script>

<iframe id="{IDENTIFIER}"
    title="{TITLE}"
    width="100%"
    height="{MIN_HEIGHT}px"
    src="{URL}"
    {ALLOW_LIST}
</iframe>"""

STD_ALLOW_LIST = 'allow="camera;microphone;display-capture;autoplay"'

async def display_gizmo_jupyter_iframe(gizmo, min_height=20, delay=0.1, allow_list=STD_ALLOW_LIST, **args):
    identifier = gizmo._identifier
    url = gizmo._entry_url()
    D = dict(
        IDENTIFIER = identifier,
        TITLE = identifier,
        #HEIGHT = height,
        MARGIN = 10,
        URL = url,
        ALLOW_LIST = allow_list,
        DELAY = 10000,
        MIN_HEIGHT = min_height,
    )
    iframe_html = IFRAME_TEMPLATE.format(**D)
    #server_task = server.run_in_task(**args)
    async def start_gizmo():
        from IPython.display import HTML, display
        await asyncio.sleep(delay)
        #print("displaying", url)
        #print(iframe_html)
        display(HTML(iframe_html))
    start_task = H5Gizmos.schedule_task(start_gizmo())
    await start_task

'''
async def embed(gizmo, allow_list='allow="camera;microphone"', delay=0.1):
    "Embed gizmo in jupyter.  Create or use the global server if needed."
    from IPython.display import HTML, display
    assert isnotebook(), "Gizmo embedding is only supported inside jupyter notebooks."
    identifier = gizmo._identifier
    url = gizmo._entry_url()
    D = dict(
        IDENTIFIER = identifier,
        TITLE = identifier,
        #HEIGHT = height,
        URL = url,
        ALLOW_LIST = allow_list,
        #DELAY = 10000,
    )
    iframe_html = IFRAME_TEMPLATE.format(**D)
    await asyncio.sleep(delay)  # This should allow the server to start if needed.
    display(HTML(iframe_html))'''

# name aliases (maybe rename later?)
#launch_in_browser = run_gizmo_standalone

class GzServer:

    verbose = False

    def __init__(
            self, 
            prefix="gizmo", 
            server=None, 
            port=None,  # Choose an available port.
            interface=STDInterface,
            out=None,  # context redirect (like widgets.Output) or None
            err=None,  # context redirect (like widgets.Output) or None
            ):
        server = server or get_local_ip()
        if port is None:
            port = choose_port()
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
            ):
        result = H5Gizmos.Gizmo(server=self, exit_on_disconnect=exit_on_disconnect, log_messages=log_messages)
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

    def run_in_task(self, app_factory=web.Application, async_run=web._run_app, **args):
        loop = get_or_create_event_loop()
        app = self.get_app(app_factory=app_factory)
        self.status = "making runner"
        if self.verbose:
            print("making runner")
        runner = self.make_runner(app, async_run=async_run, **args)
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
        # https://docs.aiohttp.org/en/v0.22.4/web.html#aiohttp-web-graceful-shutdown
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
          
    async def make_runner(self, app, async_run=web._run_app, **args):
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
            self.my_print ("runner using port", port)
            if "print" not in args:
                args["print"] = self.my_print
            await async_run(app, port=port, **args)
        except asyncio.CancelledError:
            self.status = "app has been cancelled,"
            #pr(self.status)
            self.cancelled = True
        finally:
            self.status = "app has stopped."
            #pr(self.status)
            self.stopped = True

    def add_routes(self):
        app = self.app
        prefix = "/" + self.prefix
        app.router.add_route(GET, prefix + '/http/{tail:.*}', self.handle_http_get)
        app.router.add_route(POST, prefix + '/http/{tail:.*}', self.handle_http_post)
        app.router.add_route(GET, prefix + '/ws/{tail:.*}', self.handle_web_socket)

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

    def handle_http_get(self, request, interface=None):
        #pr(" ... server get", request.path)
        with self.my_stderr():
            with self.my_stdout():
                if interface is None:
                    interface = self.interface
                return self.handle(request, method=GET, interface=interface)

    def handle_http_post(self, request, interface=None):
        with self.my_stderr():
            with self.my_stdout():
                #pr(" ... server post", request.path)
                if interface is None:
                    interface = self.interface
                return self.handle(request, method=POST, interface=interface)

    def handle_web_socket(self, request, interface=None):
        with self.my_stderr():
            with self.my_stdout():
                #pr(" ... server socket", request.path)
                if interface is None:
                    interface = self.interface
                return self.handle(request, method=WS, interface=interface)

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
            return await self.handle_ws(info, request, interface)
        else:
            assert filename is not None, "HTTP requests should have a filename " + repr(info.splitpath)
            handler = f2h.get(filename)
            assert handler is not None, "No handler for filename " + repr(info.splitpath)
            #pr("... mgr delegating to handler", handler)
            if method == GET:
                return await handler.handle_get(info, request, interface=interface)
            elif method == POST:
                return await handler.handle_post(info, request, interface=interface)
            else:
                raise AssertionError("unknown http method: " + repr(method))

    async def handle_ws(self, info, request, interface=STDInterface):
        handler = self.web_socket_handler
        #pr ("delegating web socket handling to", handler)
        assert handler is not None, "No web socket handler for id " + repr(self.identifier)
        await handler.handle(info, request, interface)

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
            ):
        assert method in ("http", "ws"), "method should be http or ws: " + repr(method)
        server = server or for_gizmo._server
        port = port or for_gizmo._port
        prefix = prefix or self.prefix
        identifier = identifier or self.identifier
        path_components = [prefix, method, identifier]
        if filename is not None:
            path_components.append(filename)
        path = "/".join(path_components)
        url = "%s://%s:%s/%s" % (protocol, server, port, path)
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

    def set_content(self, byte_content, content_type=None):
        if len(byte_content) > self.get_sanity_limit:
            raise ValueError("transfers larger than %s not yet supported" %
                self.get_sanity_limit)
        if content_type is not None:
            self.content_type = content_type
        self.bytes = bytes(byte_content)

    get_sanity_limit = 1590000000

    async def handle_get(self, info, request, interface=STDInterface):
        # based on https://gist.github.com/buxx/d0a749b6673a18a90b47464b79254124
        bytes = self.bytes
        ln = len(bytes)
        chunksize = self.chunksize
        content_type = self.content_type
        if ln < chunksize:
            return interface.respond(body=bytes, content_type=content_type)
        elif ln < self.get_sanity_limit:
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
        await self.pipeline.handle_websocket_request(request)
