
// based on https://medium.com/piecesofcode/testing-javascript-code-with-jest-18a398888838

const H5Gizmos = require('../H5Gizmos/js/H5Gizmos');

test('module is loaded', () => {
    expect(H5Gizmos.is_loaded).toBe(true);
});

test("sends a message", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    tr.send(["hello", "world"]);
    expect(save_message).toEqual(["hello", "world"]);
});

test("caches objects", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    expect(() => { tr.get_reference("thing"); }).toThrow();
    var object = ["hello", "world"];
    tr.set_reference("thing", object);
    var pair = tr.get_reference("thing");
    expect(pair.value).toBe(object);
    tr.forget_reference("thing")
    expect(() => { tr.get_reference("thing"); }).toThrow()
});

test("preserves json", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    var value = {
        0: 1,
        1: ["a string", 123, true, null]
    };
    var json_ob = tr.json_safe(value, 5);
    expect(json_ob).toEqual(value);
});

test("truncates json", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    var value = {
        0: 1,
        1: ["a string", 123, true, null],
        2: [[2]],
        3: [[[3]]],
        4: [[[[4]]]],
        5: [[[[[5]]]]],
    };
    var expected = {
        0: 1,
        1: ["a string", 123, true, null],
        2: [[2]],
        3: [[[3]]],
        4: [[[[4]]]],
        5: [[[[null]]]],
    };
    var json_ob = tr.json_safe(value, 5);
    expect(json_ob).toEqual(expected);
});

test("converts binary to hex", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    var value = {
        0: new Uint8Array([1,2,3]),
    };
    var expected = {
        0: "010203",
    };
    var json_ob = tr.json_safe(value, 5);
    expect(json_ob).toEqual(expected);
});

test("converts hex to binary", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    var hex = "010203";
    var binary = new Uint8Array([1,2,3])
    var converted = tr.from_hex(hex);
    expect(converted).toEqual(binary);
    expect(() => { tr.from_hex("01020"); }).toThrow();
});

test("rejects bad messages", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    expect(() => { tr.parse_message("01020"); }).toThrow();
    expect(() => { tr.parse_message(["bad", "message"]); }).toThrow();
});

function lit(val) {
    var h5 = H5Gizmos;
    return [h5.LITERAL, val];
};

function exec_(val) {
    var h5 = H5Gizmos;
    return [h5.EXEC, val];
};

test("rejects bad commands", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    expect(() => { tr.parse_command("01020"); }).toThrow();
    expect(() => { tr.parse_command(["bad", "message"]); }).toThrow();
});

test("doesn't double wrap", () => {
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new H5Gizmos.Translator(dthis, sender);
    var pair = tr.value_pair("test value");
    expect(pair.value).toEqual("test value");
    expect(() => { tr.value_pair(pair); }).toThrow();
});

test("parses a literal", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var val = ["some", "value"];
    var json_cmd = lit(val); //[h5.LITERAL, val];
    var cmd = tr.parse_command(json_cmd);
    var exec = cmd.execute(tr);
    expect(exec.value).toEqual(val);
});

test("executes a literal", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var val = ["some", "value"];
    var json_cmd = lit(val); //[h5.LITERAL, val];
    var json_msg = exec_(json_cmd); //[h5.EXEC, json_cmd];
    var msg = tr.parse_message(json_msg);
    var exec = msg.execute(tr);
    expect(exec).toEqual(val);
});

function get(oid, cmd, dpth) {
    var h5 = H5Gizmos;
    return [h5.GET, oid, cmd, dpth];
};

test("gets a literal", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var val = ["some", "value"];
    var oid = "oid123";
    var to_depth = 5;
    var json_cmd = lit(val); //[h5.LITERAL, val];
    var json_msg = get(oid, json_cmd, to_depth);
    var msg = tr.parse_message(json_msg);
    var exec = msg.execute(tr);
    expect(exec).toEqual(val);
    var expected = [h5.GET, oid, val]
    expect(save_message).toEqual(expected);
});

