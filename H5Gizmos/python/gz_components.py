"""
Composable gizmo factories.
"""

from H5Gizmos import do, get, name, run, get_gizmo
from . import gizmo_server
from . import H5Gizmos
import numpy as np

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

    def attach_gizmo(self, gizmo):
        self.gizmo = gizmo
        self.add_dependencies(gizmo)

    def run(self, task=None, verbose=True, log_messages=False):
        self.task = task
        run(self.run_main, verbose=verbose, log_messages=log_messages)

    def prepare_application(self, gizmo):
        self.attach_gizmo(gizmo)
        self.configure_page(gizmo)

    async def run_main(self, gizmo):
        self.prepare_application(gizmo)
        do(gizmo.window.addEventListener("unload", self.shutdown), to_depth=1)
        self.add_std_icon(gizmo)
        await gizmo.start_in_browser()
        #gizmo._start_report_error_task()
        task = self.task
        if task is not None:
            await task()

    def add_std_icon(self, gizmo):
        # https://www.w3.org/2005/10/howto-favicon
        gizmo._add_content(os_path="../static/icon.png", content_type="image/png")
        gizmo._insert_html('<link rel="icon" type="image/png" href="./icon.png"/>', in_body=False)

    async def iframe(self, verbose=False, log_messages=False):
        assert gizmo_server.isnotebook(), "iframe method only runs in IPython kernel."
        gizmo = await get_gizmo(verbose=verbose, log_messages=log_messages)
        self.prepare_application(gizmo)
        await gizmo.start_in_iframe()

    async def browse(self, verbose=True, log_messages=False):
        assert gizmo_server.isnotebook(), "browse method only runs in IPython kernel."
        if verbose:
            print("Displaying gizmo component in new browser window.")
        gizmo = await get_gizmo(verbose=verbose, log_messages=log_messages)
        self.prepare_application(gizmo)
        self.add_std_icon(gizmo)
        await gizmo.start_in_browser()

    def configure_page(self, gizmo):
        self.window = gizmo.window
        self.document = gizmo.document
        body = self.body = gizmo.GIZMO_BODY
        interface = gizmo.H5GIZMO_INTERFACE
        element = self.dom_element_reference(gizmo)
        do(interface._set("Target", element))
        target = self.target = interface.Target
        do(body.append(target))

    def add_dependencies(self, gizmo):
        """
        Add libraries, css files, references, or other resources required by the component to the gizmo.
        """
        gizmo._initial_reference("window")
        gizmo._initial_reference("document")
        gizmo._initial_reference("H5GIZMO_INTERFACE")
        gizmo._initial_reference("H5Gizmos")
        gizmo._initial_reference("GIZMO_BODY", 'document.getElementById("GIZMO_BODY")')

    def dom_element_reference(self, gizmo):
        """
        initialize and return a reference to the DOM element for this component.
        """
        self.gizmo = gizmo
        self.initialize_object_cache()
        return "Undefined gizmo component."  # override return value in subclass.

    def initialize_object_cache(self):
        gizmo = self.gizmo
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

    def my(self, name):
        "Get reference to a previously cached object on the JS side"
        return self.js_object_cache[name]

    def new(self, javascript_class_link, *javascript_argument_links):
        """
        Make a link which when executed will create and return the equivalent of

            new javascript_class(javascript_arguments);
        """
        return self.gizmo.H5Gizmos.New(javascript_class_link, javascript_argument_links)

    def function(self, argument_names, body_string):
        """
        Make a link which when executed will return the equivalent of the Javascript function value:

            (function (argument_names) body_string)
        """
        return self.gizmo.H5Gizmos.Function(list(argument_names), body_string)


    async def store_array(self, array, cache_name, dtype=None):
        """
        Transfer a numpy array to Javascript and store it in the local cache.
        The array is flattened and converted to an appropriate Javascript indexed collection.
        Return a reference to the cached index collection.
        """
        #element = self.element
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
            length = await get(gizmo.H5Gizmos.store_blob(url, object, cache_name, converter))
        finally:
            # Remove the resource
            gizmo._remove_getter(url)
        return self.my(cache_name)
        
    def shutdown(self, *args):
        "Graceful shutdown"
        import sys
        print("shutting down.")
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
