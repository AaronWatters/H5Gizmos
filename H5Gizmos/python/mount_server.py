
"""
Initial proof of concept for gizmo server with mountable static paths
"""

#from simple_http import websocket_handler
from aiohttp import web
import aiohttp
import asyncio
import weakref
import mimetypes
import os

class GzContext:

    """
    Weakly referenced container for injecting gizmo components.
    When this context is finalized it should clean up all related resources.
    Components inside this container should never make hard references to the container to allow proper finalization.
    """

    verbose = False

    def __init__(
        self, 
        server, 
        static_content_provider, 
        dynamic_content_provider,
        web_socket_provider,
        gizmo_collection):
        (
            self.server,
            self.static_content_provider, 
            self.dynamic_content_provider,
            self.web_socket_provider,
            self.gizmo_collection,
        ) =  self.components = (
                server,
                static_content_provider, 
                dynamic_content_provider,
                web_socket_provider,
                gizmo_collection,
            )
        # following https://docs.python.org/3/library/weakref.html
        print("linking components")
        for component in self.components:
            if component is not None:
                component.weak_reference_context(self)
        self._finalizer = weakref.finalize(self, finalize_components, self.components)
        self.last_message = None
        self.vmessage("initialized")

    async def shutdown(self):
        await self.server.shutdown()

    def vmessage(self, *args):
        self.last_message = args
        if self.verbose:
            print("ctx", id(self), *args)

    def run_standalone(self):
        self.vmessage("running standalone")
        self.server.run_standalone()

    def run_in_task(self):
        self.vmessage("running in jupyter")
        task = self.server.run_in_task()
        return task

    def finalize(self):
        self.vmessage("explicitly finalizing")
        self._finalizer()

def finalize_components(components):
    for component in components:
        if component is not None:
            component.finalize()


DEFAULT_PORT = 9091


class GzComponentSuperclass:

    "Standard interactions with the context container."

    verbose = False

    def weak_reference_context(self, context):
        if self.verbose:
            print("linking", self)
        self._context_ref = weakref.ref(context)

    def get_context(self):
        return self._context_ref()

    def finalize(self):
        # default: do nothing
        if self.verbose:
            print("finalizing", self)
        self._context_ref = None

class GzServer(GzComponentSuperclass):

    "Http and web socket server logic"

    def __init__(self, prefix="/gizmo", port=DEFAULT_PORT):
        self.prefix = prefix
        self.port = port
        self.status = "initialized"
        self.task = None
        self.app = None
        self.stopped = False

    def run_standalone(self):
        app = self.get_app()
        self.status = "running standalone"
        result = web.run_app(app, port=self.port)
        self.status = "done standalone"
        return result

    def run_in_task(self, **args):
        loop = asyncio.get_event_loop()
        app = self.get_app()
        self.status = "making runner"
        if self.verbose:
            print("making runner")
        runner = self.make_runner(app, **args)
        if self.verbose:
            print("creating task")
        task = loop.create_task(runner)
        self.task = task
        return task
        
    async def make_runner(self, app, **args):
        self.status = "starting runner"
        #app = self.get_app()
        try:
            port = self.port
            print ("runner using port", port)
            await web._run_app(app, port=port, **args)
        except asyncio.CancelledError:
            self.status = "app has been cancelled,"
        finally:
            self.status = "app has stopped."
            self.stopped = True

    def get_app(self):
        self.app = web.Application()
        self.add_routes()
        return self.app

    async def shutdown(self):
        app = self.app
        if app is not None:
            # https://stackoverflow.com/questions/55236254/cant-stop-aiohttp-websocket-server
            await app.shutdown()
            await app.cleanup()
            # should also clean up any outstanding web sockets xxxx ????

    def add_routes(self):
        app = self.app
        context = self.get_context()
        assert context is not None, "No context -- cannot add routes."
        prefix = self.prefix
        if context.static_content_provider is not None:
            app.router.add_route('GET', prefix + '/static/{tail:.*}', context.static_content_provider.get_handler)
        if context.dynamic_content_provider is not None:
            app.router.add_route('GET', prefix + '/dynamic/{tail:.*}', context.dynamic_content_provider.get_handler)
            app.router.add_route('POST', prefix + '/dynamic/{tail:.*}', context.dynamic_content_provider.post_handler)
        if context.web_socket_provider is not None:
            app.router.add_route('GET', prefix + '/ws', context.web_socket_provider.handler)

    def finalize(self):
        if self.verbose:
            print("finalizing", self)
        if self.task is not None:
            print("cancelling server task")
            self.task.cancel()
        self._context_ref = None

