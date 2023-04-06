
# Requires python 3.8
# Run from setup folder:
# nosetests --with-coverage --cover-html --cover-package=H5Gizmos --cover-erase --cover-inclusive

import unittest

import numpy as np
import json
import asyncio
import aiohttp
from aiohttp import web

#from H5Gizmos.python import H5Gizmos
from H5Gizmos.python import gz_parent_protocol as H5Gizmos

from H5Gizmos.python.gizmo_server import (
    GzServer,
    WebInterface,
    RequestUrlInfo,
    DEFAULT_PORT,
    GizmoPipelineSocketHandler,
    gizmo_task_server,
)

class FakeApp:

    def __init__(self, *args, **kwargs):
        self.router = FakeRouter()
        self.shut = False
        self.clean = False
        self.on_shutdown = []

    async def shutdown(self):
        self.shut = True

    async def cleanup(self):
        self.clean = True

route_count = 4

class FakeRouter:

    def __init__(self):
        self.routes = []

    def add_route(self, *args):
        self.routes.append(args)

def trivial_fake_sync_run(*args, **kwargs):
    return (args, kwargs)

async def trivial_fake_async_run(*args, **kwargs):
    return (args, kwargs)

class TestServerSync(unittest.TestCase):

    def test_mocked_server_standalone(self):
        S = GzServer()
        S.verbose = True
        info = S.run_standalone(app_factory=FakeApp, sync_run=trivial_fake_sync_run)
        self.assertIsInstance(S.app, FakeApp)
        self.assertEqual(len(S.app.router.routes), route_count)

class TestMockServerAsync(unittest.IsolatedAsyncioTestCase):
    
    async def test_mock_server_async(self):
        S = GzServer()
        S.verbose = True
        task = S.run_in_task(app_factory=FakeApp, async_run=trivial_fake_async_run)
        await task
        self.assertIsInstance(S.app, FakeApp)
        self.assertEqual(len(S.app.router.routes), route_count)
        assert not S.app.shut
        assert not S.app.clean
        await S.shutdown()
        assert S.app.shut
        assert S.app.clean

async def trivial_fake_async_run_cancel(*args, **kwargs):
    #pr("raising cancel error")
    raise asyncio.CancelledError

class TestMockServerAsyncCancel(unittest.IsolatedAsyncioTestCase):
    
    async def test_mock_server_async(self):
        S = GzServer()
        S.verbose = True
        task = S.run_in_task(app_factory=FakeApp, async_run=trivial_fake_async_run_cancel)
        await task
        self.assertIsInstance(S.app, FakeApp)
        self.assertEqual(len(S.app.router.routes), route_count)
        assert not S.app.shut
        assert not S.app.clean
        await S.shutdown()
        assert S.app.shut
        assert S.app.clean
        assert S.cancelled

class MockFileInterface:

    body = content_type = None
    exists_result = True

    def respond(self, body, content_type):
        self.body = body
        self.content_type = content_type

    def stream_respond(self, *args, **kwargs):
        raise MockFileDoesntExist(repr((args, kwargs)))

    def file_exists(self, path):
        self.path = path
        return self.exists_result

    def get_file_bytes(self, path=None):
        self.path = path
        return b'bytes'

class MockFileDoesntExist(ValueError):
    "fake exception"

class MockFileRequest:

    def __init__(self, path):
        self.path = path


class TestMockFile(unittest.IsolatedAsyncioTestCase):

    async def test_mock_file(self):
        interface = MockFileInterface()
        S = GzServer()
        mgr = S.get_new_manager()
        handler = mgr.add_file("/var/index.html", interface=interface)
        path = handler.method_path()
        #self.assertEqual(path, None)
        req = MockFileRequest(path)
        await S.handle_http_get(req, interface=interface)
        self.assertEqual(interface.body, interface.get_file_bytes())
        self.assertEqual(interface.content_type, 'text/html')

class TestMockFile2(unittest.IsolatedAsyncioTestCase):

    async def test_mock_no_file(self):
        interface = MockFileInterface()
        S = GzServer()
        mgr = S.get_new_manager()
        handler = mgr.add_file("/var/index.html", interface=interface)
        # must be after handler
        interface.exists_result = False
        #self.assertEqual(handler.url_path, None)
        path = handler.method_path()
        req = MockFileRequest(path)
        with self.assertRaises(MockFileDoesntExist):
            await S.handle_http_post(req, interface=interface)

