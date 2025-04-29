"""

Gizmo protocol.  Parent side.

See js/H5Gizmos.js for protocol JSON formats.

"""

import os
import time
import numpy as np
import json
import asyncio
import aiohttp
import sys, traceback
import contextlib

from .hex_codec import bytearray_to_hex
from aiohttp import web
from . import gz_resources
from . import gizmo_server

# Max size of packet sent over web socket.
PACKET_LIMIT = 500000 # half a meg

# Default wait time for JS future values.
DEFAULT_TIMEOUT = 10


def do(link_action, to_depth=None):
    "Run the link in javascript and discard the result."
    # command style convenience convenience accessor
    return link_action._exec(to_depth=to_depth)

async def js_await(promise_reference, get_result=True, to_depth=None):
    """
    Await promise, 
    dispose of result reference, 
    optionally return resolved value.
    """
    result = None
    result_ref = await wait_for(promise_reference, to_depth=to_depth)
    if get_result:
        result = await get(result_ref, to_depth=to_depth)
    result_ref._disconnect()
    return result

async def wait_for(promise_reference, to_depth=None):
    "await the promise_reference, return a cached reference to resolution."
    gz = promise_reference._owner_gizmo
    return await gz._js_await(promise_reference, to_depth=to_depth)

async def get(link_action, to_depth=None, timeout=DEFAULT_TIMEOUT):
    "Run the link in javascript and return the result."
    # command style convenience convenience accessor
    return await link_action._get(to_depth=to_depth, timeout=timeout)

def name(id, link_action, to_depth=None):
    "Run the link in javascript and cache the result using the id."
    # command style convenience convenience accessor
    return link_action._connect(id, to_depth=to_depth)

def unname(cache_ref):
    "uncache the object associated with the cache_ref"
    cache_ref._disconnect()

def new_identifier(prefix="Gizmo"):
    Gizmo.COUNTER += 1
    c = Gizmo.COUNTER
    t = int(time.time() * 1000)
    return "%s_%s_%s" % (prefix, t, c)

FORBIDDEN_BROWSERS = ["lynx"]