class BaseProvider(GzComponentSuperclass):

    NOT_FOUND = "You can't get there from here"

    async def handler(self, request):
        return web.StreamResponse(status=404, reason=self.NOT_FOUND)

    async def get_handler(self, request):
        return self.handler(request)

    async def post_handler(self, request):
        return self.handler(request)


TEST_HTML = """
<!DOCTYPE html>
<html>
    <head>
        <title>WebSocket demo</title>
    </head>
    <body>
        <h1>Websocket test.</h1>
        <script>
            debugger;
            //var ws = new WebSocket("ws://127.0.0.1:8080/ws");
            var ws = new WebSocket("ws://127.0.0.1:8080/gizmo/ws?test=yes");
            var messages = document.createElement('ul');
            ws.onmessage = function (event) {
                var messages = document.getElementsByTagName('ul')[0],
                    message = document.createElement('li'),
                    content = document.createTextNode(event.data);
                message.appendChild(content);
                messages.appendChild(message);
            };
            document.body.appendChild(messages);
            ws.onopen = function(event) {
                ws.send("Hello from javascript!")
                ws.send("Now closing...");
                ws.send("close");
            }
        </script>
    </body>
</html>
""".replace("8080", str(DEFAULT_PORT))

class TestStaticProvider(BaseProvider):

    verbose = True

    async def get_handler(self, request):
        if self.verbose:
            print ("handling http", request)
        return web.Response(body=TEST_HTML, content_type="text/html")

class StaticFolderProvider(BaseProvider):

    verbose = True

    def __init__(self, url_path_prefix):
        self.url_prefix = url_path_prefix
        self.url_to_folder = {}

    def add_responder(self, path_fragment, responder):
        full_prefix = self.url_prefix + "/" + path_fragment
        print("adding responder for", full_prefix)
        self.url_to_folder[full_prefix] = responder

    def add_folder(self, path_fragment, folder_path):
        responder = FolderResponder(folder_path)
        return self.add_responder(path_fragment, responder)

    async def get_handler(self, request):
        print ("handling http", request)
        path = request.path
        print ("looking for path", path)
        # kiss for now
        path_match = ""
        path_responder = self.url_to_folder.get("")
        for (rpath, responder) in self.url_to_folder.items():
            print("testing", rpath)
            match = path.startswith(rpath)
            if match and ((path_responder is None) or (len(rpath) > len(path_match))):
                print("new longest match", rpath)
                path_match = rpath
                path_responder = responder
        if path_responder is None:
            print("no match found")
            raise aiohttp.web.HTTPNotFound(reason="no match: "+path)
        suffix = path[len(path_match):]
        info = path_responder.get_body(suffix)
        if info is None:
            print("file not found by responder")
            raise aiohttp.web.HTTPNotFound(reason="file not found: "+suffix)
        (body, content_type, encoding) = info   # encoding not used? xxxx
        if content_type is None:
            content_type = "text/plain" # xxxx ???
        return web.Response(body=body, content_type=content_type)

class FolderResponder:

    def __init__(self, folder_path):
        self.folder_path = folder_path

    def get_body(self, suffix):
        full_path = os.path.join(self.folder_path, suffix)
        (content_type, encoding) = mimetypes.guess_type(full_path)
        print("trying to read", full_path, content_type, encoding)
        if not os.path.isfile(full_path):
            return None  # no folder support (yet)
        try:
            f = open(full_path, "rb")
        except FileNotFoundError:
            return None
        body = f.read()
        f.close()
        return (body, content_type, encoding)

class TestWebSocketProvider(BaseProvider):

    verbose = True

    async def handler(self, request):
        print ("handling websocket", request)
        ws = web.WebSocketResponse()
        #keeper.ws_response = ws
        await ws.prepare(request)
        print ("ws attached", ws)
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.text:
                if msg.data == 'close':
                    print("closing", ws)
                    await ws.close()
                else:
                    print("answering", ws, msg.data)
                    await ws.send_str(msg.data + '/answer')
            elif msg.tp == aiohttp.MsgType.error:
                print(ws, 'ws connection closed with exception %s' %
                    ws.exception())
        print('websocket connection closed', ws)
        return ws