function connect(id, cmd) {
    var h5 = H5Gizmos;
    return [h5.CONNECT, id, cmd];
};
function disconnect(id) {
    var h5 = H5Gizmos;
    return [h5.DISCONNECT, id];
};
function reference(id) {
    var h5 = H5Gizmos;
    return [h5.REFERENCE, id];
};

test("sets and gets references", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var val = ["some", "value"];
    // store the value
    var json_cmd = lit(val); //[h5.LITERAL, val];
    var id = "object_123"
    var json_msg = connect(id, json_cmd);
    var msg = tr.parse_message(json_msg);
    var exec = msg.execute(tr);
    expect(exec).toEqual(val);
    // get the value from storage
    var json_ref = reference(id);
    var oid = "oid456";
    var dpth = 5;
    var json_get = get(oid, json_ref, dpth);
    var get_msg = tr.parse_message(json_get);
    var get_exec = get_msg.execute(tr);
    expect(get_exec).toEqual(val);
    var expected = [h5.GET, oid, val]
    expect(save_message).toEqual(expected);
    // disconnect the value
    var json_disc = disconnect(id);
    var msg_disc = tr.parse_message(json_disc);
    var msg_exec = msg_disc.execute(tr);
    expect(() => { get_msg.execute(tr); }).toThrow();
});

function _bytes(hexstring) {
    var h5 = H5Gizmos;
    return [h5.BYTES, hexstring];
};

test("converts bytes", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var hexstring = "0123456789abcdef";
    var bytes_cmd = _bytes(hexstring);
    var exec_msg = exec_(bytes_cmd); //[h5.EXEC, json_cmd];
    var msg = tr.parse_message(exec_msg);
    var exec = msg.execute(tr);
    var hex_back = tr.to_hex(exec)
    expect(hex_back).toEqual(hexstring);
});

function _map(dictionary) {
    var h5 = H5Gizmos;
    return [h5.MAP, dictionary];
};

test("parses maps", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var dictionary = {
        "first": lit(1),
        "second": lit("two"),
        "third": lit([3]),
    };
    var expected = {
        "first": 1,
        "second": "two",
        "third": [3],
    };
    var map_cmd = _map(dictionary);
    var map_msg = exec_(map_cmd); //[h5.EXEC, json_cmd];
    var msg = tr.parse_message(map_msg);
    //var exec = msg.execute(tr);
    var exec = tr.execute_command(msg);
    expect(exec).toEqual(expected);
});

test("sends parse errors", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var map_cmd = ['no such indicator'];  // invalid message
    var map_msg = exec_(map_cmd); //[h5.EXEC, json_cmd];
    expect(function() { tr.parse_message(map_msg); }).toThrow();
    expect(save_message[0]).toEqual(h5.EXCEPTION);
});

function _sequence(list) {
    var h5 = H5Gizmos;
    return [h5.SEQUENCE, list];
};

test("parses lists", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var list = [
        lit(1),
        lit("two"),
        lit([3]),
    ];
    var expected = [
        1,
        "two",
        [3],
    ]
    var seq_cmd = _sequence(list);
    var seq_msg = exec_(seq_cmd); //[h5.EXEC, json_cmd];
    var msg = tr.parse_message(seq_msg);
    var exec = msg.execute(tr);
    expect(exec).toEqual(expected);
});

function _get(target_cmd, index_cmd) {
    var h5 = H5Gizmos;
    return [h5.GET, target_cmd, index_cmd];
};

test("gets attributes", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var target = {"attr": 42};
    var index = "attr";
    var target_cmd = lit(target);
    var index_cmd = lit(index);
    var get_cmd = _get(target_cmd, index_cmd);
    var expected = 42;
    var get_msg = exec_(get_cmd); //[h5.EXEC, json_cmd];
    var msg = tr.parse_message(get_msg);
    var exec = msg.execute(tr);
    expect(exec).toEqual(expected);
});