def check_browser():
    import webbrowser
    try:
        name = webbrowser.get().name
        if name in FORBIDDEN_BROWSERS:
            raise SystemError("Cannot browse: This browser is not supported: " + repr(name))
    except AttributeError:
        pass  # no name


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
    KEEPALIVE = "K"
    RECONNECT_ID = "reconnect_id"
    ACKNOWLEDGE = "A"

    # default slot -- override this to optimize transfers of 1-d numeric arrays
    _translate_1d_array = None

    def __init__(
        self, 
        sender=None, 
        default_depth=3, 
        pipeline=None, 
        server=None, 
        exit_on_disconnect=False,
        log_messages=False,
        # file-like where to send callback Prints (set to false to send to server log StringIO)
        callback_stdout=None,
        template=None,
        ):
        self.template = template
        self._log_messages = log_messages
        self._exit_on_disconnect = exit_on_disconnect
        self._identifier = self._new_identifier_string()
        self._pipeline = pipeline
        self._sender = sender
        #self._server = server
        self._url_prefix = None
        self._default_depth = default_depth
        self._call_backs = {}
        self._callable_to_oid = {}
        self._counter = 0
        self._oid_to_get_futures = {}
        self._initial_references = {}
        self._on_exception = None
        self._last_exception_payload = None
        self._manager = None
        self._server = None  # server string like "192.168.1.173"
        self._port = None
        #self._entry_url = None
        #self._ws_url = None
        self._html_page = None
        self.print_callback_exception = True
        self._filename = None
        self._exception_loop_test_flag = False
        self._unreported_exception_payload = None
        self._embedded_components = set()
        self._out = None
        if callback_stdout != False:
            if callback_stdout is None:
                self._out = contextlib.redirect_stdout(sys.stdout)
            else:
                self._out = contextlib.redirect_stdout(callback_stdout)
        self._err = None
        self._start_confirm_future = make_future()
        self._confirmation_underway = False

    COUNTER = 0

    def _new_identifier_string(self, prefix="Gizmo"):
        return new_identifier(prefix)

    def _check_last_flush_queue_task(self):
        if self._pipeline is not None:
            self._pipeline.check_last_flush_queue_task()

    def _do(self, link_action, to_depth=None):
        "Run the link in javascript and discard the result."
        # gizmo object convenience accessor
        return do(link_action, to_depth=to_depth)

    async def _get(self, link_action, to_depth=None):
        "Run the link in javascript and return the result."
        # gizmo object convenience accessor
        return await get(link_action, to_depth=to_depth)

    def _name(self, id, link_action, to_depth=None):
        "Run the link in javascript and cache the result using the id."
        # gizmo object convenience accessor
        return name(id, link_action, to_depth=to_depth)

    async def _awaitable_flush(self):
        await self._pipeline.packer.awaitable_flush()

    def _configure_entry_page(self, title="Gizmo", filename="index.html"):
        self._filename = filename
        mgr = self._manager
        assert mgr is not None, "manager must be set before page configuration."
        #ws_url = mgr.local_url(for_gizmo=self, method="ws", filename=None)
        #if ws_url.startswith("http:"):
        #    ws_url = "ws:" + ws_url[5:]
        #self._ws_url = ws_url
        handler = self._html_page = gz_resources.HTMLPage(
            #ws_url=self._ws_url, 
            title=title,
            template=self.template,
            identifier=self._identifier,
            log_messages=self._log_messages,
            )
        mgr.add_http_handler(filename, handler)
        self._js_file("../../H5Gizmos/js/H5Gizmos.js")
        #self._entry_url = mgr.local_url(for_gizmo=self, method="http", filename=filename)

    def _entry_url(self, proxy=False):
        gizmo_link = None
        if proxy:
            gizmo_link = "GizmoLink"
        return self._manager.local_url(
            for_gizmo=self, 
            method="http", 
            filename=self._filename,
            gizmo_link=gizmo_link,
            )

    #def __call__(self, new_page=True):
    #    return self.open_in_browser(server, new_page=new_page)

    async def start_in_browser(self, new_page=True, proxy=False):
        await self._open_in_browser(new_page=new_page, proxy=proxy)
        await self._has_started()

    async def start_in_iframe(self, height=20, proxy=False):
        assert gizmo_server.isnotebook(), "Iframe interface only runs in a Jupyter IPython notebook."
        await self._open_in_jupyter_iframe(height=height, proxy=proxy)
        await self._has_started()

    async def _has_started(self):
        """
        Use a round trip call/callback to the Javascript front end
        to confirm that communication is established.
        Call this after the Javascript front end has been set up.
        """
        #p("_has_started round trip test initializing...")
        # Await callback confirmation
        #self._start_confirm_future = make_future()
        confirm = self._start_confirm_future
        if not self._confirmation_underway:
            self._confirmation_underway = True
            callback = GizmoCallback(self._confirm_start, self)
            call_callback = GizmoCall(callback, [], self)
            do(call_callback)
            if self._exit_on_disconnect:
                self._start_heartbeat()
        await self._start_confirm_future
        return self._start_confirm_future.result()

    _heartbeat_interval_seconds = 0.5
    _heartbeat_check_seconds = 3.0

    def _start_heartbeat(self, interval_seconds=None, check_seconds=None):
        interval_seconds = interval_seconds or self._heartbeat_interval_seconds
        check_seconds = check_seconds or self._heartbeat_check_seconds
        schedule_task(self._trigger_heartbeat(interval_seconds))
        # https://quantlane.com/blog/ensure-asyncio-task-exceptions-get-logged/
        check_task = schedule_task(self._check_heartbeat(check_seconds))
        check_task.add_done_callback(self._handle_heart_stop)

    def _handle_heart_stop(self, check_task, verbose=False):
        if verbose:
            print("heart stopped!")
        try:
            check_task.result()
        except asyncio.CancelledError:
            if verbose:
                print("gizmo heartbeat task cancelled.")
        except SystemExit:
            if verbose:
                print("gizmo heartbeat task exited.")
        else:
            raise

    _heartbeat_detected = True
    _keep_heart_beating = True

    def _detect_heartbeat(self, verbose=False):
        if verbose:
            print("   Heartbeat felt.")
        self._heartbeat_detected = True

    async def _trigger_heartbeat(self, interval_seconds, verbose=False):
        callback = GizmoCallback(self._detect_heartbeat, self)
        call_callback = GizmoCall(callback, [], self)
        while self._keep_heart_beating:
            if verbose:
                print("Triggering heartbeat")
            do(call_callback)
            await asyncio.sleep(interval_seconds)

    async def _check_heartbeat(self, check_seconds, verbose=False):
        while self._keep_heart_beating:
            self._heartbeat_detected = False
            await asyncio.sleep(check_seconds)
            if verbose:
                print("Checking for heartbeat.")
            if self._keep_heart_beating and not self._heartbeat_detected:
                if verbose:
                    print("No heartbeat detected.")
                # xxxx maybe shoule add a callback here...
                if self._exit_on_disconnect:
                    sys.exit()
    
    def _confirm_start(self):
        self._start_confirm_future.set_result(True)

    async def _show_start_link(self, proxy=False):
        if gizmo_server.isnotebook():
            await self._show_jupyter_start_link()
        else:
            await self._print_start_link()

    async def _show_jupyter_start_link(self):
        # xxxx why is this async?
        from . import jupyter_gizmo_support
        mgr = self._manager
        suffix = mgr.jupyter_url_suffix(
            for_gizmo=self,
            method="http",
            filename=self._filename,
        )
        fallback_url = self._entry_url(proxy=False)
        #self._display_html_in_ipython("<p>iframe url: " + url + "</p>")
        #self._display_html_in_ipython("<p>suffix: " + suffix + "</p>")
        # end debug
        jupyter_gizmo_support.display_link(suffix, fallback_url)

    async def _print_start_link(self):
        from .gizmo_link import LINK_PREFIX
        url = self._entry_url()
        link = '<a href="%s" target="_blank">Click to open</a> <br> \n %s %s \n' % (
            url, LINK_PREFIX, url)
        OKGREEN = '\033[92m'
        ENDC = '\033[0m'
        msg = "Open gizmo using link (control-click / open link)\n\n" + link + "\n\n"
        txt = "%s\n%s\n%s" % (OKGREEN, msg, ENDC)
        print (txt, flush=True)
        await self._has_started()

    async def _show_start_link0(self, proxy=False):
        # xxxx old version -- delete.
        from .gizmo_link import LINK_PREFIX
        #from IPython.display import HTML, display
        url = self._entry_url(proxy=proxy)
        link = '<a href="%s" target="_blank">Click to open</a> <br> \n %s %s \n' % (
            url, LINK_PREFIX, url)
        if gizmo_server.isnotebook():
            msg = "<h4>Open gizmo using link</h4>\n" + link
            #display(HTML(msg))
            self._display_html_in_ipython(msg)
        else:
            assert not proxy, "Proxy start link is not supported outside of notebook context."
            OKGREEN = '\033[92m'
            ENDC = '\033[0m'
            msg = "Open gizmo using link (control-click / open link)\n\n" + link + "\n\n"
            txt = "%s\n%s\n%s" % (OKGREEN, msg, ENDC)
            print (txt, flush=True)
        await self._has_started()

    def _display_html_in_ipython(self, msg):
        from IPython.display import HTML, display
        display(HTML(msg))

    async def _open_in_browser(self, new_page=True, proxy=False):
        import webbrowser
        url = self._entry_url(proxy=proxy)
        if gizmo_server.isnotebook():
            return await gizmo_server.display_gizmo_in_jupyter_new_tab(url)
        elif new_page:
            webbrowser.open_new(url)
        else:
            webbrowser.open_new_tab(url)

    async def _open_in_jupyter_iframe(self, height=20, proxy=False):
        # xxxx why is this async?
        from . import jupyter_gizmo_support
        mgr = self._manager
        fallback_url = self._entry_url(proxy=False)
        #self._display_html_in_ipython("<p>iframe url: " + fallback_url + "</p>")
        suffix = mgr.jupyter_url_suffix(
            for_gizmo=self,
            method="http",
            filename=self._filename,
        )
        jupyter_gizmo_support.display_iframe(suffix, fallback_url)

    def _initial_reference(self, identity, js_expression=None):
        assert type(identity) == str, "identity must be str " + repr(identity)
        if js_expression is None:
            js_expression = identity   # like "window"
        else:
            assert type(js_expression) == str, "js expression must be string if specified"
        assert self._html_page is not None, "reference requires initialized html page."
        key = (identity, js_expression)
        if key in self._initial_references:
            return  # don't duplicate existing reference
        ref = self._reference_identity(identity)
        self._html_page.link_reference(identity, js_expression)
        self._initial_references[key] = ref

    def _reference_identity(self, identity):
        if hasattr(self, identity) and getattr(self, identity) is not None:
            raise NameError(
                "id reference will not override in-use slot: " + repr(identity))
        reference = GizmoReference(identity, self)
        setattr(self, identity, reference)
        return reference

    def _dereference_identity(self, identity):
        ##pr("deref id", repr(identity))
        # Silently ignore if the attribute is missing.
        if not hasattr(self, identity):
            return
        old_value = getattr(self, identity)
        assert isinstance(old_value, GizmoReference), (
            "Deref does not apply to non-references.")
        setattr(self, identity, None)

    def _page_is_configurable(self):
        assert self._html_page is not None, "Cannot configure page until HTML page object is attached."
        assert not self._html_page.materialized, "Cannot configure HTML after it is materialized."
        return True

    def _embed_no_duplicate(self, key, check=True):
        if not check:
            assert self._page_is_configurable()
            return True
        embedded = self._embedded_components
        if key in embedded:
            # the resource has been embedded already.. don't do it twice
            return False
        else:
            #("permitting first embedding", key)
            assert self._page_is_configurable()
            embedded.add(key)
            return True

    def _insert_html(self, html_text, in_body=True):
        # don't check for duplicates xxx?
        assert self._page_is_configurable()
        self._html_page.insert_html(html_text, in_body=in_body)

    def _embedded_css(self, style_text):
        if self._embed_no_duplicate(style_text):
            self._html_page.embedded_css(style_text)

    def _embedded_script(self, javascript_code, in_body=True, check=True):
        if not self._embed_no_duplicate(javascript_code, check):
            return  # don't insert the same code twice unless override.
        self._html_page.embedded_script(javascript_code, in_body=in_body)

    def _remote_css(self, css_url, check=True):
        if self._embed_no_duplicate(css_url, check):
            self._html_page.remote_css(css_url)

    def _remote_js(self, js_url, in_body=False, check=True):
        if self._embed_no_duplicate(js_url, check):
            self._html_page.remote_js(js_url, in_body=in_body)

    def _relative_js(self, js_url, in_body=False, check=True):
        self._manager.validate_relative_path(js_url)
        return self._remote_js(js_url, in_body, check)

    def _relative_css(self, css_url, in_body=False, check=True):
        self._manager.validate_relative_path(css_url)
        return self._remote_css(css_url, check)

    def _js_file(self, os_path, url_path=None, in_body=False):
        if self._embed_no_duplicate(os_path):
            mgr = self._manager
            full_path = gz_resources.get_file_path(os_path)
            handler = mgr.add_file(full_path, url_path, content_type="text/javascript")
            filename = handler.filename
            # this should be a RELATIVE URL
            #full_url = mgr.local_url(for_gizmo=self, method="http", filename=filename)
            relative_url = self.relative_url(filename)
            self._remote_js(relative_url, in_body=in_body, check=False)

    def _css_file(self, os_path, url_path=None):
        if self._embed_no_duplicate(os_path):
            mgr = self._manager
            full_path = gz_resources.get_file_path(os_path)
            handler = mgr.add_file(full_path, url_path, content_type="text/css")
            filename = handler.filename
            # this should be a RELATIVE URL
            #full_url = mgr.local_url(for_gizmo=self, method="http", filename=filename)
            relative_url = self.relative_url(filename)
            self._remote_css(relative_url, check=False)

    def _serve_folder(self, url_file_name, os_path, module_file_path=None):
        """
        Serve all files below os_path using prefix url_file_name
        """
        # this is prolly not really correct
        assert "/" not in url_file_name, "Url file name should not contain subfolders."
        if module_file_path is not None:
            from_folder = os.path.dirname(module_file_path)
            abs_os_path0 = os.path.join(from_folder, os_path)
            os_path = os.path.abspath(abs_os_path0)
        full_path = gz_resources.get_file_path(os_path)
        mgr = self._manager
        mgr.serve_folder(full_path, url_file_name)

    def _add_content(self, os_path, content_type, url_path=None, dont_duplicate=True):
        # don't check for duplicates, etc. content may be modified during processing.
        mgr = self._manager
        full_path = gz_resources.get_file_path(os_path)
        handler = mgr.add_file(full_path, url_path, content_type=content_type)
        return handler.filename

    def _add_getter(self, url_path, getter):
        """Add a customer getter to serve a resource (like gizmo_server.BytesGetter())."""
        mgr = self._manager
        mgr.add_http_handler(url_path, getter)

    def _remove_getter(self, url_path):
        self._manager.remove_http_handler(url_path)

    def relative_url(self, filename):
        return "./" + filename

    def _set_manager(self, gz_server, mgr):
        self._manager = mgr
        self._server = gz_server.server
        self._url_prefix = gz_server.url_prefix
        self._port = gz_server.port
        self._out = self._out or gz_server.out
        self._err = self._err or gz_server.err

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
    
    async def _js_await(self, promise_reference, to_depth=None):
        """
        Return cached reference to resolution of promise_reference.
        """
        future = self._js_promise(promise_reference, to_depth=to_depth)
        await future
        return future.result()
    
    def _js_promise(self, promise_reference, to_depth=None):
        """
        Return an awaitable which resolves or errors
        when the denotee of the promise reference resolves
        or errors on the JS side.

        Result of future is reference to resolved JS object in cache.
        """
        # xxxx should add timeout...
        # Get a reference to the cached promise result
        refid = new_identifier("js_promise")
        reference = GizmoReference(refid, self)
        # Construct a Python future.
        future = asyncio.Future()
        def clean_up():
            self._unregister_callback(callable=fullfill)
            self._unregister_callback(callable=reject)
            #reference._disconnect()
        def fullfill(*args):
            future.set_result(reference)
            clean_up()
        def reject(*args):
            exc = JavascriptEvalException("js future rejected: " + repr(args))
            future.set_exception(exc)
            clean_up()
        # attach the python future to the js future
        do(self.H5GIZMO_INTERFACE.cache_promise_result(
            refid,
            promise_reference,
            fullfill,
            reject,
        ), to_depth=to_depth)
        return future
    
    def _unregister_callback(self, oid=None, callable=None):
        if oid is not None:
            callable = self._call_backs[oid]
        elif callable is not None:
            oid = self._callable_to_oid[callable]
        # silently ignore missing values due to previous errors
        if oid in self._call_backs:
            del self._call_backs[oid]
        if callable in self._callable_to_oid:
            del self._callable_to_oid[callable]

    def _send(self, json_message):
        if self._log_messages:
            print("sending json", repr(json_message)[:100])
        try:
            #("gizmo sending json", repr(json_message)[:100])
            #(self._sender)
            self._check_web_socket()
            self._sender(json_message)
        finally:
            self._check_last_flush_queue_task()

    def _check_web_socket(self):
        p = self._pipeline
        if p is not None:
            p.check_web_socket_not_closed()

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
        elif indicator == Gizmo.KEEPALIVE:
            return   # ignore keepalive messages
        else:
            truncated_payload = repr(json_response)[:50]
            info = "Unknown indicator: %s; payload=%s" % (indicator, truncated_payload)
            raise BadResponseFormat(info)

    def _fail_all_gets(self, exception):
        o2f = self._oid_to_get_futures
        self._oid_to_get_futures = {}
        for fut in o2f.values():
            fut.set_exception(exception)

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

    _print_callback_exception = True
    _on_callback_exception = None

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
            on_exc = self._on_callback_exception
            if on_exc is not None:
                fmt = traceback.format_exc()
                on_exc(fmt)
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
            else:
                self._unreported_exception_payload = payload
        else:
            self._unreported_exception_payload = payload
        on_exc = self._on_exception
        if on_exc is not None:
            on_exc(payload)
        return exc

    async def _poll_report_exception(self, delay=1.0, limit=None):
        # test whether a loop is already running.
        #("DEBUG:: exception polling task is running")
        # xxxx should link this to self._err redirect xxxx
        self._exception_loop_test_flag = False
        await asyncio.sleep(delay * 3)
        if self._exception_loop_test_flag:
            print("Aborting redundant exception polling task.")
            raise RuntimeError("Exception loop seems already to be running.")
        count = 0
        while (limit is None) or (count < limit):
            #("DEBUG:: polling for exceptions", count)
            count += 1
            self._exception_loop_test_flag = True
            ue = self._unreported_exception_payload
            self._unreported_exception_payload = None
            if ue is not None:
                print(count, "=" * 50)
                print("Unreported exception detected for", self)
                print(ue)
                print(count, "=" * 50)
            await asyncio.sleep(delay)

    def _start_report_error_task(self, delay=1.0, limit=None):
        #("DEBUG:: starting error polling task")
        schedule_task(self._poll_report_exception(delay, limit))

    def _register_future(self, timeout=None):
        self._counter += 1
        o2f = self._oid_to_get_futures
        oid = "GZget_" + repr(self._counter)
        def on_timeout():
            if o2f.get(oid) is not None:
                del o2f[oid]
        future = make_future(timeout=timeout, on_timeout=on_timeout)
        o2f[oid] = future
        """if timeout is not None:
            async def timeout_check():
                await asyncio.sleep(timeout)
                if not future.done():
                    exc = FutureTimeout("Timeout expired: "+ repr(timeout))
                    future.set_exception(exc)
                if o2f.get(oid) is not None:
                    del o2f[oid]
            schedule_task(timeout_check())"""  # refactored
        return (oid, future)