class TestMockFile3(unittest.IsolatedAsyncioTestCase):

    async def test_mock_bad_method(self):
        interface = MockFileInterface()
        S = GzServer()
        mgr = S.get_new_manager()
        handler = mgr.add_file("/var/index.html", interface=interface)
        #self.assertEqual(handler.url_path, None)
        path = handler.method_path()
        req = MockFileRequest(path)
        info = RequestUrlInfo(req, S.prefix)
        with self.assertRaises(AssertionError):
            await mgr.handle("Gulp", info, req, interface=interface)

class TestFileServices(unittest.TestCase):

    def test_mock_no_handler(self):
        interface = MockFileInterface()
        interface.exists_result = False
        S = GzServer()
        mgr = S.get_new_manager()
        with self.assertRaises(AssertionError):
            handler = mgr.add_file("/var/index.html", interface=interface)

    def test_file_interface(self):
        import tempfile
        import os
        interface = WebInterface()
        with tempfile.NamedTemporaryFile(delete=False) as tf:
            name = tf.name
            try:
                ##pr ("temp file at", name)
                content = b"bytes"
                tf.write(content)
                tf.close()
                self.assertTrue(interface.file_exists(name))
                byt = interface.get_file_bytes(name)
                self.assertEqual(byt, content)
            finally:
                os.unlink(name)
            self.assertFalse(interface.file_exists(name))


class ResponseInfo:

    def __init__(self, status, text):
        self.status = status
        self.text = text


class StartStop(unittest.IsolatedAsyncioTestCase):

    async def startup(self, server, delay):
        #task = asyncio.sleep(1) # testing debug only
        task = server.run_in_task()
        await asyncio.sleep(delay)
        return task

    async def shutdown(self, server, task):
        #context.server.finalize()
        #context.finalize()
        await server.shutdown()
        #task2 = schedule_task(shutdown())
        #await task2
        await task
        assert server.stopped == True

    async def get_url_response(self, url):
        # https://www.twilio.com/blog/asynchronous-http-requests-in-python-with-aiohttp
        # https://docs.aiohttp.org/en/stable/client_reference.html
        async with aiohttp.ClientSession() as client:
            async with client.get(url) as resp:
                status = resp.status
                text = await resp.text()
                return ResponseInfo(status, text)

class TestStartStop(StartStop):

    async def test_start_stop(self, delay=0.1):
        server = GzServer()
        task = await self.startup(server, delay)
        await self.shutdown(server, task)

def std_url(path, protocol="http", server=None):
    if path.startswith("/"):
        path = path[1:]
    port = DEFAULT_PORT
    if server is not None:
        port = server.port
    return "%s://localhost:%s/%s" % (protocol, port, path)

class TestHTTPdelivery(StartStop):

    async def test_http_delivery(self, delay=0.1):
        class file_bytes_getter:
            content = b"abcdefghijklmnop" * 10
            def __init__(self):
                self.delivered = False
            def __call__(self, path):
                #print("Now delivering content.")
                self.delivered = True
                return self.content
        get_file_bytes = file_bytes_getter()
        def file_exists(path):
            return True
        interface = WebInterface(get_file_bytes=get_file_bytes, file_exists=file_exists)
        S = GzServer(interface=interface)
        mgr = S.get_new_manager()
        handler = mgr.add_file("/var/index.html", interface=interface)
        #self.assertEqual(handler.url_path, None)
        path = handler.method_path()
        url = std_url(path, server=S)
        #pr("   ... getting url", repr(url))
        #req = MockFileRequest(handler.url_path)
        #await S.handle_http_get(req, interface=interface)
        task = None
        try:
            #print("Now starting task")
            task = await self.startup(S, delay)
            #print("Started", task)
            #print("Now getting URL response", url)
            info = await self.get_url_response(url)
            #print("Got response", repr(info.text))
        finally:
            if task is not None:
                #print("shutting down task")
                await self.shutdown(S, task)
                #print("task is shutdown", task)
        self.assertEqual(get_file_bytes.delivered, True)
        self.assertEqual(info.status, 200)
        self.assertEqual(info.text.encode("utf-8"), file_bytes_getter.content)

