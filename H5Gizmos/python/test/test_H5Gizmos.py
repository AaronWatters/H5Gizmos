

# Requires python 3.8
# Run from setup folder:
# nosetests --with-coverage --cover-html --cover-package=H5Gizmos --cover-erase --cover-inclusive

import unittest

import numpy as np
import json

from H5Gizmos.python.gz_parent_protocol import (
    Gizmo, 
    GZ,
    GizmoLiteral,
    JavascriptEvalException,
    NoSuchCallback,
    GizmoLink,
    GizmoReference,
    CantConvertValue,
    NoRequestForOid,
    BadResponseFormat,
    GizmoPacker,
    FINISHED_UNICODE,
    CONTINUE_UNICODE,
    BadMessageIndicator,
    JsonCodec,
    GZPipeline,
    schedule_task,
    TooManyRequests,
    ValueConverter,
)

'''
class TestFails(unittest.TestCase):

    def test_fail(self):
        self.assertEqual(1, 0)
'''

def dummy_request(id="1234"):
    "fake web socket request interface to make tests work."
    class url:
        query = {Gizmo.RECONNECT_ID: id}
    class request:
        _rel_url = url
    return request

class GizmoWrapper:

    def __init__(self, default_depth=5):
        self.sent_data = []
        self.G = Gizmo(self.send, default_depth)

    def send(self, object):
        self.sent_data.append(object)

def _lit(json_ob):
    return [GZ.LITERAL, json_ob]

def _call(callable_cmd, args):
    return [GZ.CALL, callable_cmd, args]

def _ref(identity):
    return [GZ.REFERENCE, identity]

def _get(target_cmd, index_cmd):
    return [GZ.GET, target_cmd, index_cmd]

def _seq(cmds):
    return [GZ.SEQUENCE, cmds]

def _map(mapping):
    return [GZ.MAP, mapping]

def _callback(oid, to_depth):
    return [GZ.CALLBACK, oid, to_depth]

def _bytes(hex):
    return [GZ.BYTES, hex]

def get_msg(oid, cmd, to_depth):
    return [GZ.GET, oid, cmd, to_depth]

def exec_msg(cmd):
    return [GZ.EXEC, cmd]

def connect_msg(id, cmd):
    return [GZ.CONNECT, id, cmd]

def disconnect_msg(id):
    return [GZ.DISCONNECT, id]

class FakeWebSocketResponse:

    _prepared = False
    _sent = None
    _closed = False

    def __init__(self):
        ##p("init", self)
        #self._messages = messages
        #if messages:
        #    raise ValueError("please use append", messages)
        self._messages = []
        self._index = 0
        #p("init", self)

    def __repr__(self) -> str:
        return "resp" + repr([self._index, self._messages])

    def append(self, msg):
        #p("append", self, msg)
        self._messages.append(msg)

    def __aiter__(self):
        #p("in aiter", self)
        return self

    async def __anext__(self):
        #p("in anext", self)
        i = self._index
        self._index += 1
        msgs = self._messages
        if i >= len(msgs):
            #p("stopping", self)
            raise StopAsyncIteration
        result = msgs[i]
        #p("anext=", result)
        return result

    async def prepare(self, request):
        self._prepared = True
        self._request = request
        self._sent = []

    async def send_str(self, unicode_str):
        self._sent.append(unicode_str)

    async def drain(self, *arguments):
        pass # do nothing

class FakeWebSocketConnection:

    def __init__(self, messages_to_send):
        ws = FakeWebSocketResponse()
        self.ws = ws
        for message in messages_to_send:
            ws.append(message)

    def get_web_socket(self):
        return self.ws

class FakeWebSocketMessage:

    def __init__(self, typ, data):
        self.type = typ
        self.data = data

    def __repr__(self):
        return "msg" + repr((self.type, self.data))

def FakeWebSocketUnicodeMessages(unicode_strings, msg_type=GZPipeline.MSG_TYPE_TEXT):
    messages = []
    for ustr in unicode_strings:
        msg = FakeWebSocketMessage(msg_type, ustr)
        messages.append(msg)
    cnx = FakeWebSocketConnection(messages)
    return cnx