def make_future(timeout=None, on_timeout=None):
    "Get a future associated with the global event loop."
    # Convenience
    loop = gizmo_server.get_or_create_event_loop()
    future = loop.create_future()
    # xxx this is cut/paste/modified from _register_future
    if timeout is not None:
        async def timeout_check():
            await asyncio.sleep(timeout)
            if not future.done():
                exc = FutureTimeout("Timeout expired: "+ repr(timeout))
                future.set_exception(exc)
                if on_timeout is not None:
                    on_timeout()
        schedule_task(timeout_check())
    return future


GZ = Gizmo

class BadResponseFormat(ValueError):
    "Javascript sent a message which was not understood."

class FutureTimeout(ValueError):
    "Timeout waiting for value."

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

    def _register_get_future(self, timeout=None):
        if self._get_oid is not None:
            return (self._get_oid, self._get_future)
        result = (self._get_oid, self._get_future) = self._owner_gizmo._register_future(timeout=timeout)
        return result

    def _exec(self, to_depth=None, detail=False):
        to_depth = to_depth or self._owner_gizmo._default_depth
        gz = self._owner_gizmo
        cmd = self._command(to_depth)
        #pr("cmd", repr(cmd)[:200])
        msg = [GZ.EXEC, cmd]
        gz._send(msg)
        if detail:
            return cmd
        else:
            return None

    async def _get(self, to_depth=None, timeout=DEFAULT_TIMEOUT, oid=None, future=None, test_result=None):
        gz = self._owner_gizmo
        to_depth = to_depth or gz._default_depth
        cmd = self._command(to_depth)
        if oid is None:
            # allow the test suite to pass in the future for testing only...
            (oid, future) = self._register_get_future(timeout=timeout)
        self._get_oid = oid
        msg = [GZ.GET, oid, cmd, to_depth]
        #("now sending")
        gz._send(msg)
        if test_result is not None:
            return test_result  # only for code coverage...
        await future
        self._get_oid = None
        self._get_future = None
        #("now awaiting get result")
        return future.result()

    def _connect(self, id, to_depth=None):
        "Store the command result in the JS object_cache using the id."
        gz = self._owner_gizmo
        to_depth = to_depth or gz._default_depth
        cmd = self._command(to_depth)
        msg = [GZ.CONNECT, id, cmd]
        gz._send(msg)
        self._owner_gizmo._reference_identity(id)
        return GizmoReference(id, gz)

    def _disconnect(self, id=None):
        "Remove the id and referent from the JS object_cache"
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

    def __repr__(self):
        return "%s[%s]" % (self._target_cmd, self._index_cmd)

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

    def __repr__(self):
        return "%s._set(%s, %s)" % (self._target_cmd, self._index_cmd, self._value_cmd)

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

    def __repr__(self):
        return "%s%s" % (self._callable_cmd, tuple(self._args_cmds))

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

    def __repr__(self):
        return "_CACHE_[%s]" % repr(self._id)

    def _command(self, to_depth):
        return [GZ.REFERENCE, self._id]

    def _get_id(self):
        return self._id

    def disconnect(self):
        return self._disconnect(self._id)


