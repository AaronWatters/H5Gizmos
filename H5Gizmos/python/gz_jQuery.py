
from H5Gizmos.python.gz_resources import MISC_OPERATIONS_TEMPLATE
from . import gz_components
from . import H5Gizmos
from .H5Gizmos import do, name

MISC_JAVASCRIPT = """
// miscellaneous javascript to support jQuery

function add_websocket_error_callback() {
    var tr = H5GIZMO_INTERFACE;
    tr.ws_error_message_callback = function(message) {
        var info = tr.jquery_info;
        if (!info) {
            info = $("<div/>").appendTo($("#GIZMO_BODY"));
        }
        info.html(message);
        info.css("background-color", "pink")
    };
    return tr.ws_error_message_callback;
}
"""

class jQueryComponent(gz_components.Component):

    def __init__(self, init_text="Uninitialized JQuery Gizmo.", tag="<div/>"):
        self.init_text = init_text
        self.tag = tag
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
        gizmo._initial_reference("websocket_error_callback", "add_websocket_error_callback()")

    def dom_element_reference(self, gizmo):
        super().dom_element_reference(gizmo)
        # ??? does it cause harm to always create an extra container around the element ???
        self.container = name(self.container_name, gizmo.jQuery("<div/>"))
        #divtext = "<div>%s</div>" % self.init_text
        self.element = name(self.element_name, gizmo.jQuery(self.tag))
        if self.init_text:
            do(self.element.html(self.init_text))
        do(self.element.appendTo(self.container))
        return self.container[0]

    def get_info_div(self):
        if self.info_div is None:
            gizmo = self.gizmo
            assert gizmo is not None, "no gizmo to attach"
            self.info_div = H5Gizmos.name(self.info_name, gizmo.jQuery("<div/>"))
            do(self.info_div.appendTo(self.container))
            do(gizmo.H5GIZMO_INTERFACE._set("jquery_info", self.info_div))
            #do(gizmo.add_websocket_error_callback())
        return self.info_div

class jQueryButton(jQueryComponent):

    options = None  # default
    on_click = None
    
    def __init__(self, init_text, tag="<button/>", on_click=None, options=None):
        super().__init__(init_text, tag)
        self.options = options
        self.on_click = on_click

    widget_name = "button"
    on_click_depth = 1

    def initialize_jquery_widget(self):
        options = self.options
        initializer = self.element[self.widget_name]
        if options is not None:
            do(initializer(options))
        else:
            do(initializer())
        self.set_on_click(self.on_click)

    def set_on_click(self, on_click):
        if on_click is not None:
            do(self.element.on("click", on_click), to_depth=self.on_click_depth)
            do(self.element.prop("disabled", False))
        else:
            do(self.element.off("click"))
            do(self.element.prop("disabled", True))

    def dom_element_reference(self, gizmo):
        result = super().dom_element_reference(gizmo)
        self.initialize_jquery_widget()
        return result

class Stack(jQueryComponent):

    def __init__(self, children, tag="<div/>", background="#999", child_background="white"):
        super().__init__(init_text=None, tag=tag)
        self.children = children
        self.background = background
        self.child_background = child_background
        self.children_name = H5Gizmos.new_identifier("JQuery_container")
        self.children_reference = None

    def dom_element_reference(self, gizmo):
        result = super().dom_element_reference(gizmo)
        self.attach_children(self.children)
        return result

    def attach_children(self, children):
        gizmo = self.gizmo
        assert gizmo is not None, "gizmo must be attached."
        do(self.element.empty())
        self.children = children
        # xxxx maybe use child.element?
        jq = gizmo.jQuery
        references = [jq(child.dom_element_reference(gizmo)) for child in children]
        seq = H5Gizmos.GizmoSequence(references, self.gizmo)
        name(self.children_name, seq)
        row_template = "auto"
        col_template = " ".join(["auto"] * len(children))
        # https://stackoverflow.com/questions/47882924/preventing-double-borders-in-css-grid
        css = {
            "display": "grid",
            "grid-template-columns": col_template,
            "grid-template-rows": row_template,
            #"grid-gap": "3px",
            "padding": "3px",
            "border-radius": "3px",
            #"width": "100vw"
        }
        bg = self.background
        if bg is not None:
            css["background-color"] = bg
        do(self.element.css(css))
        cb = self.child_background
        for (rownum, childref) in enumerate(references):
            css = {
                "grid-column": "1",
                "grid-row": str(rownum + 1),  # 1 based indexing
                #"width": "100%",
                #"width": "100%",
                #"overflow": "auto",
                "padding": "15px",
            }
            if cb is not None:
                css["background-color"] = cb
            if bg is not None:
                css["border"] = "1px solid " + str(bg)
            child_container = gizmo.jQuery("<div/>").css(css).appendTo(self.element)
            do(childref.appendTo(child_container))
            #do(childref.appendTo(self.element))
            #do(childref.css(css))

# aliases
Html = jQueryComponent
Button = jQueryButton

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