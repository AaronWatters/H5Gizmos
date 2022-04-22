"""
Composable gizmo factories.
"""

# run should work in jupyter -- delegate to browse when jupyter env detected.

#from time import time
#from numpy.lib.function_base import _ARGUMENT
from H5Gizmos import do, get, name, run, get_gizmo, schedule_task
from . import gizmo_server
from . import H5Gizmos
from . import gz_get_blob
import numpy as np
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
    close_button = True
    gizmo_configured = False

    def attach_gizmo(self, gizmo):
        self.gizmo = gizmo
        self.add_dependencies(gizmo)
        # add deferred dependencies after standard dependencies (for example so jQuery is available in deferred code)
        self.add_deferred_dependencies(gizmo)
        gizmo._translate_1d_array = self.translate_1d_array
        self.gizmo_configured = True

    def run(self, task=None, auto_start=True, verbose=True, log_messages=False, close_button=True):
        self.task = task
        self.auto_start = auto_start
        self.close_button = close_button
        run(self.run_main, verbose=verbose, log_messages=log_messages)

    def prepare_application(self, gizmo):
        self.attach_gizmo(gizmo)
        self.configure_page(gizmo)

    async def run_main(self, gizmo):
        self.prepare_application(gizmo)
        self.shutdown_on_unload(gizmo)
        self.add_std_icon(gizmo)
        if self.close_button:
            gizmo._insert_html('<button onclick="self.close()">Close</button>')
        if self.auto_start:
            await gizmo.start_in_browser()
        else:
            await gizmo._show_start_link()
        #gizmo._start_report_error_task()
        task = self.task
        if task is not None:
            await task()

    def shutdown_on_unload(self, gizmo):
        do(gizmo.window.addEventListener("unload", self.shutdown_parent_only), to_depth=1)

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
        try:
            H5Gizmos.check_browser()
        except Exception:
            return await self.link(verbose=verbose, log_messages=log_messages, title=title)
        else:
            return await self.browse(verbose=verbose, log_messages=log_messages, title=title)

    async def iframe(self, height=20, verbose=False, log_messages=False):
        assert gizmo_server.isnotebook(), "iframe method only runs in IPython kernel."
        gizmo = await get_gizmo(verbose=verbose, log_messages=log_messages)
        self.prepare_application(gizmo)
        await gizmo.start_in_iframe(height=height)

    async def browse(
        self, 
        title="Gizmo",
        auto_start=True, 
        verbose=True, 
        log_messages=False, 
        close_button=True,
        await_start=True,
        ):
        if auto_start:
            H5Gizmos.check_browser()
        in_notebook = gizmo_server.isnotebook()
        if verbose:
            print("Displaying gizmo component in new browser window.")
        gizmo = await get_gizmo(verbose=verbose, log_messages=log_messages, title=title)
        if close_button:
            gizmo._insert_html('<button onclick="self.close()">Close</button>')
        self.prepare_application(gizmo)
        if verbose:
            print("   entry_url=", gizmo._entry_url())
        #if close_button:
        #    gizmo._insert_html('<button onclick="self.close()">Close</button>')
        if not in_notebook:
            self.shutdown_on_unload(gizmo)
        self.add_std_icon(gizmo)
        if auto_start:
            await gizmo.start_in_browser()
        else:
            if await_start:
                await gizmo._show_start_link()

    async def link(self, title="Gizmo", verbose=False, log_messages=False, await_start=True):
        await self.browse(
            title=title,
            auto_start=False, 
            verbose=verbose, 
            log_messages=log_messages,
            await_start=await_start,
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
        self.window = gizmo.window
        self.document = gizmo.document
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
        stylesheet_path = self.stylesheet_path
        if (stylesheet_path):
            gizmo._css_file(stylesheet_path)
        gizmo._initial_reference("window")
        gizmo._initial_reference("document")
        gizmo._initial_reference("H5GIZMO_INTERFACE")
        gizmo._initial_reference("H5Gizmos")
        gizmo._initial_reference("make_array_buffer", "H5Gizmos.make_array_buffer")
        gizmo._initial_reference("GIZMO_BODY", 'document.getElementById("GIZMO_BODY")')
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

    def serve_folder(self, url_file_name, os_path):
        "Serve files from folder locally, guessing MIME type.."
        if self.gizmo is not None:
            return self.gizmo._serve_folder(url_file_name, os_path)
        return self.dependency("_serve_folder", (url_file_name, os_path))

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
        self.initialize_object_cache()
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

class HelloComponent(Component):
    
    def __init__(self, text="Hello world"):
        self.text = text

    def dom_element_reference(self, gizmo):
        super().dom_element_reference(gizmo)
        return self.text

def test_standalone():
    hello = HelloComponent()
    hello.run(verbose=False)
