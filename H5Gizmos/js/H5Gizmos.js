
/*

Gizmo protocol. Child side.

Top level messages:

[EXEC, command]: 
    Evaluate command and discard result.
[GET, oid, command, to_depth]: 
    Evaluate  command and send back json converted result to depth as [GET, oid, json_value]
[CONNECT, id, command]:
    Evaluate command and cache result internally using id.
[DISCONNECT, id]:
    Uncache id.

Command formats:

[LITERAL, jsonob]
    Untranslated JSON object.
[BYTES, string]
    Hex string converted to Uint8Array.
[MAP, {name: command, ...}]
    Generate dictionary interpreting commands.
[SEQUENCE, [command, ...]]
    Generate sequence, interpreting commands.
[REFERENCE, id_string]
    Return cached object associated with id_string.
[GET, target_command, index_command]
    Index into target using index.
[CALL, callable_command, [args_command...]]
    Call callable with args (using appropriate this binding).
[CALLBACK, id_string, to_depth] 
    Create function f(arg,...) which when called sends [CALLBACK, id_string, [json_arg, ...]
    with json_args truncated to depth.
[SET, target_command, index_command, value_command]
    Index assign into target using index and value.

Exception message:
    [EXCEPTION, message, oid_or_null]
    Indicates an exception was encountered.  If oid is provided then resolve GET for that oid.
*/

var H5Gizmos = {};