function _call(callable_command, args_commands) {
    var h5 = H5Gizmos;
    return [h5.CALL, callable_command, args_commands];
};

test("calls a function", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    // connect a function reference
    function increment(x) { return x + 1; };
    var id_string = "xxx"
    tr.set_reference(id_string, increment);
    // call the function using the command interface
    var json_ref = reference(id_string);
    var json_args = [lit(44)];
    var json_call = _call(json_ref, json_args);
    var call_json_msg = exec_(json_call);
    var msg = tr.parse_message(call_json_msg);
    var exec = msg.execute(tr);
    var expected = 45;
    expect(exec).toEqual(expected);
});

test("calls a method", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    // connect an object instance
    class TestObject {
        constructor(step) {
            this.step = step;
        };
        increment_method (input) {
            return input + this.step;
        };
    };
    var my_instance = new TestObject(13);
    var id_string = "yyy"
    tr.set_reference(id_string, my_instance);
    // call the function using the command interface
    var json_ref = reference(id_string);
    var json_name = lit("increment_method");
    var json_method = _get(json_ref, json_name);
    var json_args = [lit(44)];
    var json_call = _call(json_method, json_args);
    var call_json_msg = exec_(json_call);
    var msg = tr.parse_message(call_json_msg);
    var exec = msg.execute(tr);
    var expected = 44 + 13;
    expect(exec).toEqual(expected);
});

test("sends an exception for a bad get", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var oiderr = null;
    var sender = function(message) {
        save_message = message;
        if (message[2]) {
            oiderr = message[2]
        }
    };
    var tr = new h5.Translator(dthis, sender);
    var val = ["some", "value"];
    var oid = "oid123";
    var to_depth = 5;
    var json_lit = lit(val); //[h5.LITERAL, val];
    var json_call = _call(json_lit, []);
    var json_msg = get(oid, json_call, to_depth);
    var msg = tr.parse_message(json_msg);
    expect(function () { tr.execute_command(msg); }).toThrow();
    var indicator = save_message[0];
    expect(indicator).toEqual(h5.EXCEPTION);
    expect(oiderr).toEqual(oid);
});

function _set(target_cmd, index_cmd, value_command) {
    var h5 = H5Gizmos;
    return [h5.SET, target_cmd, index_cmd, value_command];
};

test("sets an attribute", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    // connect an object instance
    var attr_name = "attr";
    var my_instance = {};
    my_instance[attr_name] = -99;
    var id_string = "yyy"
    tr.set_reference(id_string, my_instance);
    // call the function using the command interface
    var json_ref = reference(id_string);
    var json_name = lit(attr_name);
    var set_value = 42;
    var json_value = lit(set_value);
    var json_set = _set(json_ref, json_name, json_value);
    var set_json_msg = exec_(json_set);
    var msg = tr.parse_message(set_json_msg);
    var exec = msg.execute(tr);
    var expected = set_value;
    expect(my_instance[attr_name]).toEqual(expected);
});

function _callback(id_string, to_depth) {
    var h5 = H5Gizmos;
    return [h5.CALLBACK, id_string, to_depth];
};

test("creates a callback which calls back.", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var id_string = "callback0";
    var to_depth = 5;
    var json_args = [lit(44), lit("arg2")];
    var json_callback = _callback(id_string, to_depth);
    var json_call_callback = _call(json_callback, json_args);
    var callback_json_msg = exec_(json_call_callback);
    var msg = tr.parse_message(callback_json_msg);
    var exec = msg.execute(tr);
    var expected_args = [44, "arg2"]
    var expected_message = [h5.CALLBACK, id_string, expected_args];
    expect(save_message).toEqual(expected_message);
    //expect(exec).toEqual(expected_args)
});