literalTypes = set([
    int,
    float,
    str,
    bool,
    type(None),
    list,
    dict,
])

class GizmoLiteral(GizmoLink):

    """
    Wrapped JSON literal
    """

    def __init__(self, value, owner):
        t = type(value)
        assert t in literalTypes, "bad literal type" + repr(t)
        self._owner_gizmo = owner
        self._value = value

    def __repr__(self):
        return "L(%s)" % repr(self._value)

    def _command(self, to_depth):
        return [GZ.LITERAL, self._value]


class GizmoSequence(GizmoLink):

    """
    Wrapped sequence
    """

    def __init__(self, commands, owner):
        self._owner_gizmo = owner
        self._commands = commands

    def __repr__(self):
        return "S%s" % repr(self._commands)

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

    def __repr__(self):
        return "D%s" % repr(self._command_dictionary)

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

    def __repr__(self):
        return "B" + repr(self._byte_array)

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

    def __repr__(self):
        return "CB[%s]" % (self._callable_object,)

    def _command(self, to_depth):
        return [GZ.CALLBACK, self._oid, to_depth]


def np_array_translator(a, gizmo):
    # allow the gizmo to translate 1d arrays
    translator = gizmo._translate_1d_array
    if translator is not None and len(a.shape) == 1:
        return translator(a)
    return a.tolist()