class TestGizmo(unittest.TestCase):

    def test_converts_None_in_dict(self):
        import numpy as np
        D = dict(key=None)
        converted = ValueConverter(D, None)
        assert converted.is_literal
        DC = converted.command._value
        self.assertEqual(DC, D)

    def test_converts_float32_in_dict(self):
        import numpy as np
        a = np.array([42.3], dtype=np.float32)
        D = dict(key=a[0])
        self.assertEqual(type(D["key"]), np.float32)
        converted = ValueConverter(D, None)
        assert converted.is_literal
        DC = converted.command._value
        self.assertEqual(type(DC["key"]), float)

    def test_converts_float32_in_list(self):
        import numpy as np
        a = np.array([42.3], dtype=np.float32)
        L = [a[0]]
        self.assertEqual(type(L[0]), np.float32)
        converted = ValueConverter(L, None)
        assert converted.is_literal
        LC = converted.command._value
        self.assertEqual(type(LC[0]), float)

    def test_calls_callback(self):
        data = []
        def callback_function(*args):
            data.append(args)
        GW = GizmoWrapper()
        G = GW.G
        oid = G._register_callback(callback_function)
        arguments = ["this", "argument", "list"]
        json_msg = [GZ.CALLBACK, oid, arguments]
        G._receive(json_msg)
        self.assertEqual(data, [tuple(arguments)])

    def test_no_such_callback(self):
        data = []
        def callback_function(*args):
            data.append(args)
        GW = GizmoWrapper()
        G = GW.G
        oid = G._register_callback(callback_function)
        oid = "nope:" + oid #  make an invalid oid
        arguments = ["this", "argument", "list"]
        json_msg = [GZ.CALLBACK, oid, arguments]
        with self.assertRaises(NoSuchCallback):
            G._receive(json_msg)
            self.assertEqual(data, [tuple(arguments)])

    def test_ref_attr_request(self):
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someObject", G)
        getatr = ref.attribute
        getatr._exec()
        expected = exec_msg(_get(_ref("someObject"), _lit("attribute")))
        self.assertEqual(GW.sent_data, [expected])

    def test_ref_item_request(self):
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someObject", G)
        getatr = ref["attribute"]
        getatr._exec()
        expected = exec_msg(_get(_ref("someObject"), _lit("attribute")))
        self.assertEqual(GW.sent_data, [expected])

    def test_ref_call_request(self):
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        call = ref("abc", 1)
        call._exec()
        expected = exec_msg(_call(_ref("someFunction"), [_lit("abc"), _lit(1)]))
        self.assertEqual(GW.sent_data, [expected])

    def test_ref_call_with_list_literal(self):
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        the_list = [1, "two"]
        call = ref("abc", the_list)
        call._exec()
        expected = exec_msg(_call(_ref("someFunction"), [_lit("abc"), _lit(the_list)]))
        self.assertEqual(GW.sent_data, [expected])

    def test_ref_call_with_dict_literal(self):
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        the_dict = {"hello": "world"}
        call = ref("abc", the_dict)
        call._exec()
        expected = exec_msg(_call(_ref("someFunction"), [_lit("abc"), _lit(the_dict)]))
        self.assertEqual(GW.sent_data, [expected])

    def test_ref_call_with_list_ref(self):
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        ref2 = GizmoReference("someObject", G)
        the_list = [1, ref2]
        the_list_cmd = _seq([_lit(1), _ref("someObject")])
        call = ref("abc", the_list)
        call._exec()
        expected = exec_msg(_call(_ref("someFunction"), [_lit("abc"), the_list_cmd]))
        self.assertEqual(GW.sent_data, [expected])

    def test_ref_call_with_dict_ref(self):
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        ref2 = GizmoReference("someObject", G)
        the_dict = {"hello": ref2}
        the_dict_cmd = _map({"hello": _ref("someObject")})
        call = ref("abc", the_dict)
        call._exec()
        expected = exec_msg(_call(_ref("someFunction"), [_lit("abc"), the_dict_cmd]))
        self.assertEqual(GW.sent_data, [expected])

    def test_execs_literal(self, detail=False):
        GW = GizmoWrapper()
        G = GW.G
        json_ob = [1, "json", None]
        lit = GizmoLiteral(json_ob, G)
        lit._exec(detail)
        expected = exec_msg(_lit(json_ob))
        self.assertEqual(GW.sent_data, [expected])

    def test_exec_literal_detail(self):
        return self.test_execs_literal(detail=True)

    def test_requests_connection(self):
        GW = GizmoWrapper()
        G = GW.G
        json_ob = [1, "json", None]
        lit = GizmoLiteral(json_ob, G)
        identifier = "window"
        cnx = lit._connect(identifier)
        expected = connect_msg(identifier, _lit(json_ob))
        self.assertEqual(GW.sent_data, [expected])

    def test_requests_connection_then_disconnect(self):
        GW = GizmoWrapper()
        G = GW.G
        json_ob = [1, "json", None]
        lit = GizmoLiteral(json_ob, G)
        identifier = "window"
        cnx = lit._connect(identifier)
        expected_connect = connect_msg(identifier, _lit(json_ob))
        cnx._disconnect()
        expected_disconnect = disconnect_msg(identifier)
        self.assertEqual(GW.sent_data, [expected_connect, expected_disconnect])

    def test_raises_not_implemented(self):
        X = GizmoLink()
        with self.assertRaises(NotImplementedError):
            X._command(to_depth=10)
        with self.assertRaises(NotImplementedError):
            X._get_id()

    def test_wraps_callable(self):
        def example_callable(x):
            return x + 1
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        call = ref("abc", example_callable)
        call._exec()
        #self.assertEqual(G._callable_to_oid, None)
        oid = G._callable_to_oid[example_callable]
        cb_json = _callback(oid, G._default_depth)
        expected = exec_msg(_call(_ref("someFunction"), [_lit("abc"), cb_json]))
        self.assertEqual(GW.sent_data, [expected])

    def test_converts_bytes(self):
        example_bytes = bytearray([1,2,3])
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        call = ref("abc", example_bytes)
        call._exec()
        hex = "010203"
        bytes_json = _bytes(hex)
        expected = exec_msg(_call(_ref("someFunction"), [_lit("abc"), bytes_json]))
        self.assertEqual(GW.sent_data, [expected])

    def test_converts_array(self):
        L = [100, 200, 300]
        example_array = np.array(L)
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        call = ref("abc", example_array)
        call._exec()
        hex = "010203"
        array_json = _lit(L)
        expected = exec_msg(_call(_ref("someFunction"), [_lit("abc"), array_json]))
        self.assertEqual(GW.sent_data, [expected])

    def test_unconvertible(self):
        cant_convert = np
        GW = GizmoWrapper()
        G = GW.G
        ref = GizmoReference("someFunction", G)
        with self.assertRaises(CantConvertValue):
            call = ref("abc", cant_convert)
            call._exec()
            expected = exec_msg(_call(_ref("someFunction"), [_lit("abc")]))
            self.assertEqual(GW.sent_data, [expected])

    def test_no_request_for_oid(self):
        GW = GizmoWrapper()
        G = GW.G
        oid = "oid123_doesn't exist"
        json_ob = [1, "two", 3]
        get_response = [GZ.GET, oid, json_ob]
        with self.assertRaises(NoRequestForOid):
             G._receive(get_response)

    def test_dont_receive_maps(self):
        GW = GizmoWrapper()
        G = GW.G
        get_response = {"a": "mapping"}
        with self.assertRaises(BadResponseFormat):
             G._receive(get_response)

    def test_bad_indicator(self):
        GW = GizmoWrapper()
        G = GW.G
        get_response = ["nonsense", "reply"]
        with self.assertRaises(BadResponseFormat):
             G._receive(get_response)

    '''BROKEN TEST CASES...
    def test_receive_chunks(self):
        packets_processed = []
        def process_packet(packet):
            packets_processed.append(packet)
        strings_sent = []
        def awaitable_sender(string):
            strings_sent.append(string)
        packet_limit = 1000000
        auto_flush = True
        P = GizmoPacker(process_packet, awaitable_sender, packet_limit, auto_flush)
        P.on_unicode_message(CONTINUE_UNICODE + "abc")
        P.on_unicode_message(FINISHED_UNICODE + "123")
        self.assertEqual(packets_processed,  ['abc123'])

    def test_rejects_bad_chunks(self):
        packets_processed = []
        def process_packet(packet):
            packets_processed.append(packet)
        strings_sent = []
        def awaitable_sender(string):
            strings_sent.append(string)
        packet_limit = 1000000
        auto_flush = True
        P = GizmoPacker(process_packet, awaitable_sender, packet_limit, auto_flush)
        with self.assertRaises(BadMessageIndicator):
            P.on_unicode_message("*" + "abc")
        self.assertEqual(packets_processed,  [])'''

    def test_processes_json_string(self):
        processed_json = []
        def process_json(json_ob):
            processed_json.append(json_ob)
        sent_unicode = []
        def send_unicode(x):
            sent_unicode.append(x)
        errors = []
        def on_error(msg):
            errors.append(msg)
        codec = JsonCodec(process_json, send_unicode, on_error)
        expected = ["this", 1, "json"]
        jstring = '["this", 1, "json"]'
        codec.receive_unicode(jstring)
        self.assertEqual(processed_json, [expected])

    def test_rejects_bad_json_string(self):
        processed_json = []
        def process_json(json_ob):
            processed_json.append(json_ob)
        sent_unicode = []
        def send_unicode(x):
            sent_unicode.append(x)
        errors = []
        def on_error(msg):
            errors.append(msg)
        codec = JsonCodec(process_json, send_unicode, on_error)
        jstring = '["this", 1, "json]'
        with self.assertRaises(Exception):
            codec.receive_unicode(jstring)
        self.assertEqual(len(errors), 1)

    def test_encodes_json_object(self):
        processed_json = []
        def process_json(json_ob):
            processed_json.append(json_ob)
        sent_unicode = []
        def send_unicode(x):
            sent_unicode.append(x)
        errors = []
        def on_error(msg):
            errors.append(msg)
        codec = JsonCodec(process_json, send_unicode, on_error)
        json_ob = ["this", 1, "json"]
        codec.send_json(json_ob)
        self.assertEqual(len(sent_unicode), 1)
        [ustr] = sent_unicode
        parsed = json.loads(ustr)
        self.assertEqual(parsed, json_ob)

    def test_rejects_bad_json_object(self):
        processed_json = []
        def process_json(json_ob):
            processed_json.append(json_ob)
        sent_unicode = []
        def send_unicode(x):
            sent_unicode.append(x)
        errors = []
        def on_error(msg):
            errors.append(msg)
        codec = JsonCodec(process_json, send_unicode, on_error)
        json_ob = ["this", 1, "json", json]
        with self.assertRaises(Exception):
            codec.send_json(json_ob)
        self.assertEqual(len(errors), 1)

