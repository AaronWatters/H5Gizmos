"""
Composable gizmo factories.
"""

# run should work in jupyter -- delegate to browse when jupyter env detected.

#from time import time
#from numpy.lib.function_base import _ARGUMENT
from H5Gizmos import do, get, name, get_gizmo, schedule_task
from . import gizmo_server
#from . import H5Gizmos
from . import gz_resources
from . import gz_parent_protocol as H5Gizmos
from . import gz_get_blob
import numpy as np
import os
import asyncio

JS_COLLECTION_NAME_MAP = {
    # numpy dtype : name of analogous collection
    np.int8: "Int8Array",
    np.uint8: "Uint8Array",
    np.int16: "Int16Array",
    np.int16: "Uint16Array",
    np.int32: "Int32Array",
    np.uint32: "Uint32Array",
    np.float32: "Float32Array",
    np.float64: "Float64Array",
    np.int64: "BigInt64Array",
    np.uint64: "BigUint64Array",
}

# xxx what is the diff np.dtype(np.uint8) vs np.uint8???
for (ty, n) in list(JS_COLLECTION_NAME_MAP.items()):
    JS_COLLECTION_NAME_MAP[np.dtype(ty)] = n

class Component:

    gizmo = None   # default until gizmo is attached.
    task = None
    verbose = False
    js_object_cache = None
    cache_name = None
    auto_start = True  # start browser page automatically.
    close_button = False
    gizmo_configured = False
    _gizmo_attached_future = None
    _component_started_future = None
    _actions_awaiting_start = None
    _module_context = None
    template = None

    def __init__(self):
        # start the task which waits for gizmo initialization
        self.component_started_future()

    def make_template(self, from_html):
        self.template = gz_resources.Template(from_html)
        return self.template
    
    def make_template_from_file(self, file_path):
        self.template = gz_resources.Template.from_file(file_path)
        return self.template

    def get_module_context(self):
        from . import gz_module_support
        result = self._module_context
        if result is None:
            result = self._module_context = gz_module_support.Module_context()
        return result
    
    def load_node_modules(self, node_modules_folder, url_prefix="node_modules", module_file_path=None):
        """
        Load node_modules directory.  Must execute before gizmo server initialization.

        To load relative to module __file__ location:

        H = Html("<h1>Hello modules!</a>")
        H.load_node_modules(node_modules, "nm", module_file_path=__file__)
        # prepare references to modules
        H.load_module("qd_vector")
        ...
        await H.link()
        name = await get(H.gizmo.modules.qd_vector.name)
        """
        if self.gizmo:
            raise RuntimeError("Node modules must be loaded before gizmo initialization. "
                               + repr(node_modules_folder))
        self.serve_folder(url_prefix, node_modules_folder, module_file_path)
        context = self.get_module_context()
        context.map_node_modules(node_modules_folder, url_prefix, module_file_path)

    def load_module(self, module_identifier, alias=None):
        if self.gizmo:
            raise RuntimeError("Modules must be loaded before gizmo initialization. "
                               + repr(module_identifier))
        context = self.get_module_context()
        context.load_module(module_identifier, alias)

    def load_bundle(self, relative_bundle_path, module_file_path, url_prefix, module_id=None):
        """
        For example invoked in a Python module source file:

        G.load_bundle("../dist/chart_js_gizmo.es.js", __file__, "chart_js")

        loads the "../dist/chart_js_gizmo.es.js" module, accessible in Python
        via the reference

        G.modules.chart_js

        module_file_path should normally be __file__ in module context.
        relative_bundle_path should be the location of the bundle relative
        to the module_file_path -- like "../dist/chart_js_gizmo.es.js".
        url_prefix should be a name like "chart_js" to use as an URL bundle
        prefix -- combining with module_file_path to "./chart_js/chart_js_gizmo.es.js".
        """
        if self.gizmo:
            raise RuntimeError("Bundles must be loaded before gizmo initialization. "
                               + repr(relative_bundle_path))
        from_folder = os.path.dirname(module_file_path)
        abs_bundle_path0 = os.path.join(from_folder, relative_bundle_path)
        abs_bundle_path = os.path.abspath(abs_bundle_path0)
        (bundle_folder, bundle_file_name) = os.path.split(abs_bundle_path)
        module_url = "./" + url_prefix + "/" + bundle_file_name
        self.serve_folder(url_prefix, bundle_folder)
        if module_id is None:
            module_id = url_prefix
        self.load_module(module_url, module_id)

    def _add_module_support(self):
        context = self._module_context
        if context is not None:
            import_map = context.import_map_html()
            self.insert_html(import_map)
            script = context.module_loader_html()
            self.insert_html(script)

    def gizmo_attached_future(self):
        """
        Future which resolves when gizmo is attached.
        """
        f = self._gizmo_attached_future
        if f is None:
            f = self._gizmo_attached_future = H5Gizmos.make_future()
        if self.gizmo is not None and not f.done():
            f.set_result(True)
        return f
    
    def component_started_future(self):
        """
        Future which resolves when the component has initialized on the front end.
        """
        f = self._component_started_future
        if f is None:
            f = self._component_started_future = H5Gizmos.make_future()
            self._actions_awaiting_start = []
            attached = self.gizmo_attached_future()
            async def start_test_task():
                await attached
                await self.gizmo._has_started()
                #(self, "signal component has started.")
                f.set_result(True)
                # execute deferred actions now (stop on first exception (???))
                actions = self._actions_awaiting_start
                self._actions_awaiting_start = []
                for action in actions:
                    #("    deferred action", action)
                    action()
            H5Gizmos.schedule_task(start_test_task())
        return f
    
    def call_when_started(self, action):
        #(self, "call when started", action)
        # make sure future is created...
        started = self.component_started_future()
        #started = (self.gizmo is not None)
        if not started.done():
            #(self, "  wait for start, deferring", action)
            self._actions_awaiting_start.append(action)
        else:
            # started: just call immediately
            #(self, "component started, calling immediately.", action)
            action()

    def attach_gizmo(self, gizmo):
        self.gizmo = gizmo
        self.add_dependencies(gizmo)
        # add deferred dependencies after standard dependencies (for example so jQuery is available in deferred code)
        self.add_deferred_dependencies(gizmo)
        gizmo._translate_1d_array = self.translate_1d_array
        self.gizmo_configured = True
        attached = self.gizmo_attached_future()
        if not attached.done():
            attached.set_result(True)

    def prepare_application(self, gizmo):
        self.attach_gizmo(gizmo)
        self.configure_page(gizmo)

    def shutdown_on_unload(self, gizmo):
        #do(gizmo.window.addEventListener("unload", self.shutdown_parent_only), to_depth=1)
        self.on_shutdown(self.shutdown_parent_only, gizmo=gizmo)

    def on_shutdown(self, callback, gizmo=None):
        def action(gizmo=gizmo):
            if gizmo is None:
                gizmo = self.gizmo
            assert gizmo is not None, "No gizmo attached -- cannot add listener."
            do(gizmo.window.console.log("adding unload callback"))
            do(gizmo.window.addEventListener("unload", callback), to_depth=1)
        self.call_when_started(action)

    _icon_path = "../static/icon.png"
    _icon_content_type = "image/png"

    def set_icon(self, path, content_type=None):
        import os
        assert os.path.isfile(path), "File not found: " + repr(path)
        self._icon_path = path
        self._icon_content_type = content_type

    def add_std_icon(self, gizmo):
        # https://www.w3.org/2005/10/howto-favicon
        gizmo._add_content(os_path=self._icon_path, content_type=self._icon_content_type, url_path="icon.png")
        gizmo._insert_html('<link rel="icon" type="image/png" href="./icon.png"/>', in_body=False)

    async def show(self, verbose=False, log_messages=False, title="Gizmo"):
        """
        Try to guess the right way to display self as iframe, in browser tab, or default to link.
        """
        if gizmo_server.isnotebook():
            return await self.iframe(verbose=verbose, log_messages=log_messages)
        use_link = False
        # Use a link if local guis are not supported.
        if not gizmo_server.use_local_gui():
            if verbose:
                print("Server prefix does not allow opening a local browser window. Please use link.")
            use_link = True
        # Use a link if the browser check fails.
        if not use_link:
            try:
                H5Gizmos.check_browser()
            except Exception:
                use_link = True
        if use_link:
            # Show a link and hope the reader will know what to do with it...
            return await self.link(verbose=verbose, log_messages=log_messages, title=title)
        else:
            # Try to launch a new browser tab automatically.
            return await self.browse(verbose=verbose, log_messages=log_messages, title=title)

    async def iframe(self, height=20, verbose=False, log_messages=False, proxy=False):
        assert gizmo_server.isnotebook(), "iframe method only runs in IPython kernel."
        gizmo = await get_gizmo(verbose=verbose, log_messages=log_messages, template=self.template)
        self.prepare_application(gizmo)
        await gizmo.start_in_iframe(height=height, proxy=proxy)
        # Make sure all deferred actions complete before continuing...
        await self.component_started_future()

    async def browse(
        self, 
        title="Gizmo",
        auto_start=True, 
        verbose=False, 
        log_messages=False, 
        #close_button=False,
        await_start=True,
        proxy=False,
        shutdown_on_close=True,
        force=False,
        ):
        if auto_start:
            # override auto_start if running under gizmo_link server
            if gizmo_server.running_under_gizmo_link():
                if verbose:
                    print("Overriding auto start inside gizmo_link.")
                auto_start = False
        in_notebook = gizmo_server.isnotebook()
        # Unless forced use links from jupyter
        # to prevent error messages when the note book is openned
        # again later.
        if (not force) and in_notebook:
            auto_start = False
        if auto_start:
            H5Gizmos.check_browser()
        if verbose:
            print("Display gizmo component in new browser window.")
        gizmo = await get_gizmo(verbose=verbose, log_messages=log_messages, title=title, template=self.template)
        self.prepare_application(gizmo)
        if verbose:
            print("   entry_url=", gizmo._entry_url(proxy=proxy))
        if shutdown_on_close and not in_notebook:
            self.shutdown_on_unload(gizmo)
        self.add_std_icon(gizmo)
        if auto_start:
            await gizmo.start_in_browser(proxy=proxy)
        else:
            if await_start:
                await gizmo._show_start_link(proxy=proxy)
        if await_start or auto_start:
            # Make sure all deferred actions complete before continuing...
            await self.component_started_future()

    async def link(
            self, 
            title="Gizmo",
            verbose=False, 
            log_messages=False, 
            await_start=True, 
            proxy=False,
            shutdown_on_close=True,
            ):
        await self.browse(
            title=title,
            auto_start=False, 
            verbose=verbose, 
            log_messages=log_messages,
            await_start=await_start,
            proxy=proxy,
            shutdown_on_close=shutdown_on_close,
            )

    async def has_started(self):
        gizmo = self.gizmo
        if gizmo is None:
            return False
        else:
            return await gizmo._has_started()

    def entry_url(self):
        gizmo = self.gizmo
        assert gizmo is not None, "entry URL is available only after gizmo is configured."
        return self.gizmo._entry_url()

    def configure_page(self, gizmo):
        # reference shortcuts
        self.window = gizmo.window
        self.document = gizmo.document
        self.modules = gizmo.modules
        body = self.body = gizmo.GIZMO_BODY
        interface = gizmo.H5GIZMO_INTERFACE
        element = self.dom_element_reference(gizmo)
        do(interface._set("Target", element))
        target = self.target = interface.Target
        do(body.append(target))

    stylesheet_path = "../static/gizmo_style.css"  # changable in subclass (to None to disable)

    def add_dependencies(self, gizmo):
        """
        Add libraries, css files, references, or other resources required by the component to the gizmo.
        """
        self._add_module_support()
        stylesheet_path = self.stylesheet_path
        if (stylesheet_path):
            gizmo._css_file(stylesheet_path)
        gizmo._initial_reference("window")
        gizmo._initial_reference("document")
        gizmo._initial_reference("H5GIZMO_INTERFACE")
        gizmo._initial_reference("H5Gizmos")
        gizmo._initial_reference("make_array_buffer", "H5Gizmos.make_array_buffer")
        gizmo._initial_reference("GIZMO_BODY", 'document.getElementById("GIZMO_BODY")')
        gizmo._initial_reference("modules", "window.H5GIZMO_INTERFACE.modules")
        self.serve_folder("GIZMO_STATIC", "../static")

    def add_deferred_dependencies(self, gizmo):
        "Add deferred dependencies after standard dependencies."
        dependency_list = self.dependency_list
        if dependency_list:
            for (method_name, arguments) in dependency_list:
                method = getattr(gizmo, method_name)
                method(*arguments)

    dependency_list = None
    dependency_set = None

    def dependency(self, method_name, arguments):
        "deferred dependency -- must be evaluated after gizmo is bound."
        dlist = self.dependency_list or []
        dset = self.dependency_set or set()
        entry = (method_name, tuple(arguments))
        if entry in dset:
            # ignore duplicate
            return
        assert not self.gizmo_configured, "cannot load this dependency after initialization: " + repr(entry)
        dlist.append(entry)
        dset.add(entry)
        self.dependency_list = dlist
        self.dependency_set = dset

    def initial_reference(self, identity, js_expression=None):
        "Reference to a Javascript value, bound at initialization."
        return self.dependency("_initial_reference", (identity, js_expression))

    def serve_folder(self, url_file_name, os_path, module_file_path=None):
        "Serve files from folder locally, guessing MIME type.."
        if self.gizmo is not None:
            return self.gizmo._serve_folder(url_file_name, os_path, module_file_path)
        return self.dependency("_serve_folder", (url_file_name, os_path, module_file_path))

    def relative_js(self, js_url, in_body=False, check=True):
        "Load a Javascript URL from a locally served folder."
        return self.dependency("_relative_js", (js_url, in_body, check))

    def relative_css(self, css_url, in_body=False, check=True):
        "Load a CSS style sheet URL from a locally served folder."
        return self.dependency("_relative_css", (css_url, in_body, check))

    def insert_html(self, html_text, in_body=True):
        "Insert HTML at initialization time."
        return self.dependency("_insert_html", (html_text, in_body))

    def embedded_css(self, style_text):
        "Embedded style at initialization."
        return self.dependency("_embedded_css", (style_text,))

    def embedded_script(self, javascript_code, in_body=False, check=True):
        "Embedded javascript code at initialization."
        return self.dependency("_embedded_script", (javascript_code, in_body, check))

    def remote_css(self, css_url, check=True):
        "Load a remote CSS resource by URL at initialization."
        return self.dependency("_remote_css", (css_url, check))

    def remote_js(self, js_url, in_body=True, check=True):
        "Load a remote JS library by URL at initialization."
        return self.dependency("_remote_js", (js_url, in_body, check))

    def js_file(self, os_path, url_path=None, in_body=False):
        "Load a Javascript library from a file at initialization."
        return self.dependency("_js_file", (os_path, url_path, in_body))

    def css_file(self, os_path, url_path=None):
        "Load a CSS style sheet from a file at initialization."
        return self.dependency("_css_file", (os_path, url_path))

    def add_content(self, os_path, content_type=None, url_path=None, dont_duplicate=True):
        "Configure a content resource from a file."
        if self.gizmo is None:
            return self.dependency("_add_content", (os_path, content_type, url_path, dont_duplicate))
        else:
            return self.gizmo._add_content(os_path, content_type, url_path, dont_duplicate)

    def dom_element_reference(self, gizmo):
        """
        initialize and return a reference to the DOM element for this component.
        """
        self.gizmo = gizmo
        attached = self.gizmo_attached_future()
        if not attached.done():
            attached.set_result(True)
        self.initialize_object_cache()
        self.window = gizmo.window # define the window shortcut
        return "Undefined gizmo component."  # override return value in subclass.

    def initialize_object_cache(self):
        gizmo = self.gizmo
        cache_name = self.cache_name
        if cache_name is None:
            cache_name = self.cache_name = (self.cache_name or self.get_cache_name())
            self.js_object_cache = name(cache_name, H5Gizmos.GizmoLiteral({}, gizmo))

    def get_cache_name(self):
        prefix = "cache"
        try:
            prefix = type(self).__name__
        except Exception:
            pass
        return H5Gizmos.new_identifier(prefix)

    def cache(self, name, js_reference):
        """
        Evaluate the js_reference and store the value in the object cache on the JS side.
        Return a reference to the cached value.  Name of None will generate an arbitrary fresh name.
        """
        if name is None:
            name = self.get_cache_name()
        do(self.js_object_cache._set(name, js_reference))
        return self.js_object_cache[name]

    def uncache(self, name):
        "Break the reference to the cached object."
        cache = self.js_object_cache
        window = self.window
        return do(window.Reflect.deleteProperty(cache, name))

    def my(self, name):
        "Get reference to a previously cached object on the JS side"
        return self.js_object_cache[name]

    def reference(self, name):
        assert self.gizmo is not None, "gizmo is not configured."
        return getattr(self.gizmo, name)

    def new(self, javascript_class_link, *javascript_argument_links):
        """
        Make a link which when executed will create and return the equivalent of

            new javascript_class(javascript_arguments);
        """
        #return self.gizmo.H5Gizmos.New(javascript_class_link, javascript_argument_links) # doesn't always work?
        return self.window.Reflect.construct(javascript_class_link, javascript_argument_links)

    def function(self, argument_names, body_string):
        """
        Make a link which when executed will return the equivalent of the Javascript function value:

            (function (argument_names) body_string)
        """
        return self.gizmo.H5Gizmos.Function(list(argument_names), body_string)

    async def store_array(self, array, cache_name, dtype=None, timeout=60):
        """
        Transfer a numpy array to Javascript and store it in the local cache using HTTP GET.
        The array is flattened and converted to an appropriate Javascript indexed collection.
        Return a reference to the cached index collection.

        When done with the array in JS, break the array reference with component.uncache(cache_name).
        """
        # XXX add multiple get implementation for VERY large arrays.
        gizmo = self.gizmo
        if dtype is None:
            dtype = array.dtype
        rarray = array.ravel().astype(dtype)
        object = self.js_object_cache
        converter_name = JS_COLLECTION_NAME_MAP.get(dtype)
        assert converter_name is not None, "No JS converter for numpy dtype: " + repr(dtype)
        converter = gizmo.window[converter_name]
        # Set up the blob resource
        url = H5Gizmos.new_identifier("blob")
        array_bytes = rarray.tobytes()
        content_type = "application/x-binary"
        getter = gizmo_server.BytesGetter(url, array_bytes, gizmo._manager, content_type )
        gizmo._add_getter(url, getter)
        # Pull the resource on the JS side.
        try:
            length = await get(gizmo.H5Gizmos.store_blob(url, object, cache_name, converter), timeout=timeout)
            self._store_result = length # for debugging
        finally:
            # Remove the resource
            gizmo._remove_getter(url)
        return self.my(cache_name)

    async def store_json(self, json_object, cache_name, timeout=60):
        """
        Transfer a JSON to Javascript and store it in the local cache using HTTP GET.
        Return a reference to the cached index collection.

        When done with the json object in JS, break the array reference with component.uncache(cache_name).
        """
        # XXX cut/paste/edit from store_array -- refactor?
        import json
        gizmo = self.gizmo
        object = self.js_object_cache
        # Set up the blob resource
        url = H5Gizmos.new_identifier("json")
        json_str = json.dumps(json_object)
        # https://stackoverflow.com/questions/7585435/best-way-to-convert-string-to-bytes-in-python-3
        json_bytes = str.encode(json_str)
        content_type = "application/json"
        getter = gizmo_server.BytesGetter(url, json_bytes, gizmo._manager, content_type )
        gizmo._add_getter(url, getter)
        # Pull the resource on the JS side.
        try:
            response = await get(gizmo.H5Gizmos.store_json(url, object, cache_name), timeout=timeout)
            self._store_result = response # for debugging
        finally:
            # Remove the resource
            gizmo._remove_getter(url)
        return self.my(cache_name)

    def translate_1d_array(self, array):
        """
        Convert a 1d numpy array into an array buffer of a corresponding type if possible in JS.
        Returns a link to a function call for generating the value on JS side.
        """
        dtype = array.dtype
        converter_name = JS_COLLECTION_NAME_MAP.get(dtype);
        if converter_name is not None:
            array_bytes = bytearray( array.tobytes() )
            gizmo = self.gizmo
            result = gizmo.make_array_buffer(converter_name, array_bytes)
            return result
        # default
        return array.tolist()

    async def get_array_from_buffer(self, buffer_reference, dtype=np.uint8, timeout=60):
        """
        Get a binary buffer from Javascript and convert it to a numpy array of the specified dtype.
        """
        gizmo = self.gizmo
        postback = gz_get_blob.BytesPostBack()
        endpoint = H5Gizmos.new_identifier("array_post_endpoint")
        gizmo._add_getter(endpoint, postback)
        json_metadata = {}
        try:
            do(gizmo.H5GIZMO_INTERFACE.post_binary_data(endpoint, buffer_reference, json_metadata))
            data = await postback.wait_for_post(timeout=timeout, on_timeout=self.on_timeout)
        finally:
            gizmo._remove_getter(endpoint)
        (body, query) = data
        data_bytes = bytearray(body)
        return np.frombuffer(data_bytes, dtype=dtype)

    async def get_webgl_image_array(
        self,
        context_reference,
        x=None, 
        y=None, 
        w=None, 
        h=None,
        timeout=60,
    ):
        gizmo = self.gizmo
        postback = gz_get_blob.BytesPostBack()
        endpoint = H5Gizmos.new_identifier("webgl_image_endpoint")
        gizmo._add_getter(endpoint, postback)
        try:
            do(gizmo.H5Gizmos.post_webgl_canvas_image(
                endpoint,
                context_reference,
                x, y, w, h))
            data = await postback.wait_for_post(timeout=timeout, on_timeout=self.on_timeout)
        finally:
            gizmo._remove_getter(endpoint)
        return self.array_from_canvas_data(data)

    async def get_canvas_image_array(
        self, 
        canvas_reference,
        x=None, 
        y=None, 
        w=None, 
        h=None,
        context_reference=None,
        timeout=60):
        gizmo = self.gizmo
        postback = gz_get_blob.BytesPostBack()
        endpoint = H5Gizmos.new_identifier("canvas_image_endpoint")
        gizmo._add_getter(endpoint, postback)
        try:
            do(gizmo.H5Gizmos.post_2d_canvas_image(
                endpoint, 
                canvas_reference, 
                context_reference,
                x, y, w, h))
            data = await postback.wait_for_post(timeout=timeout, on_timeout=self.on_timeout)
        finally:
            gizmo._remove_getter(endpoint)
        return self.array_from_canvas_data(data)

    def array_from_canvas_data(self, data):
        (body, query) = data
        data_bytes = bytearray(body)
        byte_array = np.frombuffer(data_bytes, dtype=np.uint8)
        height = query["height"]
        width = query["width"]
        result = byte_array.reshape((height, width, 4))
        return result

    def on_timeout(self, *ignored):
        raise TimeoutError("Operation timed out")

    def shutdown_parent_only(self, *args):
        import sys
        print("shutting down.")
        sys.exit()
        
    def shutdown(self, *args):
        "Graceful shutdown"
        #import sys
        #print("shutting down.")
        #sys.exit()
        print("scheduling shutdown.")
        schedule_task(self.shutdown_task())

    async def shutdown_task(self, delay=2):
        import sys
        import io
        gizmo = self.gizmo
        try:
            await get(gizmo.H5GIZMO_INTERFACE.shutdown(), timeout=delay)
        except Exception as e:
            print ("Interface shutdown exception", e)
        # sleep to allow delivery of shut down signal...
        #asyncio.sleep(delay)
        print("shutting down.")
        # ignore any error messages to stdio caused by exit
        sys.stderr = self.stdio_redirect = io.StringIO()  # xxx this is hacky...
        sys.exit()