(function() {
    var h5 = H5Gizmos;
    h5.EXEC = "E";
    h5.GET = "G";
    h5.CONNECT = "C";
    h5.DISCONNECT = "D";
    h5.LITERAL = "L";
    h5.BYTES = "B";
    h5.MAP = "M";
    h5.SEQUENCE = "SQ";
    h5.REFERENCE = "R";
    h5.CALL = "C";
    h5.CALLBACK = "CB";
    h5.SET = "S";
    h5.EXCEPTION = "X"

    var indicator_to_message_parser = {};
    var indicator_to_command_parser = {};

    class Translator {
        constructor(default_this, sender) {
            this.default_this = default_this;
            this.sender = sender;
            this.object_cache = {};
        };
        get_reference(id_string) {
            var obj = this.object_cache[id_string];
            if (!obj) {
                throw new Error("no such object found for id: " + id_string);
            }
            return this.value_pair(obj);
        };
        set_reference(id_string, obj) {
            this.object_cache[id_string] = obj;
        };
        forget_reference(id_string) {
            delete this.object_cache[id_string];
        };
        send(json_object) {
            this.sender(json_object);
        };
        send_error(message, err, oid) {
            if (!err) {
                err = new Error(message);
                message = "Error in Gizmo message processing."
            }
            if (!oid) {
                oid = null; 
            }
            var json = [h5.EXCEPTION, "" + err, oid];
            this.send(json);
            throw err;
        };
        json_safe(val, depth) {
            // convert value to acceptible JSON  value truncated at depth
            var that = this;
            var ty = (typeof val);
            if ((ty == "number") || (ty == "string") || (ty == "boolean")) {
                return val;
            }
            if ((val instanceof Uint8Array) || (val instanceof Uint8ClampedArray)) {
                // send as hexidecimal string for uint arrays
                return this.to_hex(val);
            }
            if (!val) {
                // translate all other falsies to null
                return null;
            }
            if (((typeof depth) == "number") && (depth > 0)) {
                if (Array.isArray(val)) {
                    var result = [];
                    val.forEach(function(elt, i) {
                        var r = that.json_safe(elt, depth-1);
                        //if (r != null) {
                        result[i] = r;
                        //}
                    });
                    return result;
                } else {
                    var result = {};
                    for (var key in val) {
                        var jv = that.json_safe(val[key], depth-1);
                        //if (jv != null) {
                        result[key] = jv;
                        //}
                    }
                    return result;
                }
            }
            return null;
        };
        to_hex(int8array) {
            var length = int8array.length;
            var hex_array = Array(length);
            for (var i=0; i<length; i++) {
                var b = int8array[i];
                var h = b.toString(16);
                if (h.length==1) {
                    h = "0" + h
                }
                hex_array[i] = h;
            }
            return hex_array.join("");
        };
        from_hex(hexstr) {
            var length2 = hexstr.length;
            if ((length2 % 2) != 0) {
                throw new Error("hex string length must be multiple of 2");
            }
            var length = length2 / 2;
            var result = new Uint8Array(length);
            for (var i=0; i<length; i++) {
                var i2 = 2 * i;
                var h = hexstr.substring(i2, i2+2);
                var b = parseInt(h, 16);
                result[i] = b;
            }
            return result;
        };
        parse_message(message_json_ob) {
            if (!Array.isArray(message_json_ob)) {
                this.send_error("top level message json should be array: " + (typeof message_json_ob));
            }
            var remainder = message_json_ob.slice();
            var indicator = remainder[0];
            remainder.shift();
            var Parser = indicator_to_message_parser[indicator];
            if (!Parser) {
                this.send_error("No message parser for indicator: " + indicator);
            }
            try {
                return new Parser(this, remainder);
            } catch (err) {
                this.send_error("failed to parse message", err)
            }
        };
        parse_command(command_json_ob) {
            if (!Array.isArray(command_json_ob)) {
                this.send_error("top level message json should be array: " + (typeof command_json_ob));
            }
            var remainder = command_json_ob.slice();
            var indicator = remainder[0];
            remainder.shift();
            var Parser = indicator_to_command_parser[indicator];
            if (!Parser) {
                this.send_error("No command parser for indicator: " + indicator);
            }
            // exceptions should be caught in calling parse_message (?)
            return new Parser(this, remainder);
        };
        parse_commands(commands_json_obs) {
            var result = [];
            for (var i=0; i<commands_json_obs.length; i++) {
                var json_ob = commands_json_obs[i];
                var c = this.parse_command(json_ob);
                result.push(c);
            }
            return result;
        };
        execute_commands(commands) {
            var result = [];
            for (var i=0; i<commands.length; i++) {
                var c = commands[i];
                var e = c.execute(this);
                result.push(e);
            }
            return result;
        };
        execute_command(command) {
            // execute command and catch exceptions
            try {
                return command.execute(this);
            } catch (err) {
                this.send_error("exception in command execution", err);
            }
        };
        this_value_pair(this_ob, this_value) {
            return new ThisValuePair(this_ob, this_value, this.default_this);
        };
        value_pair(obj) {
            var default_this = this.default_this;
            return new ThisValuePair(default_this, obj, default_this);
        };
        values_from_pairs(pairs) {
            var result = [];
            for (var i=0; i<pairs.length; i++) {
                result.push(pairs[i].value);
            }
            return result;
        };
    };
    h5.Translator = Translator;

    // Messages
    class ExecMessageParser {
        constructor(translator, payload) {
            this.translator = translator;
            this.json_payload = payload;
            this.parse(translator, payload);
        }
        parse(translator, payload) {
            var [command] = payload;
            this.command = translator.parse_command(command);
        };
        execute(translator) {
            // return result for testing, not transmitted.
            var pair = this.command.execute(translator);
            return pair.value;
        };
    };
    indicator_to_message_parser[h5.EXEC] = ExecMessageParser;

    class GetMessageParser extends ExecMessageParser {
        parse(translator, payload) {
            var [oid, command, to_depth] = payload;
            this.oid = oid;
            this.command = translator.parse_command(command);
            this.to_depth = to_depth;
        };
        execute(translator) {
            // execute command and resolve, or resolve with an exception.
            try {
                var pair = this.command.execute(translator);
                var value = pair.value;
                this.json_value = this.translator.json_safe(value, this.to_depth);
                this.payload = [h5.GET, this.oid, this.json_value];
                translator.send(this.payload);
                return value;
            } catch (err) {
                translator.send_error("Error executing GET", err, this.oid);
            }
        };
    };
    indicator_to_message_parser[h5.GET] = GetMessageParser;

    class ConnectMessageParser extends ExecMessageParser {
        parse(translator, payload) {
            var [id, command] = payload;
            this.id = id;
            this.command = translator.parse_command(command);
        };
        execute(translator) {
            // return result for testing, not transmitted.
            var pair = this.command.execute(translator);
            var value = pair.value;
            translator.set_reference(this.id, value);
            return value;
        };
    };
    indicator_to_message_parser[h5.CONNECT] = ConnectMessageParser;

    class DisconnectMessageParser extends ExecMessageParser {
        parse(translator, payload) {
            var [id] = payload;
            this.id = id;
        };
        execute(translator) {
            // return result for testing, not transmitted.
            translator.forget_reference(this.id);
            return this.id
        };
    };
    indicator_to_message_parser[h5.DISCONNECT] = DisconnectMessageParser;

    // COMMANDS
    class LiteralCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [jsonob] = payload;
            this.jsonob = jsonob;
        };
        execute(translator) {
            return translator.value_pair(this.jsonob);
        };
    };
    indicator_to_command_parser[h5.LITERAL] = LiteralCommandParser;

    class BytesCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [hexstr] = payload;
            this.hexstr = hexstr;
        };
        execute(translator) {
            this.binary = translator.from_hex(this.hexstr);
            return translator.value_pair(this.binary);
        };
    };
    indicator_to_command_parser[h5.BYTES] = BytesCommandParser;

    class MapCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [mapjson] = payload;
            this.mapjson = mapjson;
            var map_commands = {};
            for (var attr in mapjson) {
                var json_cmd = mapjson[attr];
                map_commands[attr] = translator.parse_command(json_cmd);
            }
            this.map_commands = map_commands;
        };
        execute(translator) {
            var map_commands = this.map_commands;
            var map_values = {};
            for (var attr in map_commands) {
                var cmd = map_commands[attr];
                var pair = cmd.execute(translator);
                var value = pair.value;
                map_values[attr] = value;
            }
            return translator.value_pair(map_values);
        };
    };
    indicator_to_command_parser[h5.MAP] = MapCommandParser;

    class SequenceCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [sequence] = payload;
            this.commands = translator.parse_commands(sequence);
        };
        execute(translator) {
            this.value_pairs = translator.execute_commands(this.commands);
            var values = translator.values_from_pairs(this.value_pairs);
            return translator.value_pair(values);
        };
    };
    indicator_to_command_parser[h5.SEQUENCE] = SequenceCommandParser;

    class ReferenceCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [id_string] = payload;
            this.id_string = id_string;
        };
        execute(translator) {
            return translator.get_reference(this.id_string);
        };
    };
    indicator_to_command_parser[h5.REFERENCE] = ReferenceCommandParser;

    class GetCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [target_command, index_command] = payload;
            this.target_command = translator.parse_command(target_command);
            this.index_command = translator.parse_command(index_command);
        };
        execute(translator) {
            this.target_pair = this.target_command.execute(translator);
            this.index_pair = this.index_command.execute(translator);
            var target = this.target_pair.value;
            var index = this.index_pair.value;
            var value = target[index];
            this.result = translator.this_value_pair(target, value);
            return this.result;
        };
    };
    indicator_to_command_parser[h5.GET] = GetCommandParser;

    class CallCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [callable_command, args_commands] = payload;
            this.callable_command = translator.parse_command(callable_command)
            this.args_commands = translator.parse_commands(args_commands);
        };
        execute(translator) {
            this.callable = this.callable_command.execute(translator);
            this.args = translator.execute_commands(this.args_commands);
            var args_values = translator.values_from_pairs(this.args);
            this.result = this.callable.call_with_this(args_values);
            return this.result;
        };
    };
    indicator_to_command_parser[h5.CALL] = CallCommandParser;

    class CallbackCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [id_string, to_depth] = payload;
            this.id_string = id_string;
            this.to_depth = to_depth;
        };
        execute(translator) {
            var to_depth = this.to_depth;
            var id_string = this.id_string;
            var that = this;
            var callback_function = function(...args) {
                var json_args = [];
                for (var i=0; i<args.length; i++) {
                    var jsoni = translator.json_safe(args[i], to_depth);
                    json_args.push(jsoni);
                }
                var payload = [h5.CALLBACK, id_string, json_args];
                translator.send(payload);
                return payload;
            };
            return translator.value_pair(callback_function);
        };
    };
    indicator_to_command_parser[h5.CALLBACK] = CallbackCommandParser;

    class SetCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [target_command, index_command, value_command] = payload;
            this.target_command = translator.parse_command(target_command);
            this.index_command = translator.parse_command(index_command);
            this.value_command = translator.parse_command(value_command);
        };
        execute(translator) {
            this.target_pair = this.target_command.execute(translator);
            this.index_pair = this.index_command.execute(translator);
            this.value_pair = this.value_command.execute(translator);
            var target = this.target_pair.value;
            var index = this.index_pair.value;
            var value = this.value_pair.value
            target[index] = value;
            return this.target_pair;  // ???
        };
    };
    indicator_to_command_parser[h5.SET] = SetCommandParser;

    class ThisValuePair {
        // A value paired with a "this" calling context.
        constructor(this_ob, value, default_this) {
            if ((this_ob._is_value_pair) || (value._is_value_pair) || (default_this._is_value_pair)) {
                throw new Error("Do not double wrap value pairs.");
            }
            this.this_ob = this_ob;
            this.value = value;
            this.default_this = default_this;
            this._is_value_pair = true;
        };
        /*
        set(map_value) {
            var this_ob = this.this_ob;
            var value = this.value;
            this_ob[value] = map_value;
            return this;
        };
        get() {
            var this_ob = this.this_ob;
            var value = this.value;
            var result = this_ob[value];
            return ThisValuePair(this.default_this, result);
        };
        */
        call_with_this(args) {
            var this_ob = this.this_ob;
            var value = this.value;
            var result = value.apply(this_ob, args);
            return new ThisValuePair(this.default_this, result, this.default_this);
        };
    };

    const FINISHED_UNICODE = "F";
    const CONTINUE_UNICODE = "C";

    class Packer {
        constructor(web_socket, process_packet, packet_limit) {
            var that = this;
            this.packet_limit = packet_limit || 1000000;
            this.collector = [];
            //this.ws_url = ws_url;
            this.packet_receiver = process_packet;
            //var ws = new socketMaker(ws_url);
            this.ws = web_socket;
            this.ws.onmessage = function(event) {
                that.onmessage(event);
            };
        };
        onmessage(event) {
            //debugger;
            var data = event.data;
            //console.log("got data: ", data)
            var indicator = data.slice(0, 1);
            var payload = data.slice(1);
            var collector = this.collector;
            if (indicator == CONTINUE_UNICODE) {
                collector.push(payload);
            } else if (indicator == FINISHED_UNICODE) {
                this.collector = []
                collector.push(payload);
                var packet = collector.join("");
                //console.log("finishing: ", packet)
                this.packet_receiver(packet);
            } else {
                throw new Error("unknown indicator: " + data.slice(0, 10));
            }
        };
        send_unicode(packet_unicode) {
            var ln = packet_unicode.length;
            var limit = this.packet_limit;
            var ws = this.ws;
            for (var start=0; start<ln; start+=limit) {
                var end = start + limit;
                var chunk = packet_unicode.slice(start, end);
                var last = (end >= ln);
                var indicator = CONTINUE_UNICODE;
                if (last) {
                    indicator = FINISHED_UNICODE;
                }
                var data = indicator + chunk;
                //console.log("sending data: ", data);
                ws.send(data);
            }
        };
    };
    H5Gizmos.Packer = Packer;
    H5Gizmos.FINISHED_UNICODE = FINISHED_UNICODE;
    H5Gizmos.CONTINUE_UNICODE = CONTINUE_UNICODE;

    // JSON_Codec -- coder decoder
    class JSON_Codec {
        constructor(process_json, send_unicode, on_error) {
            this.process_json = process_json;
            this.send_unicode = send_unicode;
            this.on_error = on_error;
            // xxx hypothetical infinite recursion if there is bug in error processing...
        };
        receive_unicode(unicode_str) {
            var json_ob = null;
            try {
                json_ob = JSON.parse(unicode_str);
            } catch (err) {
                if (this.on_error) {
                    var s = "" + unicode_str;
                    this.on_error("Failed to parse JSON: " + s.substring(0, 50))
                }
                throw err;
            }
            this.process_json(json_ob);
        };
        send_json(json_ob) {
            var unicode = null;
            try {
                unicode = JSON.stringify(json_ob);
                if (!unicode) {
                    throw new Error("JSON.stringify returned falsy.")
                }
            } catch (err) {
                var s = "" + json_ob;
                if (this.on_error) {
                    this.on_error("Failed to encode JSON: " + s.substring(0, 50));
                }
                throw err;
            }
            this.send_unicode(unicode);
        };
    };
    H5Gizmos.JSON_Codec = JSON_Codec;
    // Pipeline ... hooks everything together...

    H5Gizmos.is_loaded = true;

}) ();  // execute initialization in protected scope.

if (module !== undefined) {
    // For node/jest.
    module.exports = H5Gizmos;
}