
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
    expect(() => { tr.get_reference("thing"); }).toThrow()
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

test("parses a literal", () => {
    var h5 = H5Gizmos;
    var dthis = {};
    var save_message = null;
    var sender = function(message) {
        save_message = message;
    };
    var tr = new h5.Translator(dthis, sender);
    var val = ["some", "value"];
    var json_cmd = [h5.LITERAL, val];
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
    var json_cmd = [h5.LITERAL, val];
    var json_msg = [h5.EXEC, json_cmd];
    var msg = tr.parse_message(json_msg);
    var exec = msg.execute(tr);
    expect(exec).toEqual(val);
});
