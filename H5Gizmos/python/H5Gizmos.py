"""

Gizmo protocol.  Parent side.

See js/H5Gizmos.js for protocol JSON formats.

"""

import os
import numpy as np
import json
import asyncio
import aiohttp
import sys, traceback

from .hex_codec import bytearray_to_hex
from aiohttp import web
from . import gz_resources
from . import gizmo_server

class Gizmo:
    EXEC = "E"
    GET = "G"
    CONNECT = "C"
    DISCONNECT = "D"
    LITERAL = "L"
    BYTES = "B"
    MAP = "M"
    SEQUENCE = "SQ"
    REFERENCE = "R"
    CALL = "C"
    CALLBACK = "CB"
    SET = "S"
    EXCEPTION = "X"

    def __init__(self, sender=None, default_depth=3, pipeline=None):
        self._pipeline = pipeline
        self._sender = sender
        self._default_depth = default_depth
        self._call_backs = {}
        self._callable_to_oid = {}
        self._counter = 0
        self._oid_to_get_futures = {}
        self._on_exception = None
        self._last_exception_payload = None
        self._manager = None
        self._server = None
        self._port = None
        self._entry_url = None
        self._ws_url = None
        self._html_page = None
        self._print_callback_exception = True

    async def _awaitable_flush(self):
        await self._pipeline.packer.awaitable_flush()

    def _configure_entry_page(self, title="Gizmo", filename="index.html"):
        mgr = self._manager
        assert mgr is not None, "manager must be set before page configuration."
        ws_url = mgr.local_url(for_gizmo=self, method="ws", filename=None)
        if ws_url.startswith("http:"):
            ws_url = "ws:" + ws_url[5:]
        self._ws_url = ws_url
        handler = self._html_page = gz_resources.HTMLPage(ws_url=self._ws_url, title=title)
        mgr.add_http_handler(filename, handler)
        self._js_file("../../H5Gizmos/js/H5Gizmos.js")
        self._entry_url = mgr.local_url(for_gizmo=self, method="http", filename=filename)

    def _initial_reference(self, identity, js_expression=None):
        assert type(identity) == str, "identity must be str " + repr(identity)
        if js_expression is None:
            js_expression = identity   # like "window"
        assert self._html_page is not None, "reference requires initialized html page."
        #if hasattr(self, identity):
        #    raise NameError(
        #        "initial reference will not override in-use slot: " + repr(identity))
        #reference = GizmoReference(identity, self)
        #setattr(self, identity, reference)
        self._reference_identity(identity)
        self._html_page.link_reference(identity, js_expression)

    def _reference_identity(self, identity):
        if hasattr(self, identity) and getattr(self, identity) is not None:
            raise NameError(
                "id reference will not override in-use slot: " + repr(identity))
        reference = GizmoReference(identity, self)
        setattr(self, identity, reference)

    def _dereference_identity(self, identity):
        print("deref id", repr(identity))
        old_value = getattr(self, identity)
        assert isinstance(old_value, GizmoReference), (
            "Deref does not apply to non-references.")
        setattr(self, identity, None)

    def _insert_html(self, html_text):
        self._html_page.insert_html(html_text)

    def _embedded_css(self, style_text):
        self._html_page.embedded_css(style_text)

    def _embedded_script(self, javascript_code, in_body=True):
        self._html_page.embedded_script(javascript_code, in_body=in_body)

    def _remote_css(self, css_url):
        self._html_page.remote_css(css_url)

    def _remote_js(self, js_url, in_body=False):
        self._html_page.remote_js(js_url, in_body=in_body)

    def _js_file(self, os_path, url_path=None, in_body=False):
        mgr = self._manager
        full_path = gz_resources.get_file_path(os_path)
        handler = mgr.add_file(full_path, url_path, content_type="text/javascript")
        filename = handler.filename
        # this should be a RELATIVE URL
        #full_url = mgr.local_url(for_gizmo=self, method="http", filename=filename)
        relative_url = self.relative_url(filename)
        self._remote_js(relative_url)

    def relative_url(self, filename):
        return "./" + filename

    def _set_manager(self, gz_server, mgr):
        self._manager = mgr
        self._server = gz_server.server
        self._port = gz_server.port

    def _set_pipeline(self, pipeline):
        self._pipeline = pipeline
        self._sender = pipeline.send_json

    def _register_callback(self, callable):
        c2o = self._callable_to_oid
        cbs = self._call_backs
        oid = c2o.get(callable)
        if oid is None:
            self._counter += 1
            oid = "cb_" + repr(self._counter)
            c2o[callable] = oid
            cbs[oid] = callable
        return oid

    def _send(self, json_message):
        print("gizmo sending json", repr(json_message))
        self._sender(json_message)

    def _receive(self, json_response):
        try:
            indicator = json_response[0]
            payload = json_response[1:]
        except Exception as e:
            truncated_payload = repr(json_response)[:50]
            info = "Error: %s; payload=%s" % (e, truncated_payload)
            raise BadResponseFormat(info)
        if indicator == Gizmo.GET:
            return self._resolve_get(payload)
        elif indicator == Gizmo.CALLBACK:
            return self._call_back(payload)
        elif indicator == Gizmo.EXCEPTION:
            return self._receive_exception(payload)
        else:
            truncated_payload = repr(json_response)[:50]
            info = "Unknown indicator: %s; payload=%s" % (indicator, truncated_payload)
            raise BadResponseFormat(info)

    def _resolve_get(self, payload):
        [oid, json_value] = payload
        o2f = self._oid_to_get_futures
        if oid is not None and oid in o2f:
            get_future = o2f[oid]
            del o2f[oid]
            if not get_future.done():
                get_future.set_result(json_value)
        else:
            raise NoRequestForOid("No known request matching oid: " + repr(oid))
        return json_value

    def _call_back(self, payload):
        [id_string, json_args] = payload
        callback_for_id = self._call_backs.get(id_string)
        if callback_for_id is None:
            raise NoSuchCallback(id_string)
        try:
            return callback_for_id(*json_args)
        except Exception as e:
            if self._print_callback_exception:
                print("exception in gizmo callback: " + repr(e))
                print("-"*60)
                traceback.print_exc(file=sys.stdout)
                print("-"*60)
            raise e

    def _receive_exception(self, payload):
        self._last_exception_payload = payload
        [message, oid] = payload
        exc = JavascriptEvalException("js error: " + repr(message))
        o2f = self._oid_to_get_futures
        if oid is not None and oid in o2f:
            get_future = o2f[oid]
            del o2f[oid]
            if not get_future.done():
                get_future.set_exception(exc)
        on_exc = self._on_exception
        if on_exc is not None:
            on_exc(payload)
        return exc

    def _register_future(self):
        self._counter += 1
        oid = "GZget_" + repr(self._counter)
        future = self._make_future()
        self._oid_to_get_futures[oid] = future
        return (oid, future)

    def _make_future(self):
        "Get a future associated with the global event loop."
        # Convenience
        loop = asyncio.get_event_loop()
        return loop.create_future()