class TestHTTP404(StartStop):

    async def test_http_404(self, delay=0.1):
        class file_bytes_getter:
            content = b"abcdef"
            def __init__(self):
                self.delivered = False
            def __call__(self, path):
                self.delivered = True
                return self.content
        get_file_bytes = file_bytes_getter()
        def file_exists(path):
            return True
        interface = WebInterface(get_file_bytes=get_file_bytes, file_exists=file_exists)
        S = GzServer(interface=interface)
        mgr = S.get_new_manager()
        handler = mgr.add_file("/var/index.html", interface=interface)
        #self.assertEqual(handler.url_path, None)
        path = "/no/such/path"
        url = std_url(path, server=S)
        #pr("   ... getting url", repr(url))
        #req = MockFileRequest(handler.url_path)
        #await S.handle_http_get(req, interface=interface)
        task = None
        try:
            task = await self.startup(S, delay)
            info = await self.get_url_response(url)
        finally:
            if task is not None:
                await self.shutdown(S, task)
        self.assertEqual(get_file_bytes.delivered, False)
        self.assertEqual(info.status, 404)


class TestNoFileForWebSocket(StartStop):

    async def test_ws_no_file(self, delay=0.1):
        class file_bytes_getter:
            content = b"abcdef"
            def __init__(self):
                self.delivered = False
            def __call__(self, path):
                self.delivered = True
                return self.content
        get_file_bytes = file_bytes_getter()
        def file_exists(path):
            return True
        interface = WebInterface(get_file_bytes=get_file_bytes, file_exists=file_exists)
        S = GzServer(interface=interface)
        mgr = S.get_new_manager()
        handler = mgr.add_file("/var/index.html", interface=interface)
        #self.assertEqual(handler.url_path, None)
        path = handler.method_path("ws")
        url = std_url(path, server=S)
        #pr("   ... getting url", repr(url))
        #req = MockFileRequest(handler.url_path)
        #await S.handle_http_get(req, interface=interface)
        task = None
        try:
            task = await self.startup(S, delay)
            info = await self.get_url_response(url)
        finally:
            if task is not None:
                await self.shutdown(S, task)
        self.assertEqual(get_file_bytes.delivered, False)
        self.assertEqual(info.status, 404)

class SillyWebSocketHandler:

    def __init__(self):
        self.data = None

    async def handle(self, info, request, interface):
        #pr("**** handler started")
        ws = web.WebSocketResponse()
        self.ws = ws
        await ws.prepare(request)
        #pr ("XXXX ws attached", ws)
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.text:
                if msg.data == 'close':
                    #pr("closing", ws)
                    await ws.close()
                else:
                    data = msg.data
                    self.data = data
                    #pr("answering", ws, data)
                    await ws.send_str(msg.data + '/answer')
            elif msg.tp == aiohttp.MsgType.error:
                #pr(ws, 'ws connection closed with exception %s' %
                #    ws.exception())
                pass
        self.ws = None
        #pr('websocket connection closed', ws)
        return ws


def ws_url(mgr, server=None):
    mprefix = "ws"
    prefix = mgr.prefix
    identifier = mgr.identifier
    components = ["", prefix, mprefix, identifier]
    path = "/".join(components)
    url = std_url(path, server=server)
    return url


class TestSillySocketHandler(StartStop):

    ws = None

    async def test_silly_handler(self):
        S = GzServer()
        handler = SillyWebSocketHandler()
        mgr = S.get_new_manager(websocket_handler=handler)
        url = ws_url(mgr, server=S)
        # https://docs.aiohttp.org/en/v0.18.3/client_websockets.html
        delay = 0.1
        session = aiohttp.ClientSession()
        task = None
        reply = None
        try:
            task = await self.startup(S, delay)
            ws = await session.ws_connect(url)
            self.ws = ws
            #ws.send_str(msg.data + 'hello')
            msgtxt = "hello"
            #pr ("sending", repr(msgtxt), "to", ws)
            await ws.send_str("hello")
            #pr("awaiting reply")
            reply = await ws.receive()
            data = reply.data
            self.reply = data
            #pr("replied", repr(data), "now closing")
            await ws.close()
        finally:
            if task is not None:
                await self.shutdown(S, task)
        self.ws = None
        self.assertNotEqual(reply, None)