class MockSocketMaker {
    constructor(ws_url) {
        this.ws_url = ws_url;
        this.onmessage = null;
        this.sends = [];
    };
    send(data) {
        this.sends.push(data);
    };
    fake_receive(chunk) {
        //cl("fake receive", chunk)
        var event = new MockEvent(chunk);
        this.onmessage(event);
    };
};
class MockEvent {
    constructor(data) {
        this.data = data;
    };
};

test('creates a Packer and processes a packet', () => {
    var h5 = H5Gizmos;
    var url = "ws://dummy.com/ws";
    var ws = new MockSocketMaker(url);
    var packets = [];
    var process_packet = function(packet) {
        packets.push(packet);
    };
    var packet_limit = 4;
    var packer = new h5.Packer(ws, process_packet, packet_limit);
    //expect(packer.ws_url).toEqual(url);
    var message1 = "123"
    packer.ws.fake_receive(h5.CONTINUE_UNICODE + message1);
    var message2 = "abc"
    packer.ws.fake_receive(h5.FINISHED_UNICODE + message2);
    var message = message1 + message2;
    expect(packets).toEqual([message]);
});

test('breaks a packet into chunks', () => {
    var h5 = H5Gizmos;
    var url = "ws://dummy.com/ws";
    var ws = new MockSocketMaker(url);
    var packets = [];
    var process_packet = function(packet) {
        packets.push(packet);
    };
    var packet_limit = 4;
    var packer = new h5.Packer(ws, process_packet, packet_limit);
    var message = "01234hello_world";
    var chunks = [
        "C0123",
        "C4hel",
        "Clo_w",
        "Forld",
        ];
    packer.send_unicode(message);
    expect(packer.ws.sends).toEqual(chunks);
});

test('rejects bad send', () => {
    var h5 = H5Gizmos;
    var url = "ws://dummy.com/ws";
    var ws = new MockSocketMaker(url);
    var packets = [];
    var process_packet = function(packet) {
        packets.push(packet);
    };
    var packet_limit = 4;
    var socketMaker = MockSocketMaker;
    var packer = new h5.Packer(ws, process_packet, packet_limit);
    //expect(packer.ws_url).toEqual(url);
    var message1 = "123"
    expect(function () { packer.ws.fake_receive("*" + message1) }).toThrow();
});

test('parses unicode JSON', () => {
    var h5 = H5Gizmos;
    var unicode = '{"name":"John", "age":30, "city":"New York"}';
    var json_ob = {"name":"John", "age":30, "city":"New York"};
    var got_json = null;
    var process_json = function(json_ob) {
        got_json = json_ob;
    };
    var sent_unicode = null;
    var send_unicode = function(str) {
        sent_unicode = str;
    };
    var error_message = null;
    var on_error = function(message, error) {
        error_message = message;
    };
    var codec = new h5.JSON_Codec(process_json, send_unicode, on_error);
    codec.receive_unicode(unicode);
    expect(got_json).toEqual(json_ob);
});

test('errors bad unicode JSON', () => {
    var h5 = H5Gizmos;
    var unicode = '{"name":"John", "age":30, "city":"New York"}';
    var json_ob = {"name":"John", "age":30, "city":"New York"};
    var got_json = null;
    var process_json = function(json_ob) {
        got_json = json_ob;
    };
    var sent_unicode = null;
    var send_unicode = function(str) {
        sent_unicode = str;
    };
    var error_message = null;
    var on_error = function(message, error) {
        error_message = message;
    };
    var codec = new h5.JSON_Codec(process_json, send_unicode, on_error);
    expect(function () { codec.receive_unicode("xxx" + unicode); }).toThrow();
    expect(error_message).not.toEqual(null);
    expect(got_json).toEqual(null);
});

