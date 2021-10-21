

import unittest

import numpy as np
import json
import asyncio
import aiohttp

from H5Gizmos.python.gizmo_server import (
    GzServer,
    WebInterface,
    RequestUrlInfo,
    DEFAULT_PORT,
)

class FakeApp:

    def __init__(self):
        self.router = FakeRouter()
        self.shut = False
        self.clean = False

    async def shutdown(self):
        self.shut = True

    async def cleanup(self):
        self.clean = True


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
        self.assertEqual(len(S.app.router.routes), 3)

class TestMockServerAsync(unittest.IsolatedAsyncioTestCase):
    
    async def test_mock_server_async(self):
        S = GzServer()
        S.verbose = True
        task = S.run_in_task(app_factory=FakeApp, async_run=trivial_fake_async_run)
        await task
        self.assertIsInstance(S.app, FakeApp)
        self.assertEqual(len(S.app.router.routes), 3)
        assert not S.app.shut
        assert not S.app.clean
        await S.shutdown()
        assert S.app.shut
        assert S.app.clean

async def trivial_fake_async_run_cancel(*args, **kwargs):
    print("raising cancel error")
    raise asyncio.CancelledError

class TestMockServerAsyncCancel(unittest.IsolatedAsyncioTestCase):
    
    async def test_mock_server_async(self):
        S = GzServer()
        S.verbose = True
        task = S.run_in_task(app_factory=FakeApp, async_run=trivial_fake_async_run_cancel)
        await task
        self.assertIsInstance(S.app, FakeApp)
        self.assertEqual(len(S.app.router.routes), 3)
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
                #print ("temp file at", name)
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

def std_url(path):
    if path.startswith("/"):
        path = path[1:]
    return "http://localhost:%s/%s" % (DEFAULT_PORT, path)

class TestHTTPdelivery(StartStop):

    async def test_http_delivery(self, delay=0.1):
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
        path = handler.method_path()
        url = std_url(path)
        print("   ... getting url", repr(url))
        #req = MockFileRequest(handler.url_path)
        #await S.handle_http_get(req, interface=interface)
        task = None
        try:
            task = await self.startup(S, delay)
            info = await self.get_url_response(url)
        finally:
            if task is not None:
                await self.shutdown(S, task)
        self.assertEqual(get_file_bytes.delivered, True)
        self.assertEqual(info.status, 200)
        self.assertEqual(info.text.encode("utf-8"), file_bytes_getter.content)

class TestHTTP404(StartStop):

    async def test_http_delivery(self, delay=0.1):
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
        url = std_url(path)
        print("   ... getting url", repr(url))
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