def tuple_to_list(t, gizmo):
    return list(t)

def np_literal_to_float(n, gizmo):
    return float(n)

def np_literal_to_int(n, gizmo):
    return int(n)

class ValueConverter:

    """
    Convert value sub-components where needed.
    """

    def __init__(self, value, owner):
        self.value = value
        self.is_literal = True
        ty = type(value)
        translator = self.translators.get(ty)
        #pr("checking translations", list(self.translators.keys()))
        #pr("translation for",  ty, "is", translator)
        translation = value
        if translator is not None:
            translation = translator(value, owner)
            ty = type(translation)
            #pr ("translation", translation, ty)
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
                translation = [c.command._value for c in conversions]
                #pr("literal types", list(map(type, translation)))
                #pr("list", translation)
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
                translation = {k: c.command._value for (k, c) in conversions.items()}
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

    def __repr__(self):
        return "V(%s)" % self.command

    scalar_types = set([int, float, str,  bool, type(None)])

    translators = {
        np.ndarray: np_array_translator,
        tuple: tuple_to_list
        #np.float: float,
        #np.float128: float,
        #np.float16: float,
        #np.float32: float,
        #np.float64: float,
        #np.int0: int,
        #np.int16: int,
        #np.int32: int,
        #np.int64: int,
    }
    for type_name in "float float128 float16 float32 float64".split():
        if hasattr(np, type_name):
            ty = getattr(np, type_name)
            translators[ty] = np_literal_to_float
    for type_name in "int int8 int0 int16 int32 int64 uintc uintp".split():
        if hasattr(np, type_name):
            ty = getattr(np, type_name)
            translators[ty] = np_literal_to_int
        type_name = "u" + type_name
        if hasattr(np, type_name):
            ty = getattr(np, type_name)
            translators[ty] = np_literal_to_int