class TestBasicSocketSendPipeline(StartStop):

    async def test_websocket_send_pipeline(self):
        from H5Gizmos.python.test.test_H5Gizmos import exec_msg, _lit, FINISHED_UNICODE
        import json
        S = GzServer()
        G = H5Gizmos.Gizmo()
        handler = GizmoPipelineSocketHandler(G)
        mgr = S.get_new_manager(websocket_handler=handler)
        url = ws_url(mgr, server=S)
        # Make a message to send to JS
        json_ob = [1, "json", None]
        json_msg = exec_msg(_lit(json_ob))
        delay = 0.1
        session = aiohttp.ClientSession()
        task = None
        received = None
        data = None
        try:
            task = await self.startup(S, delay)
            ws = await session.ws_connect(url)
            G._send(json_msg)
            #pr("awaiting receive")
            received = await ws.receive()
            data = received.data
            #self.reply = data
            ##pr("replied", repr(data), "now closing")
            await ws.close()
        finally:
            if task is not None:
                await self.shutdown(S, task)
        self.assertNotEqual(received, None)
        self.assertNotEqual(data, None)
        self.assertEqual(data[0], FINISHED_UNICODE)
        json_str = data[1:]
        json_ob_rcv = json.loads(json_str)
        self.assertEqual(json_ob_rcv, json_msg)

class TestBasicSocketCallbackPipeline(StartStop):

    async def test_websocket_callback_pipeline(self):
        from H5Gizmos.python.test.test_H5Gizmos import GZ, FINISHED_UNICODE
        import json
        S = GzServer()
        G = H5Gizmos.Gizmo()
        data = []
        def callback_function(*args):
            data.append(args)
        oid = G._register_callback(callback_function)
        handler = GizmoPipelineSocketHandler(G)
        mgr = S.get_new_manager(websocket_handler=handler)
        url = ws_url(mgr, server=S)
        # Make a message to send from JS
        arguments = ["this", "argument", "list"]
        json_msg = [GZ.CALLBACK, oid, arguments]
        msg_str = FINISHED_UNICODE + json.dumps(json_msg)
        delay = 0.1
        session = aiohttp.ClientSession()
        task = None
        received = None
        try:
            #pr("starting task")
            task = await self.startup(S, delay)
            ws = await session.ws_connect(url)
            #pr('send_str', msg_str)
            await ws.send_str(msg_str)
            #pr("closing ws")
            await ws.close()
            for i in range(100):
                # wait for message to arrive
                if len(data) > 0:
                    break
                #pr ("sleeping waiting for callback data", i)
                asyncio.sleep(delay)
        finally:
            if task is not None:
                await self.shutdown(S, task)
        self.assertEqual(data, [tuple(arguments)])


class TestBasicSocketGetPipeline(StartStop):

    async def test_websocket_get_pipeline(self):
        #pr("pipeline get test")
        from H5Gizmos.python.test.test_H5Gizmos import (
            GZ, GizmoLiteral, JavascriptEvalException, FINISHED_UNICODE)
        import json
        S = GzServer()
        G = H5Gizmos.Gizmo()
        exception_data = []
        def on_exception(payload):
            exception_data.append(payload)
        G._on_exception = on_exception
        json_ob = [1, "two", 3]
        lit = GizmoLiteral(json_ob, G)
        got_results = []
        async def get_lit():
            #pr ("attempting to get lit")
            result = await lit._get()
            got_results.append(result)
        (oid, future) = lit._register_get_future()
        handler = GizmoPipelineSocketHandler(G)
        mgr = S.get_new_manager(websocket_handler=handler)
        G._set_manager(S, mgr)
        test_url = mgr.local_url(
            for_gizmo=G,
            method="ws",
            protocol="http",
            server="x.y.z",
            port=9090,
            prefix="test_prefix",
            identifier="id000",
            filename="index.html"
        )
        self.assertEqual(test_url, 'http://x.y.z:9090/test_prefix/ws/id000/index.html')
        url = ws_url(mgr, server=S)
        delay = 0.1
        session = aiohttp.ClientSession()
        task = None
        request = None
        response = [GZ.GET, oid, json_ob]
        response_str = FINISHED_UNICODE + json.dumps(response)
        try:
            #pr("starting task")
            task = await self.startup(S, delay)
            get_task = H5Gizmos.schedule_task(get_lit())
            ws = await session.ws_connect(url)
            #pr("awaiting request")
            request = await ws.receive()
            #pr('send_str', response_str)
            await ws.send_str(response_str)
            #pr("closing ws")
            await ws.close()
            await get_task
        finally:
            if task is not None:
                await self.shutdown(S, task)
        self.assertNotEqual(request, None)
        self.assertEqual(got_results, [json_ob])
        self.assertEqual(exception_data, [])