GZ = Gizmo

class BadResponseFormat(ValueError):
    "Javascript sent a message which was not understood."

class JavascriptEvalException(ValueError):
    "Javascript reports error during command interpretation."

class NoSuchCallback(ValueError):
    "Callback id not found."

class NoRequestForOid(ValueError):
    "Target for GET reply not found."

class CantConvertValue(ValueError):
    "Can't convert value for transmission of JSON link."


class GizmoLink:

    """
    Abstract superclass for Gizmo connected interfaces.
    """

    _owner_gizmo = None  # set this in subclass
    _get_oid = None
    _get_future = None

    def _register_get_future(self):
        if self._get_oid is not None:
            return (self._get_oid, self._get_future)
        result = (self._get_oid, self._get_future) = self._owner_gizmo._register_future()
        return result

    def _exec(self, to_depth=None, detail=False):
        to_depth = to_depth or self._owner_gizmo._default_depth
        gz = self._owner_gizmo
        cmd = self._command(to_depth)
        print("cmd", cmd)
        msg = [GZ.EXEC, cmd]
        gz._send(msg)
        if detail:
            return cmd
        else:
            return None

    async def _get(self, to_depth=None, oid=None, future=None, test_result=None):
        gz = self._owner_gizmo
        to_depth = to_depth or gz._default_depth
        cmd = self._command(to_depth)
        if oid is None:
            # allow the test suite to pass in the future for testing only...
            (oid, future) = self._register_get_future()
        self._get_oid = oid
        msg = [GZ.GET, oid, cmd, to_depth]
        gz._send(msg)
        if test_result is not None:
            return test_result  # only for code coverage...
        await future
        self._get_oid = None
        self._get_future = None
        return future.result()

    def _connect(self, id, to_depth=None):
        gz = self._owner_gizmo
        to_depth = to_depth or gz._default_depth
        cmd = self._command(to_depth)
        msg = [GZ.CONNECT, id, cmd]
        gz._send(msg)
        self._owner_gizmo._reference_identity(id)
        return GizmoReference(id, gz)

    def _disconnect(self, id=None):
        if id is None:
            id = self._get_id()
        gz = self._owner_gizmo
        msg = [GZ.DISCONNECT, id]
        self._owner_gizmo._dereference_identity(id)
        gz._send(msg)

    def _command(self, to_depth):
        raise NotImplementedError("This method must be implemented in subclass.")

    def _get_id(self):
        raise NotImplementedError("No id for this subclass of GizmoLink.")

    def __call__(self, *args):
        gz = self._owner_gizmo
        arg_commands = [ValueConverter(x, gz) for x in args]
        #pr(self, "making gizmocall", arg_commands)
        return GizmoCall(self, arg_commands, gz)

    def __getattr__(self, attribute):
        gz = self._owner_gizmo
        attribute_cmd = ValueConverter(attribute, gz)
        return GizmoGet(self, attribute_cmd, gz)

    def _set(self, attribute, value):
        gz = self._owner_gizmo
        attribute_cmd = ValueConverter(attribute, gz)
        value_cmd = ValueConverter(value, gz)
        return GizmoSet(self, attribute_cmd, value_cmd, gz)

    def __getitem__(self, key):
        # in Javascript getitem and getattr are roughly the same
        return self.__getattr__(key)