FINISHED_UNICODE = "F"
CONTINUE_UNICODE = "C"

class GizmoPacker:

    def __init__(self, process_packet, awaitable_sender, packet_limit=PACKET_LIMIT, auto_flush=True):
        self.process_packet = process_packet
        self.packet_limit = packet_limit
        self.collector = []
        self.outgoing_packets = []
        self.auto_flush = auto_flush
        self.awaitable_sender = awaitable_sender
        self.flush_queue = []
        self.flush_queue_task = None
        self.last_flush_queue_task = None
        self.send_lock = asyncio.Lock()
        self.ack_future = None

    def receive_acknowledgement(self):
        "Return awaitable that resolves when ack arrives."
        assert self.ack_future is None, "Cannot await more than one ack at a time."
        future = asyncio.Future()
        self.ack_future = future
        return future

    async def execute_flush_queue(self):
        "execute the flushes in sequence (prevent interleaving)."
        try:
            while self.flush_queue:
                q = self.flush_queue
                next_flush = q[0]
                self.flush_queue = q[1:]
                #("awaiting flush queue", len(self.flush_queue))
                await next_flush
        finally:
            #("terminating flush queue task.")
            self.flush_queue = []  # should be redundant
            try:
                self.check_last_flush_queue_task()
            except Exception:
                # xxxx this shouldn't happen -- #Print error?
                pass
            self.last_flush_queue_task = self.flush_queue_task
            self.flush_queue_task = None

    def check_last_flush_queue_task(self):
        "Get the result from the last flush queue task in case there was an error."
        q = self.last_flush_queue_task
        self.last_flush_queue_task = None
        result = None
        if q is not None:
            assert q.done(), "last task queue was not finished."
            result = q.result()
        return result

    def cancel_all_flushes(self):
        qt = self.flush_queue_task
        if qt is not None:
            qt.cancel()
        #flushes = self.flush_queue
        #for task in flushes:
        #    task.cancel()  -- not tasks -- just discard the awaitables
        # The web socket is broken.  Assume any flushes and partially collected packets are broken too (???)
        self.flush_queue = []
        self.flush_queue_task = None
        self.collector = []

    def start_flush_queue_task_if_needed(self):
        if (self.flush_queue_task is None) and self.flush_queue:
            self.flush_queue_task = schedule_task(self.execute_flush_queue())
        return self.flush_queue_task

    def flush(self):
        outgoing = self.outgoing_packets
        self.outgoing_packets = []
        if outgoing:
            awaitable = self.awaitable_flush(outgoing)
            #task = schedule_task(awaitable)
            ##pr ("flush returns task", task)
            #self.last_flush_task = task
            #return task
            self.flush_queue.append(awaitable)
            return self.start_flush_queue_task_if_needed()
        else:
            return None

    async def awaitable_flush(self, outgoing=None):
        async with self.send_lock:
            await self.awaitable_flush_locked(outgoing)

    async def awaitable_flush_locked(self, outgoing=None):
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
            #p("now sending", ln)
            for start in range(0, ln, limit):
                end = start + limit
                chunk = string[start : end]
                final = (end >= ln)
                if final:
                    data = FINISHED_UNICODE + chunk
                else:
                    data = CONTINUE_UNICODE + chunk
                # ("awaiting flush")
                await self.awaitable_sender(data)
                # wait for ok if not finished.
                if not final:
                    #p("waiting for ack", start, limit)
                    await self.receive_acknowledgement()
                    #p("got ack", start, limit)

    def send_unicode(self, string):
        self.outgoing_packets.append(string)
        #("pipeline send unicode", repr(string)[:10])
        if self.auto_flush:
            task = self.flush()
            # ("send unicode returns task", task)
            return task
        else:
            return None

    async def on_unicode_message(self, message):
        indicator = message[0:1]
        remainder = message[1:]
        if indicator == CONTINUE_UNICODE:
            self.collector.append(remainder)
            # send ok reply XXXX
            #p ("debug: now sending ack", self.awaitable_sender, len(remainder))
            await self.awaitable_sender(Gizmo.ACKNOWLEDGE)
        elif indicator == FINISHED_UNICODE:
            collector = self.collector
            self.collector = []
            collector.append(remainder)
            packet = "".join(collector)
            self.process_packet(packet)
        elif indicator == Gizmo.ACKNOWLEDGE:
            #p("got ack message")
            future = self.ack_future
            self.ack_future = None
            if future is not None:
                future.set_result(message)
            else:
                print("Unexpected ack", repr(message[:20]))
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
        # ("CODEC sending unicode", repr(unicode_str)[:10])
        self.send_unicode(unicode_str)
        return unicode_str


