
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
    h5.EXCEPTION = "X";
    h5.KEEPALIVE = "K";
    h5.RECONNECT_ID = "reconnect_id";
    h5.ACKNOWLEDGE = "A";

    // Limit for websocket packets
    h5.PACKET_LIMIT = 500000;  // half a meg

    const ws_open = 1;

    var indicator_to_message_parser = {};
    var indicator_to_command_parser = {};

    class Translator {
        constructor(default_this, sender, log_messages) {
            this.default_this = default_this;
            this.sender = sender;
            this.log_messages = log_messages;
            this.object_cache = {};
            this.ws_url = null;
            this.ws = null;
            this.reconnect_id = "" + Date.now();
            this.ws_error_message_callback = null;
            this.sending_keepalives = false;
            this.halted = false;
            this.reconnect_count = 0;
            this.reconnect_limit = 10;
            // modules cache
            this.modules = {};
        };
        cache_promise_result(identifier, promise, on_resolve, on_reject) {
            var that = this;
            function onFullfilled(value) {
                that.object_cache[identifier] = value;
                if (on_resolve) {
                    on_resolve();  // don't automatically send value, use cache.
                }
            };
            function onRejected(reason) {
                if (on_reject) {
                    on_reject(reason);
                }
            };
            promise.then(onFullfilled, onRejected);
        };
        shutdown() {
            console.log("Shutting down gizmo.")
            this.halted = true;
        }
        pipeline_websocket(ws_url, on_open) {
            var that = this;
            that.ws_url = ws_url;
            var ws = new WebSocket(ws_url);
            that.ws = ws;
            that.pipeline = pipeline(ws, this);
            ws.onerror = function(event) {
                that.web_socket_error(event)
            };
            if (on_open) {
                ws.onopen = function () {
                    console.log("ws open", ws.readyState, ws_url);
                    on_open();
                }
            }
        };
        web_socket_error(event) {
            console.error("Web socket error", event);
            if (this.halted) {
                console.error("Not reporting error -- gizmo is halted.");
                throw new Error("Web socket error on halted gizmo.")
            }
            var cb = this.ws_error_message_callback;
            if (cb) {
                var message = "Web socket error."
                var ws = this.ws;
                if ((ws) && (ws.readyState != ws_open)) {
                    message = "Web socket connection is not open. Is this a duplicate connection?" + ws.readyState;
                }
                cb(message)
            }
        }
        get_ws_url(location) {
            location = location || window.location;
            var path_split = location.pathname.split("/");
            var ws_path_split = path_split.slice(0, path_split.length - 1);
            var i = ws_path_split.length - 2;
            //c.l("fixing path", ws_path_split);
            if (ws_path_split[i] == "http") {
                ws_path_split[i] = "ws"
            }
            var ws_path = ws_path_split.join("/");
            var reconnect_parameter = "?" + h5.RECONNECT_ID + "=" + this.reconnect_id;
            var protocol = window.location.protocol;
            console.log("location protocol is", protocol)
            // https://stackoverflow.com/questions/10406930/how-to-construct-a-websocket-uri-relative-to-the-page-uri
            var wsprotocol = "ws:";
            if (protocol.startsWith("https")) {
                // use secure connection if main page is secure.
                wsprotocol = "wss:"
            }
            var url = wsprotocol + "//" + location.host + ws_path + reconnect_parameter;
            console.log("ws url", url)
            return url;
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
            var that = this;
            // need to send halt confirmation.
            //if (this.halted) {
            //    throw new Error("Send refused because gizmo is halted.");
            //}
            var on_open = function() {
                that.sender(json_object);
            };
            if (this.log_messages) {
                console.log("sending json", json_object);
            }
            that.check_web_socket(on_open);
            //this.sender(json_object);
        };
        check_web_socket(on_open) {
            var ws = this.ws;
            if ((!ws) || (!this.ws_url)) {
                throw new Error("ws connection is not configured.  Cannot reconnect.")
            }
            if (ws.readyState != ws_open) {
                // always log reconnect attempts?
                this.reconnect_count += 1;
                if (this.reconnect_limit > 0) {
                    if (this.reconnect_count > this.reconnect_limit) {
                        console.error("Not attempting to reconnect, limit exceeded", this.reconnect_count)
                        throw new Error("Not reconnecting after too many reconnect attempts")
                    }
                }
                console.log("attempting to reconnect ws:", ws.readyState, this.reconnect_count)
                this.pipeline_websocket(this.ws_url, on_open);
            } else {
                this.reconnect_count = 0;
                on_open();
            }
        }
        send_error(message, err, oid) {
            if (!err) {
                err = new Error(message);
                message = "Error in Gizmo message processing."
            }
            if (!oid) {
                oid = null; 
            }
            var json = [h5.EXCEPTION, "" + err, oid];
            if (!this.halted) {
                this.send(json);
            }
            throw err;
        };
        post_binary_data(end_point, binary_data, json_metadata) {
            var that = this
            if (this.halted) {
                throw new Error("Refusing to post binary data because gizmo is halted.")
            }
            json_metadata = json_metadata || {};
            var json = JSON.stringify(json_metadata);
            var query_string = "?json=" + encodeURIComponent(json)
            var url = end_point + query_string;
    
            // https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/send
            var xhr = new XMLHttpRequest();
            xhr.open("POST", url, true);
    
            //Send the proper header information along with the request
            xhr.setRequestHeader("Content-Type", "application/octet-stream");
    
            xhr.onreadystatechange = function() {
                if (this.readyState === XMLHttpRequest.DONE && this.status === 200) {
                    // Request finished. Do processing here.
                    //c.l("request finished", xhr)
                    // The POST is for sending data -- reply is ignored if not in error.
                } else if (this.readyState === XMLHttpRequest.DONE) {
                    var status = this.status;
                    that.send_error("Bad status sent for POST: " + status);
                }
            }
            xhr.send(binary_data);
        };
        send_keepalive() {
            // Send a keepalive message to force a reconnect if the connection drops.
            // The message should be ignored by the parent.
            if (this.halted) {
                throw new Error("Refusing to send keepalive because gizmo is halted.")
            }
            this.send([h5.KEEPALIVE]);
        };
        send_keepalive_periodically (delay) {
            delay = delay || 1000;
            var that = this;
            if (that.sending_keepalives) {
                console.log("Not restarting keepalive send loop.  Already sending.");
                return;
            }
            var keep_sending = function () {
                //c.l("DEBUG: sending keepalive.")
                if (this.halted) {
                    throw new Error("Erroring keepalive loop because gizmo is halted.")
                }
                that.sending_keepalives = true;
                that.send_keepalive();
                setTimeout(keep_sending, delay);
            };
            that.sending_keepalives = true;
            setTimeout(keep_sending, delay);
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
            if (this.log_messages) {
                console.log("parsing json message", message_json_ob);
            }
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
        handle_message(message_json_ob) {
            var msg = this.parse_message(message_json_ob);
            //cl("executing msg", msg)
            return msg.execute(this);
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
            this.op = "EXEC";
            this.translator = translator;
            this.json_payload = payload;
            this.oid = null;  // default
            this.parse(translator, payload);
            this.value = null;
        }
        parse(translator, payload) {
            var [command] = payload;
            this.command = translator.parse_command(command);
        };
        execute(translator) {
            // return result for testing, not transmitted.
            try {
                var pair = this.command.execute(translator);
                var value = pair.value;
                if (value instanceof DeferredValue) {
                    this.bind_deferred_value(value, translator);
                } else {
                    this.resolve(value, translator);
                }
                return value;
            } catch (err) {
                this.reject(err, translator);
                throw err;
            }
        };
        resolve(value, translator) {
            this.value = value;
        };
        reject(err, translator) {
            translator.send_error("Error in " + this.op, err, this.oid)
        };
        bind_deferred_value(deferred, translator) {
            var that = this;
            deferred.bind_actions(
                (function (value) { that.resolve(value, translator); }), // resolve
                (function (err) { that.reject(err, translator); }),  // reject
            );
        };
    };
    indicator_to_message_parser[h5.EXEC] = ExecMessageParser;

    class GetMessageParser extends ExecMessageParser {
        parse(translator, payload) {
            this.op = "GET";
            var [oid, command, to_depth] = payload;
            this.oid = oid;
            //c.l("GET", this.oid, command, to_depth)
            this.command = translator.parse_command(command);
            this.to_depth = to_depth;
        };
        resolve(value, translator) {
            try {
                this.json_value = translator.json_safe(value, this.to_depth);
                this.payload = [h5.GET, this.oid, this.json_value];
                //c.l("GET resolves", this.payload)
                translator.send(this.payload);
                return value;
            } catch (err) {
                this.reject(err, translator);
                throw err;
            }
        };
        /*
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
                throw err;
            }
        };*/
    };
    indicator_to_message_parser[h5.GET] = GetMessageParser;

    class ConnectMessageParser extends ExecMessageParser {
        parse(translator, payload) {
            this.op = "CONNECT"
            var [id, command] = payload;
            this.id = id;
            this.command = translator.parse_command(command);
        };
        resolve(value, translator) {
            try {
                translator.set_reference(this.id, value);
                return value;
            } catch (err) {
                this.reject(err, translator);
                throw err;
            }
        };
        /*
        execute(translator) {
            // return result for testing, not transmitted.
            try {
                var pair = this.command.execute(translator);
                var value = pair.value;
                translator.set_reference(this.id, value);
                return value;
            } catch (err) {
                translator.send_error("Error in CONNECT", err, null);
                throw err;
            }
        }; */
    };
    indicator_to_message_parser[h5.CONNECT] = ConnectMessageParser;

    class DisconnectMessageParser extends ExecMessageParser {
        parse(translator, payload) {
            this.op = "DISCONNECT";
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
        execute(translator, to_truthy) {
            var ob = this.jsonob;
            if ((to_truthy) && (!ob)) {
                throw new Error("literal is not truthy: " + ob)
            }
            return translator.value_pair(ob);
        };
    };
    indicator_to_command_parser[h5.LITERAL] = LiteralCommandParser;

    class BytesCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [hexstr] = payload;
            this.hexstr = hexstr;
        };
        execute(translator, to_truthy) {
            // to_truthy is not relevant (?)
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
        execute(translator, to_truthy) {
            // to_truthy is not relevant (?)
            var map_commands = this.map_commands;
            var map_values = {};
            for (var attr in map_commands) {
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
        execute(translator, to_truthy) {
            // to_truthy is not relevant (?)
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
        execute(translator, to_truthy) {
            var ref = translator.get_reference(this.id_string);
            if ((to_truthy) && (!ref)) {
                throw new Error("ref " + this.id_string + " is not truthy " + ref);
            }
            return ref;
        };
    };
    indicator_to_command_parser[h5.REFERENCE] = ReferenceCommandParser;

    class GetCommandParser extends ExecMessageParser {
        parse(translator, payload) {
            var [target_command, index_command] = payload;
            this.target_command = translator.parse_command(target_command);
            this.index_command = translator.parse_command(index_command);
        };
        execute(translator, to_truthy) {
            // target must be truthy
            this.target_pair = this.target_command.execute(translator, true);
            this.index_pair = this.index_command.execute(translator);
            var target = this.target_pair.value;
            var index = this.index_pair.value;
            var value = target[index];
            if ((to_truthy) && (!value)) {
                console.log("get not truthy", target, index, value)
                throw new Error("get " + index + " from " + target + " not truthy: " + value);
            }
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
        execute(translator, to_truthy) {
            // callable must be truthy
            this.callable = this.callable_command.execute(translator, true);
            this.args = translator.execute_commands(this.args_commands);
            var args_values = translator.values_from_pairs(this.args);
            this.result = this.callable.call_with_this(args_values);
            if ((to_truthy) && (!this.result)) {
                throw new Error("call to " + this.callable + " returns falsy " + this.result);
            }
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
        execute(translator, to_truthy) {
            // to_truthy is not relevant (?)
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
        execute(translator, to_truthy) {
            // target must be truthy
            this.target_pair = this.target_command.execute(translator, true);
            this.index_pair = this.index_command.execute(translator);
            this.value_pair = this.value_command.execute(translator);
            var target = this.target_pair.value;
            var index = this.index_pair.value;
            var value = this.value_pair.value
            if ((to_truthy) && (!value)) {
                throw new Error(
                    "index " + index + " in " + target + " gives falsy " + value
                );
            }
            target[index] = value;
            return this.target_pair;  // ???
        };
    };
    indicator_to_command_parser[h5.SET] = SetCommandParser;

    function value_pair_test(ob) {
        if ((!ob) || (!ob.hasOwnProperty)) {
            return false;
        }
        return ob.hasOwnProperty("_is_value_pair");
    };

    class ThisValuePair {
        // A value paired with a "this" calling context.
        constructor(this_ob, value, default_this) {
            //if ((this_ob._is_value_pair) || (value._is_value_pair) || (default_this._is_value_pair)) {
            //    throw new Error("Do not double wrap value pairs.");
            //}
            if ((value_pair_test(this_ob)) || (value_pair_test(value)) || (value_pair_test(default_this))) {
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
    const LOCK_DELAY = 50;  // milliseconds
    const LOCK_TIMEOUT = 60000; // one minute in milliseconds

    class Packer {
        constructor(web_socket, process_packet, packet_limit) {
            var that = this;
            this.packet_limit = packet_limit || h5.PACKET_LIMIT;
            this.collector = [];
            //this.ws_url = ws_url;
            this.packet_receiver = process_packet;
            //var ws = new socketMaker(ws_url);
            this.ws = web_socket;
            this.ws.onmessage = function(event) {
                that.onmessage(event);
            };
            // only permit on send at a time.
            this.send_locked = false;
            this.resolve_acknowledgment = null;
            // xxxx add ack timestamp and ack reject loop task...
        };
        receive_acknowledgment() {
            // return a promise which resolves upon ack
            // xxxx add timeout mechanism?
            var that = this;
            if (this.resolve_acknowledgment) {
                throw new Error("Cannot await more than one ack at a time.");
            }
            return new Promise((resolve, reject) => {
                that.resolve_acknowledgment = resolve;
            });
        }
        lock_for_sending(delay, timeout) {
            var that = this;
            delay = delay || LOCK_DELAY;
            timeout = timeout || LOCK_TIMEOUT;
            //var lock_grabbed = false;
            var timed_out = false;
            const start_time = Date.now();
            function grab_lock(resolve, reject) {
                timed_out = ((Date.now() - start_time) > timeout);
                if (timed_out) {
                    return reject("lock time out.");
                }
                if (!that.send_locked) {
                    that.send_locked = true;
                    //lock_grabbed = true;
                    return resolve();
                } else {
                    // try again later
                    setTimeout(() => {
                        grab_lock(resolve, reject)
                    }, delay);
                }
            };
            return new Promise((resolve, reject) => {
                grab_lock(resolve, reject);
            });
        };
        onmessage(event) {
            //debugger;
            var data = event.data;
            ////cl("got data: ", data)
            var indicator = data.slice(0, 1);
            var payload = data.slice(1);
            var collector = this.collector;
            if (indicator == CONTINUE_UNICODE) {
                collector.push(payload);
                // send ok reply, don't worry about locking.
                //c.l("ack", collector.length);
                this.ws.send(h5.ACKNOWLEDGE);
            } else if (indicator == FINISHED_UNICODE) {
                this.collector = []
                collector.push(payload);
                var packet = collector.join("");
                ////cl("finishing: ", packet)
                this.packet_receiver(packet);
            } else if (indicator == h5.ACKNOWLEDGE) {
                const resolve = this.resolve_acknowledgment;
                this.resolve_acknowledgment = null;
                //c.l("debug got ack", data, resolve);
                if (resolve) {
                    resolve(payload);
                } else {
                    console.warn("unexpected ack", data.slice(0, 10));
                }
            } else {
                throw new Error("unknown indicator: " + data.slice(0, 10));
            }
        };
        async send_unicode(packet_unicode) {
            try {
                await this.lock_for_sending();
                await this.send_unicode_locked(packet_unicode);
            } finally {
                // release the lock
                this.send_locked = false;
            }
        };
        async send_unicode_locked(packet_unicode) {
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
                ////cl("sending data: ", data);
                ws.send(data);
                // wait for ok if not finished XXXXX
                if (!last) {
                    //c.l("debug: awaiting ack", start, ln)
                    await this.receive_acknowledgment();
                }
            }
        };
    };
    H5Gizmos.Packer = Packer;
    H5Gizmos.FINISHED_UNICODE = FINISHED_UNICODE;
    H5Gizmos.CONTINUE_UNICODE = CONTINUE_UNICODE;

    // Deferred GET -- return the result of an async operation when it arrives.
    // Return this as a value for a function to resolve the GET request later.
    //
    class DeferredValue {
        // should/could this be implemented using a Promise ???
        bind_actions(resolve_action, reject_action) {
            this.resolve_action = resolve_action;
            this.reject_action = reject_action;
        };
        resolve(value) {
            this.resolve_action(value)
        };
        reject(info) {
            this.reject_action(info)
        };
    };

    H5Gizmos.DeferredValue = DeferredValue;

    /* NOT USED
    class PromisedValue extends DeferredValue {
        // Link a JS promise to a Gizmo get request.
        constructor(promise) {
            super();
            var that = this;
            var success = function(value) { that.resolve(value); };
            var failure = function(error) { that.reject(error); };
            promise.then(success).catch(failure);
        };
    };

    H5Gizmos.PromisedValue = PromisedValue;
    */

    class StoreBlob extends DeferredValue {
        constructor(url, to_object, property_name, converter, responseType) {
            super();  // call the silly super constructor!
            this.init_local(url, to_object, property_name, converter, responseType);
        }
        init_local(url, to_object, property_name, converter, responseType) {
            var that = this;
            responseType = responseType || "blob";
            that.url = url
            that.to_object = to_object;
            that.property_name = property_name;
            that.converter = converter;
            that.binary_data = null;
            var request = new XMLHttpRequest();
            // async get
            request.open('GET', url, true);
            request.responseType = responseType;
            request.onload = (function () { that.on_request_load(request); })
            request.send();
        };
        on_request_load(request) {
            try {
                var that = this;
                var reader = new FileReader();
                reader.readAsArrayBuffer(request.response);
                reader.onload = (function () { that.on_reader_load(reader); });
            } catch (err) {
                this.reject(err);
            }
        };
        on_reader_load(reader) {
            try {
                var binary_data = reader.result;
                var converter = this.converter;
                if (converter) {
                    binary_data = new converter(binary_data);
                }
                this.binary_data = binary_data;
                this.to_object[this.property_name] = binary_data;
                this.resolve(this.binary_data.length);
            } catch (err) {
                this.reject(err);
            }
        };
    };

    H5Gizmos.store_blob = function (url, to_object, property_name, converter) {
        return new StoreBlob(url, to_object, property_name, converter);
    };

    class StoreJSON extends StoreBlob {
        constructor(url, to_object, property_name) {
            super(url, to_object, property_name, null, "json");
            this.json = null;
        };
        on_request_load(request) {
            try {
                this.json = request.response;
                this.to_object[this.property_name] = this.json;
                this.resolve(request.statusText);
            } catch (err) {
                this.reject(err);
            }
        };
    };

    H5Gizmos.store_json = function (url, to_object, property_name) {
        return new StoreJSON(url, to_object, property_name);
    };

    H5Gizmos.make_array_buffer = function (array_buffer_name, binary_data) {
        var array_buffer_class = window[array_buffer_name];
        if (!array_buffer_class) {
            throw new Error("array buffer class not found: " + array_buffer_class);
        }
        return new array_buffer_class(binary_data.buffer);
    };

    // JSON_Codec -- coder decoder
    class JSON_Codec {
        constructor(process_json, send_unicode, on_error) {
            this.process_json = process_json;
            this.send_unicode = send_unicode;
            this.on_error = on_error;
            // xxx hypothetical infinite recursion if there is bug in error processing...
        };
        receive_unicode(unicode_str) {
            //cl("codec rcv: ", unicode_str)
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

    // pipeline ... hooks everything together...
    function pipeline(from_web_socket, to_translator, packet_limit) {
        packet_limit = packet_limit || h5.PACKET_LIMIT;
        var process_json = function(json_ob) {
            //cl("process json: ", json_ob)
            to_translator.handle_message(json_ob);
        };
        var send_unicode = function(packet_unicode) {
            // async send to enable confirmation handshake for large messages.
            // XXXX
            packer.send_unicode(packet_unicode);
        };
        var in_codec_error = false;
        var on_codec_error = function(message) {
            // commented check is not needed?
            //if (in_codec_error) {
            //    throw new Error("error during error processing -- punting.")
            //}
            in_codec_error = true;
            try {
                to_translator.send_error(message);
            } finally {
                in_codec_error = false;
            }
        };
        var process_packet = function(packet) {
            //cl("process packet", packet)
            codec.receive_unicode(packet);
        };
        var send_json = function(json_ob) {
            codec.send_json(json_ob);
        };
        to_translator.sender = send_json;
        var codec = new JSON_Codec(process_json, send_unicode, on_codec_error);
        var packer = new Packer(from_web_socket, process_packet, packet_limit);
        return {
            ws: from_web_socket,
            packer: packer,
            codec: codec,
            translator: to_translator,
        }
    };

    H5Gizmos.pipeline = pipeline;

    // Conveniences
    H5Gizmos.Function = function (argument_names, body_string) {
        // https://stackoverflow.com/questions/7650071/is-there-a-way-to-create-a-function-from-a-string-with-javascript
        var args = [...argument_names];
        args.push(body_string);
        return new Function(...args);
    };

    /* commented new emulation -- doesn't seem to always work (for Chart.js, eg) see gz_components alternative
    // "new" keyword emulation
    // http://stackoverflow.com/questions/17342497/dynamically-control-arguments-while-creating-objects-in-javascript 
    H5Gizmos.New = function(klass, args) {
        var obj = Object.create(klass.prototype);
        return klass.apply(obj, args) || obj;
    };*/

    // https://stackoverflow.com/questions/22086722/resize-cross-domain-iframe-height
    H5Gizmos.periodically_send_height_to_parent = function(identifier, delay) {
        delay = delay || 1000;
        if(window.self === window.top) { 
            //c.l("gizmo not running in iframe.")
            return;
        }
        var html_element = document.getElementsByTagName("html")[0];
        if (html_element) {
            var send_height_to_parent = function () {
                var height = html_element.offsetHeight;
                var message = { identifier: identifier, height: height };
                //c.l("sending to parent", height, message);
                parent.postMessage(message, "*");
                setTimeout(send_height_to_parent, delay);
            }
            setTimeout(send_height_to_parent, delay);
        }
    };

    H5Gizmos.post_2d_canvas_image = function(
        end_point, dom_canvas, context2d, x, y, w, h, gizmo_translator) {
        // Send the image data from the canvas to the parent in a POST request
        context2d = context2d || dom_canvas.getContext("2d");
        x = x || 0;
        y = y || 0;
        w = w || dom_canvas.width;
        h = h || dom_canvas.height;
        // default to global interface
        gizmo_translator = gizmo_translator || H5GIZMO_INTERFACE;
        var image_data = context2d.getImageData(x, y, w, h);
        var json_metadata = {height: image_data.height, width: image_data.width};
        gizmo_translator.post_binary_data(end_point, image_data.data, json_metadata);
    };

    H5Gizmos.post_webgl_canvas_image = function(
        end_point, gl_context, x, y, w, h, gizmo_translator)
    {
        debugger;
        var gl = gl_context;
        x = x || 0;
        y = y || 0;
        w = w || (gl.drawingBufferWidth - x);
        h = h || (gl.drawingBufferHeight - y);
        // default to global interface
        gizmo_translator = gizmo_translator || H5GIZMO_INTERFACE;
        // https://developer.mozilla.org/en-US/docs/Web/API/WebGLRenderingContext/readPixels
        const pixels = new Uint8Array(w * h * 4);
        gl.readPixels(x, y, w, h, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
        var json_metadata = {height: h, width: w};
        gizmo_translator.post_binary_data(end_point, pixels, json_metadata);
    };

    H5Gizmos.is_loaded = true;

}) ();  // execute initialization in protected scope.

try {
    if (module !== undefined) {
        // For node/jest.
        module.exports = H5Gizmos;
    }
} catch (e) {
    // ignore any reference error
}