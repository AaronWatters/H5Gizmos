"""

Gizmo protocol.  Parent side.

See js/H5Gizmos.js for protocol JSON formats.

"""

import numpy as np
import json
import asyncio
from .hex_codec import bytearray_to_hex


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

    def __init__(self, sender, default_depth=5):
        self._sender = sender
        self._default_depth = default_depth
        self._call_backs = {}
        self._callable_to_oid = {}
        self._counter = 0
        self._oid_to_get_futures = {}
        self._on_exception = None
        self._last_exception_payload = None

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
        return callback_for_id(*json_args)

    def _receive_exception(self, payload):
        self._last_exception_payload = payload
        [message, oid] = payload
        exc = JavascriptEvalException(message)
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

    def _exec(self, detail=False):
        gz = self._owner_gizmo
        cmd = self._command()
        msg = [GZ.EXEC, cmd]
        gz._send(msg)
        if detail:
            return cmd
        else:
            return None

    async def _get(self, to_depth=None, oid=None, future=None, test_result=None):
        gz = self._owner_gizmo
        cmd = self._command()
        if oid is None:
            # allow the test suite to pass in the future for testing only...
            (oid, future) = gz._register_future()
        if to_depth is None:
            to_depth = gz._default_depth
        msg = [GZ.EXEC, oid, cmd, to_depth]
        gz._send(msg)
        if test_result is not None:
            return test_result  # only for code coverage...
        await future
        return future.result()

    def _connect(self, id):
        gz = self._owner_gizmo
        cmd = self._command()
        msg = [GZ.CONNECT, id, cmd]
        gz._send(msg)
        return GizmoReference(id, gz)

    def _disconnect(self, id=None):
        if id is None:
            id = self._get_id()
        gz = self._owner_gizmo
        msg = [GZ.DISCONNECT, id]
        gz._send(msg)

    def _command(self):
        raise NotImplementedError("This method must be implemented in subclass.")

    def _get_id(self):
        raise NotImplementedError("No id for this subclass of GizmoLink.")

    def __call__(self, *args):
        gz = self._owner_gizmo
        arg_commands = [ValueConverter(x, gz) for x in args]
        return GizmoCall(self, arg_commands, gz)

    def __getattr__(self, attribute):
        gz = self._owner_gizmo
        attribute_cmd = ValueConverter(attribute, gz)
        return GizmoGet(self, attribute_cmd, gz)


class GizmoGet(GizmoLink):

    """
    Proxy get javascript object property..
    """

    def __init__(self, target_cmd, index_cmd, owner):
        self._owner_gizmo = owner
        self._target_cmd = target_cmd
        self._index_cmd = index_cmd

    def _command(self):
        return [GZ.GET, self._target_cmd._command(), self._index_cmd._command()]

class GizmoCall(GizmoLink):

    """
    Proxy call javascript object
    """

    def __init__(self, callable_cmd, args_cmds, owner):
        self._owner_gizmo = owner
        self._callable_cmd = callable_cmd
        self._args_cmds = args_cmds

    def _command(self):
        args_json = [x._command() for x in self._args_cmds]
        return [GZ.CALL, self._callable_cmd._command(), args_json]

class GizmoReference(GizmoLink):

    """
    Proxy reference to a Javascript cached object.
    """

    def __init__(self, id, owner):
        self._owner_gizmo = owner
        self._id = id

    def _command(self):
        return [GZ.REFERENCE, self._id]

    def _get_id(self):
        return self._id


class GizmoLiteral(GizmoLink):

    """
    Wrapped JSON literal
    """

    def __init__(self, value, owner):
        self._owner_gizmo = owner
        self._value = value

    def _command(self):
        return [GZ.LITERAL, self._value]


class GizmoSequence(GizmoLink):

    """
    Wrapped sequence
    """

    def __init__(self, commands, owner):
        self._owner_gizmo = owner
        self._commands = commands

    def _command(self):
        cmds_json = [x._command() for x in self._commands]
        return [GZ.SEQUENCE, cmds_json]


class GizmoMapping(GizmoLink):

    """
    Wrapped sequence
    """

    def __init__(self, command_dictionary, owner):
        self._owner_gizmo = owner
        self._command_dictionary = command_dictionary

    def _command(self):
        cmds_json = {name: c._command() for (name, c) in self._command_dictionary.items()}
        return [GZ.MAP, cmds_json]

class GizmoBytes(GizmoLink):

    """
    Wrapped byte sequence
    """

    def __init__(self, byte_array, owner):
        self._owner_gizmo = owner
        self._byte_array = byte_array

    def _command(self):
        hex = bytearray_to_hex(self._byte_array)
        return [GZ.BYTES, hex]

class GizmoCallback(GizmoLink):

    """
    Wrapped callback to callable.
    """

    def __init__(self, callable_object, owner, to_depth=None):
        if to_depth is None:
            to_depth = owner._default_depth
        self._to_depth = to_depth
        self._owner_gizmo = owner
        self._callable_object = callable_object
        self._oid = owner._register_callback(callable_object)

    def _command(self):
        return [GZ.CALLBACK, self._oid, self._to_depth]


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

    def _command(self):
        return self.command._command()

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

    def flush(self):
        outgoing = self.outgoing_packets
        self.outgoing_packets = []
        if outgoing:
            awaitable = self.awaitable_flush(outgoing)
            task = schedule_task(awaitable)
            #print ("flush returns task", task)
            return task
        else:
            return None

    async def awaitable_flush(self, outgoing=None):
        limit = self.packet_limit
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
            #print ("send unicode returns task", task)
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

def schedule_task(awaitable):
    "Schedule a task in the global event loop."
    # Convenience
    loop = asyncio.get_event_loop()
    task = loop.create_task(awaitable)
    return task