class WebSocketIsClosed(IOError):
    "Cannot perform the operation because the socket has been closed."


class GZPipeline:

    def __init__(self, gizmo, packet_limit=PACKET_LIMIT, auto_flush=True):
        self.gizmo = gizmo
        gizmo._set_pipeline(self)
        #self.sender = None
        self.request = None
        self.web_socket = None
        self.waiting_chunks = []
        self.packer = GizmoPacker(self.process_packet, self._send, packet_limit, auto_flush)
        self.json_codec = JsonCodec(self.process_json, self.send_unicode, self.json_error)
        self.last_json_error = None
        self.last_receive_error = None
        self.ws_error_message = None
        self.reconnect_id = None
        self.clear()

    def check_last_flush_queue_task(self):
        self.packer.check_last_flush_queue_task()

    auto_clear = True  # set false only for debug

    def my_stdout(self):
        if self.gizmo:
            out = self.gizmo._out
            if out:
                return out
        return contextlib.redirect_stdout(sys.stdout)

    def my_stderr(self):
        if self.gizmo:
            err = self.gizmo._err
            if err:
                return err
        return contextlib.redirect_stderr(sys.stderr)

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

    def check_web_socket_not_closed(self, error_if_closed=True):
        ws = self.web_socket
        result = True  # ws ok
        if (ws is not None) and (ws._closed):
            result = False  # ws broken
            #("cannot send -- closed")
            exception = WebSocketIsClosed("cannot send to closed web socket.")
            self.gizmo._fail_all_gets(exception)
            self.packer.cancel_all_flushes()
            if error_if_closed:
                raise exception
        return result

    async def _send(self, chunk):
        #p ("pipeline sending", repr(chunk[:10]))
        with self.my_stderr():
            with self.my_stdout():
                self.check_web_socket_not_closed()
                if self.web_socket is not None:
                    await self.sender(chunk)
                else:
                    self.waiting_chunks.append(chunk)
                if self.auto_clear:
                    self.clear()

    async def handle_websocket_request(self, request, get_websocket=web.WebSocketResponse):
        #pr("pipeline handling request", request)
        incoming_id = request._rel_url.query.get(Gizmo.RECONNECT_ID)
        if self.request is not None:
            old_id = self.reconnect_id
            if (old_id is not None) and (incoming_id != old_id):
                raise TooManyRequests("A pipeline can only support one request.")
            # Otherwise if the child is trying to reconnect -- allow it.
            # XXXX Ideally we would clean up the task listening to the dead web socket, but it doesn't seem possible.
            #("reconnecting web socket", request)
            self.packer.cancel_all_flushes()
        self.reconnect_id = incoming_id
        ws = get_websocket()
        self.web_socket = ws
        # xxxx hack -- In Jupyter this generates an error that seems harmless...
        with TemporaryDisableWSLogging():
            await ws.prepare(request)
        self.request = request
        #self.sender = ws.send_str
        wc = self.waiting_chunks
        self.waiting_chunks = []
        for chunk in wc:
            #pr ("pipeline sending waiting chunk", repr(chunk))
            await self._send(chunk)
        await self.listen_to_websocket(ws)
        return ws

    async def sender(self, data):
        #p("   sender", repr(data[:20]))
        await self.web_socket.send_str(data)
        # after every send, give the other side a chance to send (?)
        #await self.web_socket.drain() -- deprecated
        await asyncio.sleep(0.001) # is this needed?

    MSG_TYPE_TEXT = aiohttp.WSMsgType.text
    MSG_TYPE_ERROR = aiohttp.WSMsgType.error

    async def listen_to_websocket(self, ws):
        # XXXX if the web socket does not close gracefully this task will never finish.
        # XXXX https://github.com/aio-libs/aiohttp/issues/4153
        # Maybe future versions of aiohttp will fix this using the heartbeat feature (which doesn't cut it now).
        # At the moment I can't figure out how to clean this up without bad side effects (hangs).
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
                    await self.receive_unicode(data)
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

    async def receive_unicode(self, unicode_str):
        #pr("pipeline receive unicode", repr(unicode_str))
        self.last_unicode_received = unicode_str
        return await self.packer.on_unicode_message(unicode_str)

    def process_packet(self, packet):
        #pr("pipeline process packet", repr(packet))
        with self.my_stderr():
            with self.my_stdout():
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
        #("pipeline send unicode", repr(unicode_str)[:10])
        task_or_none = self.packer.send_unicode(unicode_str)
        self.last_unicode_sent = unicode_str
        return task_or_none

    def json_error(self, msg):
        # ????
        #pr("pipeline json err", msg)
        self.last_json_error = msg