class TestGizmoAsync(unittest.IsolatedAsyncioTestCase):

    async def test_resolves_get(self):
        GW = GizmoWrapper()
        G = GW.G
        json_ob = [1, "two", 3]
        lit = GizmoLiteral(json_ob, G)
        to_depth = 5
        # pass in the future so we can resolve it in the test case...
        (oid, future) = G._register_future()
        awaitable = lit._get(to_depth, oid=oid, future=future)
        # emulate a resolving send from JS side
        get_response = [GZ.GET, oid, json_ob]
        G._receive(get_response)
        # future should be resolved
        self.assertTrue(future.done())
        result = await awaitable
        self.assertEqual(result, json_ob)

    async def test_get_exception(self):
        GW = GizmoWrapper()
        G = GW.G
        exception_data = []
        def on_exception(payload):
            exception_data.append(payload)
        G._on_exception = on_exception
        json_ob = [1, "two", 3]
        lit = GizmoLiteral(json_ob, G)
        to_depth = 5
        # pass in the future so we can resolve it in the test case...
        (oid, future) = G._register_future()
        awaitable = lit._get(to_depth, oid=oid, future=future)
        # emulate an exception from JS side
        get_response = [GZ.EXCEPTION, "Fake exception", oid]
        G._receive(get_response)
        # future should be resolved
        self.assertTrue(future.done())
        # awaitable should raise an error
        with self.assertRaises(JavascriptEvalException):
            result = await awaitable
            self.assertEqual(result, json_ob)
        self.assertEqual(len(exception_data), 1)
        self.assertEqual(exception_data[0][0], "Fake exception")

    async def test_allocates_future_in_get(self):
        # code coverage hack
        GW = GizmoWrapper()
        G = GW.G
        json_ob = [1, "two", 3]
        lit = GizmoLiteral(json_ob, G)
        awaitable = lit._get(to_depth=None, oid=None, future=None, test_result=json_ob)
        result = await awaitable
        self.assertEqual(result, json_ob)

    ''' BROKEN TESTS
    async def test_auto_flushes(self):
        packets_processed = []
        def process_packet(packet):
            packets_processed.append(packet)
        strings_sent = []
        async def awaitable_sender(string):
            strings_sent.append(string)
        packet_limit = 4
        auto_flush = True
        P = GizmoPacker(process_packet, awaitable_sender, packet_limit, auto_flush)
        flush_task = P.send_unicode("123abc")
        expect_sends =  ['C123a', 'Fbc']
        await flush_task
        self.assertEqual(strings_sent, expect_sends)

    async def test_manual_flushes(self):
        packets_processed = []
        def process_packet(packet):
            packets_processed.append(packet)
        strings_sent = []
        async def awaitable_sender(string):
            strings_sent.append(string)
        packet_limit = 4
        auto_flush = False
        P = GizmoPacker(process_packet, awaitable_sender, packet_limit, auto_flush)
        P.flush()
        P.send_unicode("123abc")
        expect_sends =  ['C123a', 'Fbc']
        await P.awaitable_flush()
        self.assertEqual(strings_sent, expect_sends)
        '''

    async def test_pipelines_a_message_sent(self, auto_clear=False):
        GW = GizmoWrapper()
        G = GW.G
        P = GZPipeline(G)
        P.auto_clear = auto_clear
        # Make a message to receive from JS
        json_ob = [1, "json", None]
        json_msg = exec_msg(_lit(json_ob))
        # Make a "request" for that message
        cnx = FakeWebSocketUnicodeMessages([])  # no messages from JS side
        req = dummy_request()
        # attach the web socket to the pipeline
        await P.handle_websocket_request(req, cnx.get_web_socket)
        # Send the request
        G._send(json_msg)
        # wait for the request to go through
        expect_str = FINISHED_UNICODE + json.dumps(json_msg)
        await P.packer.flush_queue_task
        ws = cnx.ws
        self.assertEqual(ws._sent, [expect_str])
        if auto_clear:
            self.assertEqual(P.last_unicode_sent, None)
        else:
            self.assertNotEqual(P.last_unicode_sent, None)
        self.assertEqual(P.last_json_received, None)

    async def test_one_request_per_pipeline(self, auto_clear=False):
        GW = GizmoWrapper()
        G = GW.G
        P = GZPipeline(G)
        P.auto_clear = auto_clear
        # Make a message to send to JS
        json_ob = [1, "json", None]
        json_msg = exec_msg(_lit(json_ob))
        # Make a "request" for that message
        cnx = FakeWebSocketUnicodeMessages([])  # no messages from JS side
        req = dummy_request()
        # attach the web socket to the pipeline
        await P.handle_websocket_request(req, cnx.get_web_socket)
        self.assertNotEqual(P.request, None)
        req2 = dummy_request("different_id")
        with self.assertRaises(TooManyRequests):
            await P.handle_websocket_request(req2, cnx.get_web_socket)

    async def test_pipelines_a_message_sent_early(self, auto_clear=False):
        #p("starging early test")
        GW = GizmoWrapper()
        G = GW.G
        P = GZPipeline(G)
        P.set_auto_flush(True)
        P.auto_clear = auto_clear
        # Make a message to send down to JS
        json_ob = [1, "json", None]
        json_msg = exec_msg(_lit(json_ob))
        # Make a "request" for that message
        cnx = FakeWebSocketUnicodeMessages([])  # no messages from JS side
        req = dummy_request()
        # Send the request
        #self.assertEqual(P.sender, None)
        #P.send_json(json_msg)
        G._send(json_msg)
        await P.packer.flush_queue_task
        # attach the web socket to the pipeline, after the send
        await P.handle_websocket_request(req, cnx.get_web_socket)
        # wait for the request to go through
        expect_str = FINISHED_UNICODE + json.dumps(json_msg)
        #await P.packer.flush_queue_task
        ws = cnx.ws
        self.assertEqual(ws._sent, [expect_str])
        if auto_clear:
            self.assertEqual(P.last_unicode_sent, None)
        else:
            self.assertNotEqual(P.last_unicode_sent, None)

    async def test_pipelines_a_message_sent_clear(self):
        return await self.test_pipelines_a_message_sent(auto_clear=True)

    async def xxxtest_async_iterable(self):
        iterable = AsyncIterable(list("abc"))
        async for d in iterable:
            #p("data", d)
            pass

