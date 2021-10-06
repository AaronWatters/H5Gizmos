

# Requires python 3.8
# Run from setup folder:
# nosetests --with-coverage --cover-html --cover-package=H5Gizmos --cover-erase --cover-inclusive

import unittest

from H5Gizmos.python.H5Gizmos import (
    Gizmo, 
    GZ,
    GizmoLiteral,
    JavascriptEvalException,
    NoSuchCallback,
    GizmoLink,
    GizmoReference,
)

'''
class TestFails(unittest.TestCase):

    def test_fail(self):
        self.assertEqual(1, 0)
'''

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

def get_msg(oid, cmd, to_depth):
    return [GZ.GET, oid, cmd, to_depth]

def exec_msg(cmd):
    return [GZ.EXEC, cmd]

def connect_msg(id, cmd):
    return [GZ.CONNECT, id, cmd]

def disconnect_msg(id):
    return [GZ.DISCONNECT, id]

class TestGizmo(unittest.TestCase):

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
            X._command()
        with self.assertRaises(NotImplementedError):
            X._get_id()

class TestGizmoAsync(unittest.IsolatedAsyncioTestCase):

    async def test_resolves_get(self):
        GW = GizmoWrapper()
        G = GW.G
        json_ob = [1, "two", 3]
        lit = GizmoLiteral(json_ob, G)
        to_depth = 5
        # pass in the future so we can resolve it in the test case...
        (oid, future) = G._register_future()
        awaitable = lit._get(to_depth, oid, future)
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
        awaitable = lit._get(to_depth, oid, future)
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