class TooManyRequests(AssertionError):
    "A pipeline can only support one request."

def schedule_task(awaitable):
    "Schedule a task in the global event loop."
    # Convenience
    loop = gizmo_server.get_or_create_event_loop()
    task = loop.create_task(awaitable)
    return task

class DoAllMethods:

    """
    Convenience for an link where you mainly want to "do" methods with literal values.
    Instead of

        do(link.method1(arg1))
        do(link.method2(arg1))
        ...

    Use

        wrapped = DoAllMethods(link)
        wrapped.method1(arg1)
        wrapped.method2(arg2)
        ...
    """
    # Note: added to support jp_doodle.
    #   Added here because it might be generally useful.

    def __init__(self, wrapped_link, to_depth=3):
        assert isinstance(wrapped_link, GizmoLink), "Only DoAllMethods for a link object. " + repr(wrapped_link)
        self._wrapped_link = wrapped_link
        self._to_depth = 3

    def __getattr__(self, attribute):
        #("getting", self._wrapped_link, attribute)
        assert not attribute.startswith("_"), "Don't access hidden attributes: " + repr(
            (attribute, self._wrapped_link)
        )
        method_link = getattr(self._wrapped_link, attribute)
        return DoAllMethodsMethodWrapper(method_link, to_depth=self._to_depth)

    def __getitem__(self, key):
        return self.__getattr__(key)

class DoAllMethodsMethodWrapper:

    def __init__(self, wrapped_method_link, to_depth=3):
        self._wrapped_method_link = wrapped_method_link
        self._to_depth = to_depth

    def __call__(self, *args):
        # ("calling", self._wrapped_method_link, args)
        call_link = self._wrapped_method_link(*args)
        do(call_link, to_depth=self._to_depth)

class TemporaryDisableWSLogging:
    "Hack to suppress logging messages from aiohttp."
    def __enter__(self):
        from aiohttp import log
        import logging
        log.ws_logger.setLevel(logging.CRITICAL)

    def __exit__(self, exc_type, exc_val, exc_tb):
        from aiohttp import log
        import logging
        log.ws_logger.setLevel(logging.WARNING)