class AsyncIterable:

    def __init__(self, items):
        self.index = 0
        self.items = items

    def __aiter__(self):
        return self

    async def __anext__(self):
        data = await self.fetch_data()
        if data:
            return data
        else:
            raise StopAsyncIteration

    async def fetch_data(self):
        index = self.index
        self.index = index + 1
        try:
            return self.items[index]
        except IndexError:
            return None


class TestGizmoAsyncSend(unittest.IsolatedAsyncioTestCase):
    async def test_pipelines_a_message_received(self, auto_clear=False):
        GW = GizmoWrapper()
        G = GW.G
        data = []
        def callback_function(*args):
            data.append(args)
        oid = G._register_callback(callback_function)
        arguments = ["this", "argument", "list"]
        json_msg = [GZ.CALLBACK, oid, arguments]
        ws_msg = FINISHED_UNICODE + json.dumps(json_msg)
        P = GZPipeline(G)
        P.auto_clear = auto_clear
        # Make a "request" with the callback
        cnx = FakeWebSocketUnicodeMessages([ws_msg])
        #async for x in cnx.ws:
        #    #p("for", x)
        req = dummy_request()
        # attach the web socket to the pipeline
        await P.handle_websocket_request(req, cnx.get_web_socket)
        # Send the request
        ws = cnx.ws
        self.assertEqual(data, [tuple(arguments)])
        if auto_clear:
            self.assertEqual(P.last_json_received, None)
        else:
            self.assertNotEqual(P.last_json_received, None)
        self.assertEqual(P.last_unicode_sent, None)

