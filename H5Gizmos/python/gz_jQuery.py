
from H5Gizmos.python.gz_resources import MISC_OPERATIONS_TEMPLATE
from . import gz_components
from . import H5Gizmos
from .H5Gizmos import do, name

MISC_JAVASCRIPT = """
// miscellaneous javascript to support jQuery

function add_websocket_error_callback() {
    var tr = H5GIZMO_INTERFACE;
    tr.ws_error_message_callback = function(message) {
        if (tr.jquery_info) {
            tr.jquery_info.html(message);
            tr.jquery_info.css("background-color", "pink")
        }
    };
}
"""

class jQueryComponent(gz_components.Component):

    def __init__(self, init_text="Uninitialized JQuery Gizmo."):
        self.init_text = init_text
        self.element_name = H5Gizmos.new_identifier("JQuery_element")
        self.info_name = H5Gizmos.new_identifier("JQuery_info")
        self.container_name = H5Gizmos.new_identifier("JQuery_container")
        self.container = None
        self.element = None
        self.info_div = None

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        gizmo._css_file("../static/jquery-ui-1.12.1/jquery-ui.css")
        gizmo._js_file("../static/jquery-ui-1.12.1/jquery.min.js")
        gizmo._js_file("../static/jquery-ui-1.12.1/jquery-ui.js")
        gizmo._embedded_script(MISC_JAVASCRIPT)
        gizmo._initial_reference("jQuery")
        gizmo._initial_reference("add_websocket_error_callback")

    def dom_element_reference(self, gizmo):
        self.container = name(self.container_name, gizmo.jQuery("<div/>"))
        divtext = "<div>%s</div>" % self.init_text
        self.element = name(self.element_name, gizmo.jQuery(divtext))
        do(self.element.appendTo(self.container))
        return self.container[0]

    def get_info_div(self):
        if self.info_div is None:
            gizmo = self.gizmo
            assert gizmo is not None, "no gizmo to attach"
            self.info_div = H5Gizmos.name(self.info_name, gizmo.jQuery("<div/>"))
            do(self.info_div.appendTo(self.container))
            do(gizmo.H5GIZMO_INTERFACE._set("jquery_info", self.info_div))
            do(gizmo.add_websocket_error_callback())
        return self.info_div

# Tests and Demos:

def hello_jquery(message="<h2>Hello world: click me.</h2>"):
    from .H5Gizmos import do
    E = jQueryComponent("initializing jquery component.")
    E.counter = 0

    async def task():
        print("setting message", message)
        do(E.element.html(message))
        print("setting on click", click_callback)
        do(E.element.on("click", click_callback))
        info = E.get_info_div()
        do(info.html("info here."))

    def click_callback(*ignored):
        E.counter += 1
        do(E.element.html("<h1><em>That tickles!</em></h1>"))
        do(E.get_info_div().html("click " + repr(E.counter)))

    E.run(task)