class TestBasicSocketErrorPipeline(StartStop):

    async def test_websocket_error_pipeline(self):
        #pr("pipeline error test")
        from H5Gizmos.python.test.test_H5Gizmos import (
            GZ, GizmoLiteral, JavascriptEvalException, FINISHED_UNICODE)
        import json
        S = GzServer()
        G = H5Gizmos.Gizmo()
        exception_data = []
        def on_exception(payload):
            exception_data.append(payload)
        G._on_exception = on_exception
        json_ob = [1, "two", 3]
        lit = GizmoLiteral(json_ob, G)
        got_results = []
        async def get_lit():
            with self.assertRaises(JavascriptEvalException):
                #pr ("attempting to get lit")
                result = await lit._get()
                got_results.append(result)
        (oid, future) = lit._register_get_future()
        handler = GizmoPipelineSocketHandler(G)
        mgr = S.get_new_manager(websocket_handler=handler)
        url = ws_url(mgr, server=S)
        delay = 0.1
        session = aiohttp.ClientSession()
        task = None
        request = None
        response = [GZ.EXCEPTION, "Fake exception", oid]
        response_str = FINISHED_UNICODE + json.dumps(response)
        try:
            #pr("starting task")
            task = await self.startup(S, delay)
            get_task = H5Gizmos.schedule_task(get_lit())
            ws = await session.ws_connect(url)
            #pr("awaiting request")
            request = await ws.receive()
            #pr('send_str', response_str)
            await ws.send_str(response_str)
            #pr("closing ws")
            await ws.close()
            await get_task
        finally:
            if task is not None:
                await self.shutdown(S, task)
        self.assertNotEqual(request, None)
        self.assertEqual(got_results, [])
        self.assertNotEqual(exception_data, [])


class TestNoWebSocketHandler(StartStop):

    async def test_no_handler(self):
        S = GzServer()
        mgr = S.get_new_manager()
        mprefix = "ws"
        prefix = mgr.prefix
        identifier = mgr.identifier
        components = ["", prefix, mprefix, identifier]
        path = "/".join(components)
        url = std_url(path, server=S)
        # https://docs.aiohttp.org/en/v0.18.3/client_websockets.html
        delay = 0.1
        session = aiohttp.ClientSession()
        task = None
        try:
            task = await self.startup(S, delay)
            with self.assertRaises(Exception):
                ws = await session.ws_connect(url)
        finally:
            if task is not None:
                await self.shutdown(S, task)
        #self.assertEqual(1, 0)

""" xxxx fix this...
class TestStaticHelloWorldGizmo(unittest.IsolatedAsyncioTestCase):

    async def x_test_hello_world(self, delay=0.01):
        #task = asyncio.sleep(1) # testing debug only
        S = gizmo_task_server()
        try:
            await asyncio.sleep(delay)
            title = "GIZMO123XYZ"
            message = "Hello world!"
            G = S.gizmo(title=title)
            G._initial_reference("window")
            G._initial_reference("doc", "window.document")
            with self.assertRaises(NameError):
                G._initial_reference("doc", "document")
            G._insert_html(message)
            style_text = "// nothing."
            G._embedded_css(style_text)
            css_url = "http:/x.y.z/aaa.css"
            G._remote_css(css_url)
            js_url = "http:/a.b.c/x.js"
            G._remote_js(js_url)
            script_text = "initialize();"
            G._embedded_script(script_text)
            #self.assertEqual(G._entry_url, None)
            url = G._entry_url
            self.assertIsNotNone(url)
            # get the url...
            response = None
            text = None
            async with aiohttp.ClientSession() as client:
                async with client.get(url) as resp:
                    status = resp.status
                    text = await resp.text()
                    response = ResponseInfo(status, text)
            #print(text)
            self.assertNotEqual(response, None)
            self.assertIn(title, text)
            self.assertIn(message, text)
            self.assertIn(style_text, text)
            self.assertIn(css_url, text)
            self.assertIn(js_url, text)
            self.assertIn(script_text, text)
            self.assertEqual(status, 200)
            #self.assertEqual(1,0)
        finally:
            await S.shutdown()
            """
