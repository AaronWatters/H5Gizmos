

import unittest

import numpy as np
import json
import asyncio

from H5Gizmos.python.gizmo_server import (
    GzServer,
    WebInterface,
    RequestUrlInfo,
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

    async def respond(self, body, content_type):
        self.body = body
        self.content_type = content_type

    async def stream_respond(self, *args, **kwargs):
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
        #self.assertEqual(handler.url_path, None)
        req = MockFileRequest(handler.url_path)
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
        req = MockFileRequest(handler.url_path)
        with self.assertRaises(MockFileDoesntExist):
            await S.handle_http_post(req, interface=interface)

class TestMockFile3(unittest.IsolatedAsyncioTestCase):

    async def test_mock_bad_method(self):
        interface = MockFileInterface()
        S = GzServer()
        mgr = S.get_new_manager()
        handler = mgr.add_file("/var/index.html", interface=interface)
        #self.assertEqual(handler.url_path, None)
        req = MockFileRequest(handler.url_path)
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