class GizmoGet(GizmoLink):

    """
    Proxy get javascript object property..
    """

    def __init__(self, target_cmd, index_cmd, owner):
        self._owner_gizmo = owner
        self._target_cmd = target_cmd
        self._index_cmd = index_cmd

    def _command(self, to_depth):
        return [
            GZ.GET, 
            self._target_cmd._command(to_depth), 
            self._index_cmd._command(to_depth)
            ]

class GizmoSet(GizmoLink):

    """
    Proxy get javascript object property..
    """

    def __init__(self, target_cmd, index_cmd, value_cmd, owner):
        self._owner_gizmo = owner
        self._target_cmd = target_cmd
        self._value_cmd = value_cmd
        self._index_cmd = index_cmd

    def _command(self, to_depth):
        return [
            GZ.SET, 
            self._target_cmd._command(to_depth), 
            self._index_cmd._command(to_depth), 
            self._value_cmd._command(to_depth)
            ]

class GizmoCall(GizmoLink):

    """
    Proxy call javascript object
    """

    def __init__(self, callable_cmd, args_cmds, owner):
        self._owner_gizmo = owner
        self._callable_cmd = callable_cmd
        self._args_cmds = args_cmds

    def _command(self, to_depth):
        args_json = [x._command(to_depth) for x in self._args_cmds]
        return [GZ.CALL, self._callable_cmd._command(to_depth), args_json]

class GizmoReference(GizmoLink):

    """
    Proxy reference to a Javascript cached object.
    """

    def __init__(self, id, owner):
        self._owner_gizmo = owner
        self._id = id

    def _command(self, to_depth):
        return [GZ.REFERENCE, self._id]

    def _get_id(self):
        return self._id

    def disconnect(self):
        return self._disconnect(self._id)


class GizmoLiteral(GizmoLink):

    """
    Wrapped JSON literal
    """

    def __init__(self, value, owner):
        self._owner_gizmo = owner
        self._value = value

    def _command(self, to_depth):
        return [GZ.LITERAL, self._value]


class GizmoSequence(GizmoLink):

    """
    Wrapped sequence
    """

    def __init__(self, commands, owner):
        self._owner_gizmo = owner
        self._commands = commands

    def _command(self, to_depth):
        cmds_json = [x._command(to_depth) for x in self._commands]
        return [GZ.SEQUENCE, cmds_json]


class GizmoMapping(GizmoLink):

    """
    Wrapped sequence
    """

    def __init__(self, command_dictionary, owner):
        self._owner_gizmo = owner
        self._command_dictionary = command_dictionary

    def _command(self, to_depth):
        cmds_json = {
            name: c._command(to_depth) 
                for (name, c) in self._command_dictionary.items()
            }
        return [GZ.MAP, cmds_json]

class GizmoBytes(GizmoLink):

    """
    Wrapped byte sequence
    """

    def __init__(self, byte_array, owner):
        self._owner_gizmo = owner
        self._byte_array = byte_array

    def _command(self, to_depth):
        hex = bytearray_to_hex(self._byte_array)
        return [GZ.BYTES, hex]

class GizmoCallback(GizmoLink):

    """
    Wrapped callback to callable.
    """

    def __init__(self, callable_object, owner):
        self._owner_gizmo = owner
        self._callable_object = callable_object
        self._oid = owner._register_callback(callable_object)

    def _command(self, to_depth):
        return [GZ.CALLBACK, self._oid, to_depth]


def np_array_to_list(a):
    return a.tolist()