test('encodes JSON objects', () => {
    var h5 = H5Gizmos;
    //var unicode = '{"name":"John", "age":30, "city":"New York"}';
    var json_ob = {"name":"John", "age":30, "city":"New York"};
    var unicode = JSON.stringify(json_ob);
    var got_json = null;
    var process_json = function(json_ob) {
        got_json = json_ob;
    };
    var sent_unicode = null;
    var send_unicode = function(str) {
        sent_unicode = str;
    };
    var error_message = null;
    var on_error = function(message, error) {
        error_message = message;
    };
    var codec = new h5.JSON_Codec(process_json, send_unicode, on_error);
    codec.send_json(json_ob);
    expect(sent_unicode).toEqual(unicode);
});

test('fails to encode bad JSON objects', () => {
    var h5 = H5Gizmos;
    //var unicode = '{"name":"John", "age":30, "city":"New York"}';
    var json_ob = function (x) { return x + 1; }
    //var unicode = JSON.stringify(json_ob);
    var got_json = null;
    var process_json = function(json_ob) {
        got_json = json_ob;
    };
    var sent_unicode = null;
    var send_unicode = function(str) {
        sent_unicode = str;
    };
    var error_message = null;
    var on_error = function(message, error) {
        error_message = message;
    };
    var codec = new h5.JSON_Codec(process_json, send_unicode, on_error);
    expect(function () { codec.send_json(json_ob); }).toThrow();
    expect(sent_unicode).toEqual(null);
});

test('pipelines a received message', () => {
    var h5 = H5Gizmos;
    var url = "ws://dummy.com/ws";
    var ws = new MockSocketMaker(url);
    var sender = null;  // overridden by pipeline
    var dthis = {};
    var tr = new h5.Translator(dthis, sender);
    var pipeline = h5.pipeline(ws, tr);
    // encapsulate a command
    var val = ["some", "value"];
    var json_cmd = lit(val); //[h5.LITERAL, val];
    //var json_msg = get(json_cmd); //[h5.EXEC, json_cmd];
    var oid = "abc";
    var depth = 5;
    var json_msg = get(oid, json_cmd, depth)
    var json_packet = h5.FINISHED_UNICODE + JSON.stringify(json_msg);
    ws.fake_receive(json_packet);
    var expect_ob = ["G", "abc", ["some", "value"]];
    var expect_packet = "F" + JSON.stringify(expect_ob);
    expect(ws.sends).toEqual([expect_packet]);
});

test("doesn't pipeline a bad message.", () => {
    var h5 = H5Gizmos;
    var url = "ws://dummy.com/ws";
    var ws = new MockSocketMaker(url);
    var sender = null;  // overridden by pipeline
    var dthis = {};
    var tr = new h5.Translator(dthis, sender);
    var pipeline = h5.pipeline(ws, tr);
    // encapsulate a command
    var val = ["some", "value"];
    var json_cmd = lit(val); //[h5.LITERAL, val];
    //var json_msg = get(json_cmd); //[h5.EXEC, json_cmd];
    var oid = "abc";
    var depth = 5;
    var json_msg = get(oid, json_cmd, depth)
    var json_packet = h5.FINISHED_UNICODE + JSON.stringify(json_msg) + "oops";
    expect(function () { ws.fake_receive(json_packet); }).toThrow();
    expect(ws.sends.length).toEqual(1);
    var packet = ws.sends[0];
    expect(packet.substring(0,1)).toEqual("F");
    var json_str = packet.substring(1);
    var json_reply = JSON.parse(json_str);
    expect(json_reply[0]).toEqual(h5.EXCEPTION);
});

test("makes a function.", () => {
    var h5 = H5Gizmos;
    var names = ["v1", "v2", "v3"];
    var body = `
        var x = v1 + v2;
        return x * v3;
    `;
    var f = h5.Function(names, body);
    var r = f(5,4,3);
    expect(r).toEqual((4 + 5) * 3);
});

test("executes New.", () => {
    var h5 = H5Gizmos;
    var args = ["v1", "v2", "v3"];
    var body = `
        var x = v1 + v2;
        return x * v3;
    `;
    args.push(body);
    var f = h5.New(Function, args);
    var r = f(5,4,3);
    expect(r).toEqual((4 + 5) * 3);
});