class WebSocketDelegatorProvider(BaseProvider):
    """
    Delegate web socket handling to a handler created by a factory.
    """

    def __init__(self, handlerFactory):
        self.handlerFactory = handlerFactory

    async def handler(self, request):
        print ("handling websocket", request)
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        print ("ws attached", ws)
        request_handler = await self.handlerFactory(request, ws)
        async for msg in ws:
            ty = msg.type
            if ty == aiohttp.WSMsgType.text:
                await request_handler.handle_text(msg)
            elif ty == aiohttp.WSMsgType.binary:
                await request_handler.handle_binary(msg)
            elif ty == aiohttp.MsgType.error:
                print(ws, 'ws connection closed with exception %s' %
                    ws.exception())
        return ws

class BaseWebSocketHandler:

    def __init__(self, request, ws):
        self.request = request
        self.ws = ws

    def handle_text(self, msg):
        raise NotImplementedError("no text handler defined. " + msg)

    def handle_binary(self, msg):
        raise NotImplementedError("no binary handler defined." + msg)

FINISHED_UNICODE = "F"
CONTINUE_UNICODE = "C"

class BadIndicator(ValueError):
    "Unknown indicator"

class WebSocketPacketHandlerFactory:

    def __init__(self, packet_handler, packet_limit=None):
        self.packet_handler = packet_handler
        self.packet_limit = packet_limit

    async def __call__(self, request, ws):
        result = WebSocketPacketHandler(request, ws)
        await result.set_packet_handler(self.packet_handler, self.packet_limit)
        return result

class WebSocketPacketHandler(BaseWebSocketHandler):
    """
    Send and receive unicode segmented messages.
    """

    packet_limit = 1000000
    collector = None

    async def set_packet_handler(self, packet_handler, packet_limit=None):
        if packet_limit is not None:
            self.packet_limit = packet_limit
        self.packet_handler = packet_handler
        packet_handler.send_to(self)
        await packet_handler.start_up()
        self.collector = []

    async def handle_text(self, msg):
        collector = self.collector
        data = msg.data
        indicator = data[0:1]
        payload = data[1:]
        if indicator == CONTINUE_UNICODE:
            collector.append(payload)
        elif indicator == FINISHED_UNICODE:
            self.collector = []
            collector.append(payload)
            packet = "".join(collector)
            proceed = await self.packet_handler.handle_unicode_packet(packet)
            if not proceed:
                # shut down the web socket
                await self.ws.close()
        else:
            raise BadIndicator("unknown packet indicator:" + repr(data[:10]))

    async def send_unicode(self, packet_unicode):
        print("sending unicode", repr(packet_unicode))
        ln = len(packet_unicode)
        limit = self.packet_limit
        ws = self.ws
        for start in range(0, ln, limit):
            end = start + limit
            chunk = packet_unicode[start: end]
            final = (end >= ln)
            if final:
                data = FINISHED_UNICODE + chunk
            else:
                data = CONTINUE_UNICODE + chunk
            print ("sending data", repr(data))
            await ws.send_str(data)
            

class BasePacketHandler:

    send_to_socket = None

    def send_to(self, ws):
        self.send_to_socket = ws

### TEST STUFF

class TestLogPacketHandler(BasePacketHandler):

    def __init__(self):
        self.packets = []

    def handle_unicode_packet(self, packet):
        print ("got unicode packet", packet)
        self.packets.append(packet)

def basicTestContext():
    # no dynamic
    d = BaseProvider()
    s = TestStaticProvider()
    w = TestWebSocketProvider()
    g = BaseProvider()
    sv = GzServer()
    context = GzContext(
        server=sv,
        static_content_provider=s,
        dynamic_content_provider=d,
        web_socket_provider=w,
        gizmo_collection=g,
    )
    return context

def test_main():
    context = basicTestContext()
    context.run_standalone()
    return context

def test_jupyter():
    print("making test context")
    context = basicTestContext()
    context.verbose = True
    print("running in jupyter")
    context.run_in_task()
    return context

if __name__ == "__main__":
    test_main()