class ValueConverter:

    """
    Convert value sub-components where needed.
    """

    def __init__(self, value, owner):
        self.value = value
        self.is_literal = True
        ty = type(value)
        translator = self.translators.get(ty)
        translation = value
        if translator is not None:
            translation = translator(value)
            ty = type(translation)
        if ty in self.scalar_types:
            self.converted = translation
            self.command = GizmoLiteral(translation, owner)
        elif ty is list:
            conversions = []
            for x in translation:
                c = ValueConverter(x,owner)
                if not c.is_literal:
                    self.is_literal = False
                conversions.append(c)
            if self.is_literal:
                self.command = GizmoLiteral(translation, owner)
            else:
                commands = [c.command for c in conversions]
                self.command = GizmoSequence(commands, owner)
        elif ty is dict:
            conversions = {}
            for key in translation:
                val = translation[key]
                c = ValueConverter(val, owner)
                if not c.is_literal or type(key) is not str:
                    self.is_literal = False
                # XXX automatically convert keys to strings???
                conversions[str(key)] = c
            if self.is_literal:
                self.command = GizmoLiteral(translation, owner)
            else:
                command_dict = {name: c.command for (name, c) in conversions.items()}
                self.command = GizmoMapping(command_dict, owner)
        elif ty is bytearray:
            self.is_literal = False
            self.command = GizmoBytes(translation, owner)
        elif isinstance(translation, GizmoLink):
            self.is_literal = False
            self.command = translation
        elif callable(translation):
            self.is_literal = False
            self.command = GizmoCallback(translation, owner)
        else:
            raise CantConvertValue("No conversion for: " + repr(ty))

    def _command(self, to_depth):
        return self.command._command(to_depth)

    scalar_types = set([int, float, str,  bool])

    translators = {
        np.ndarray: np_array_to_list,
        tuple: list,
        #np.float: float,
        #np.float128: float,
        #np.float16: float,
        #np.float32: float,
        #np.float64: float,
        #np.int: int,
        #np.int0: int,
        #np.int16: int,
        #np.int32: int,
        #np.int64: int,
    }
    for type_name in "float float128 float16 float32 float64".split():
        if hasattr(np, type_name):
            ty = getattr(np, type_name)
            translators[ty] = float
    for type_name in "int int0 int16 int32 int64".split():
        if hasattr(np, type_name):
            ty = getattr(np, type_name)
            translators[ty] = int

FINISHED_UNICODE = "F"
CONTINUE_UNICODE = "C"

class GizmoPacker:

    def __init__(self, process_packet, awaitable_sender, packet_limit=1000000, auto_flush=True):
        self.process_packet = process_packet
        self.packet_limit = packet_limit
        self.collector = []
        self.outgoing_packets = []
        self.auto_flush = auto_flush
        self.awaitable_sender = awaitable_sender
        self.last_flush_task = None

    def flush(self):
        outgoing = self.outgoing_packets
        self.outgoing_packets = []
        if outgoing:
            awaitable = self.awaitable_flush(outgoing)
            task = schedule_task(awaitable)
            ##pr ("flush returns task", task)
            self.last_flush_task = task
            return task
        else:
            return None

    async def awaitable_flush(self, outgoing=None):
        limit = self.packet_limit
        #if self.last_flush_task is not None:
        #    # wait for last flush to complete (for testing mainly?)
        #    await self.last_flush_task
        #    self.last_flush_task = None
        if outgoing is None:
            outgoing = self.outgoing_packets
            self.outgoing_packets = []
        for string in outgoing:
            ln = len(string)
            for start in range(0, ln, limit):
                end = start + limit
                chunk = string[start : end]
                final = end >= ln
                if final:
                    data = FINISHED_UNICODE + chunk
                else:
                    data = CONTINUE_UNICODE + chunk
                await self.awaitable_sender(data)

    def send_unicode(self, string):
        self.outgoing_packets.append(string)
        if self.auto_flush:
            task = self.flush()
            ##pr ("send unicode returns task", task)
            return task
        else:
            return None

    def on_unicode_message(self, message):
        indicator = message[0:1]
        remainder = message[1:]
        if indicator == CONTINUE_UNICODE:
            self.collector.append(remainder)
        elif indicator == FINISHED_UNICODE:
            collector = self.collector
            self.collector = []
            collector.append(remainder)
            packet = "".join(collector)
            self.process_packet(packet)
        else:
            raise BadMessageIndicator(repr(message[:20]))

class BadMessageIndicator(ValueError):
    "Message fragment first character not understood."