class TestGizmoAsyncSendClear(unittest.IsolatedAsyncioTestCase):
    async def test_pipelines_a_message_received_clear(self, auto_clear=True):
        GW = GizmoWrapper()
        G = GW.G
        data1 = []
        def callback_function(*args):
            #raise IndexError
            if len(data1) > 0:
                raise ValueError
            data1.append(args)
        oid = G._register_callback(callback_function)
        arguments = ["this", "argument", "list"]
        json_msg = [GZ.CALLBACK, oid, arguments]
        ws_msg = FINISHED_UNICODE + json.dumps(json_msg)
        P = GZPipeline(G)
        P.auto_clear = auto_clear
        # Make a "request" with the callback
        cnx = FakeWebSocketUnicodeMessages([ws_msg])
        #async for x in cnx.ws:
        #    #p("for", x)
        req = dummy_request()
        # attach the web socket to the pipeline
        await P.handle_websocket_request(req, cnx.get_web_socket)
        # Send the request
        ws = cnx.ws
        self.assertEqual(data1, [tuple(arguments)])
        if auto_clear:
            self.assertEqual(P.last_json_received, None)
        else:
            self.assertNotEqual(P.last_json_received, None)
        self.assertEqual(P.last_unicode_sent, None)

class TestPipelineJsonErr(unittest.IsolatedAsyncioTestCase):
    async def test_pipelines_json_err(self, auto_clear=False):
        GW = GizmoWrapper()
        G = GW.G
        ws_msg = FINISHED_UNICODE + "xxxgarbage^&%"
        P = GZPipeline(G)
        P.auto_clear = auto_clear
        # Make a "request" with the callback
        cnx = FakeWebSocketUnicodeMessages([ws_msg])
        req = dummy_request()
        # attach the web socket to the pipeline
        await P.handle_websocket_request(req, cnx.get_web_socket)
        self.assertNotEqual(P.last_json_error, None)
        self.assertNotEqual(P.last_receive_error, None)
        self.assertEqual(P.last_unicode_sent, None)
        self.assertEqual(P.last_json_received, None)

class TestPipelineWSErr(unittest.IsolatedAsyncioTestCase):
    async def test_pipelines_ws_err(self, auto_clear=False):
        GW = GizmoWrapper()
        G = GW.G
        ws_msg = FINISHED_UNICODE + "xxxgarbage^&%"
        P = GZPipeline(G)
        P.auto_clear = auto_clear
        # two error packets cause an assertion error
        cnx = FakeWebSocketUnicodeMessages([ws_msg, ws_msg], msg_type=GZPipeline.MSG_TYPE_ERROR)
        req = dummy_request()
        # attach the web socket to the pipeline
        with self.assertRaises(AssertionError):
            await P.handle_websocket_request(req, cnx.get_web_socket)
        self.assertEqual(P.last_json_error, None)
        self.assertEqual(P.last_receive_error, None)
        self.assertEqual(P.last_unicode_sent, None)
        self.assertEqual(P.last_json_received, None)
        self.assertNotEqual(P.ws_error_message, None)