class JsonCodec:

    def __init__(self, process_json, send_unicode, on_error=None):
        self.process_json = process_json
        self.send_unicode = send_unicode
        self.on_error = on_error

    def receive_unicode(self, unicode_str):
        on_error = self.on_error
        try:
            json_ob = json.loads(unicode_str)
        except Exception as e:
            if on_error:
                on_error("failed to parse json " + repr((repr(unicode_str)[:20], e)))
            raise e
        self.process_json(json_ob)
        return json_ob

    def send_json(self, json_ob):
        on_error = self.on_error
        try:
            unicode_str = json.dumps(json_ob)
        except Exception as e:
            if on_error:
                on_error("failed to encode json " + repr((repr(json_ob)[:20], e)))
            raise e
        self.send_unicode(unicode_str)
        return unicode_str


class GZPipeline:

    def __init__(self, gizmo, packet_limit=1000000, auto_flush=True):
        self.gizmo = gizmo
        gizmo._set_pipeline(self)
        self.sender = None
        self.request = None
        self.web_socket = None
        self.waiting_chunks = []
        self.packer = GizmoPacker(self.process_packet, self._send, packet_limit, auto_flush)
        self.json_codec = JsonCodec(self.process_json, self.send_unicode, self.json_error)
        self.last_json_error = None
        self.last_receive_error = None
        self.ws_error_message = None
        self.clear()

    auto_clear = True  # set false only for debug

    def clear(self):
        # release debug references
        self.last_unicode_sent = None
        self.last_json_received = None
        self.last_json_sent = None
        self.last_packet_processed = None
        self.last_unicode_received = None

    def set_auto_flush(self, state=True):
        self.packer.auto_flush = state
        if state:
            self.packer.flush()

    def send_json(self, json_ob):
        self.json_codec.send_json(json_ob)
        self.last_json_sent = json_ob

    async def _send(self, chunk):
        #pr ("pipeline sending", repr(chunk))
        if self.sender is not None:
            await self.sender(chunk)
        else:
            self.waiting_chunks.append(chunk)
        if self.auto_clear:
            self.clear()

    async def handle_websocket_request(self, request, get_websocket=web.WebSocketResponse):
        #pr("pipeline handling request", request)
        if self.request is not None:
            raise TooManyRequests("A pipeline can only support one request.")
        ws = get_websocket()
        self.web_socket = ws
        await ws.prepare(request)
        self.request = request
        self.sender = ws.send_str
        wc = self.waiting_chunks
        self.waiting_chunks = []
        for chunk in wc:
            #pr ("pipeline sending waiting chunk", repr(chunk))
            await self._send(chunk)
        await self.listen_to_websocket(ws)

    MSG_TYPE_TEXT = aiohttp.WSMsgType.text
    MSG_TYPE_ERROR = aiohttp.WSMsgType.error

    async def listen_to_websocket(self, ws):
        self.web_socket = ws
        got_exception = False
        ##pr("listening to", ws)
        async for msg in ws:
            assert not got_exception, "Web socket should terminate after an exception."
            typ = msg.type
            #pr("got message", typ, msg.data)
            if typ == self.MSG_TYPE_TEXT:
                data = msg.data
                try:
                    self.receive_unicode(data)
                except Exception as e:
                    self.last_receive_error = e
                    # continue to process messages.
                    pass
            elif typ == self.MSG_TYPE_ERROR:
                got_exception = True
                if self.ws_error_message is None:
                    self.ws_error_message = msg
                # If the ws doesn't terminate the assertion will raise.
            else:
                pass   # ??? ignore ???

    def receive_unicode(self, unicode_str):
        #pr("pipeline receive unicode", repr(unicode_str))
        self.last_unicode_received = unicode_str
        return self.packer.on_unicode_message(unicode_str)

    def process_packet(self, packet):
        #pr("pipeline process packet", repr(packet))
        self.last_packet_processed = packet
        return self.json_codec.receive_unicode(packet)

    def process_json(self, json_ob):
        #pr("pipeline process_json", repr(json_ob))
        self.last_json_received = json_ob
        self.gizmo._receive(json_ob)
        if self.auto_clear:
            self.clear()

    def send_unicode(self, unicode_str):
        "async send -- do not wait for completion."
        #pr("pipeline send unicode", repr(unicode_str))
        task_or_none = self.packer.send_unicode(unicode_str)
        self.last_unicode_sent = unicode_str
        return task_or_none

    def json_error(self, msg):
        # ????
        #pr("pipeline json err", msg)
        self.last_json_error = msg

class TooManyRequests(ValueError):
    "A pipeline can only support one request."

def schedule_task(awaitable):
    "Schedule a task in the global event loop."
    # Convenience
    loop = asyncio.get_event_loop()
    task = loop.create_task(awaitable)
    return task
