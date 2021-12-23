
from H5Gizmos.python import gizmo_server
from H5Gizmos.python.gz_resources import MISC_OPERATIONS_TEMPLATE
from . import gz_components
from . import H5Gizmos
from .H5Gizmos import do, get

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
        tr.jquery_info = info;
    };
    return tr.ws_error_message_callback;
}
"""

class jQueryComponent(gz_components.Component):

    init_text = "" # default for subclasses

    def __init__(self, init_text="Uninitialized JQuery Gizmo.", tag="<div/>"):
        self.init_text = init_text
        self.tag = tag
        #self.element_name = H5Gizmos.new_identifier("JQuery_element")
        #self.info_name = H5Gizmos.new_identifier("JQuery_info")
        #self.container_name = H5Gizmos.new_identifier("JQuery_container")
        self.container = None
        self.element = None
        self.info_div = None
        self.initial_css = {}
        self.height = None
        self.width = None

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        gizmo._css_file("../static/jquery-ui-1.12.1/jquery-ui.css")
        gizmo._js_file("../static/jquery-ui-1.12.1/jquery.min.js")
        gizmo._js_file("../static/jquery-ui-1.12.1/jquery-ui.js")
        gizmo._embedded_script(MISC_JAVASCRIPT)
        gizmo._initial_reference("jQuery")
        gizmo._initial_reference("websocket_error_callback", "add_websocket_error_callback()")

    def prepare_application(self, gizmo):
        super().prepare_application(gizmo)
        gizmo._on_callback_exception = self.on_callback_exception

    def on_callback_exception(self, error_text):
        error_text = "JQUERY GIZMO CALLBACK ERROR\n" + error_text
        error_text = error_text.replace("\n", "<br/>\n")
        html = "<pre>%s</pre>" % error_text
        self.error_message(error_text)

    def error_message(self, error_text):
        do(self.gizmo.websocket_error_callback(error_text))

    def dom_element_reference(self, gizmo):
        super().dom_element_reference(gizmo)
        # ??? does it cause harm to always create an extra container around the element ???
        #self.container = name(self.container_name, gizmo.jQuery("<div/>"))
        self.container = self.cache("container", gizmo.jQuery("<div/>"))
        #divtext = "<div>%s</div>" % self.init_text
        self.element = self.cache("element", gizmo.jQuery(self.tag))
        self.resize(width=self.width, height=self.height)
        css = self.initial_css
        if css:
            do(self.element.css(css))
        if self.init_text:
            do(self.element.html(self.init_text))
        do(self.element.appendTo(self.container))
        return self.container[0]

    def js_init(self, js_function_body, to_depth=3, **argument_names_to_values):
        assert self.element is not None, "Gizmo must be displayed for js_init evaluation."
        argument_names = ["element"] + list(argument_names_to_values.keys())
        argument_values = [self.element] + [argument_names_to_values[n] for n in argument_names[1:]]
        function = self.function(argument_names, js_function_body)
        function_call = function(*argument_values)
        do(function_call, to_depth=to_depth)

    def get_info_div(self):
        if self.info_div is None:
            gizmo = self.gizmo
            assert gizmo is not None, "no gizmo to attach"
            self.info_div = self.cache("info", gizmo.jQuery("<div/>"))
            do(self.info_div.appendTo(self.container))
            do(gizmo.H5GIZMO_INTERFACE._set("jquery_info", self.info_div))
            #do(gizmo.add_websocket_error_callback())
        return self.info_div

    def html(self, html_text):
        """
        Set the innerHTML for the element (not appropriate for all subclasses)
        """
        if self.element is None:
            self.init_text = html_text
        else:
            do(self.element.html(html_text))

    def css(self, **name_to_style):
        """
        Set CSS properties of the element before or after the Gizmo is displayed.
        """
        if self.element is not None:
            do(self.element.css(name_to_style))
        else:
            self.initial_css.update(name_to_style)

    def resize(self, width=None, height=None):
        """
        Set width and/or height of element.
        """
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        if self.element is not None:
            if width is not None:
                do(self.element.width(width))
            if height is not None:
                do(self.element.height(height))

    def on(self, event_name, callback, to_depth=1):
        "When an event of this type happens to this object, invoke the callback."
        do(self.element.on(event_name, callback), to_depth=to_depth)

    def off(self, event_name):
        "Cancel event callbacks of this type for this object."
        do(self.element.off(event_name))

    def empty(self):
        "Remove all content from this element."
        do(self.element.empty())

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
        self.on_click = on_click
        if self.element is None:
            return  # not yet configured.
        if on_click is not None:
            do(self.element.on("click", on_click), to_depth=self.on_click_depth)
            do(self.element.prop("disabled", False))
            do(self.element.css("opacity", 1.0))
        else:
            do(self.element.off("click"))
            do(self.element.prop("disabled", True))
            do(self.element.css("opacity", 0.5))

    def dom_element_reference(self, gizmo):
        result = super().dom_element_reference(gizmo)
        self.initialize_jquery_widget()
        return result

class jQueryInput(jQueryComponent):

    def __init__(self, initial_value="", input_type="text"):
        tag = '<input type="%s" value="%s"/>' % (input_type, initial_value)
        super().__init__("", tag=tag)

    def set_value(self, value):
        # https://stackoverflow.com/questions/4088467/get-the-value-in-an-input-text-box?rq=1
        do(self.element.val(value))

    async def get_value(self):
        return await get(self.element.val())


class Slider(jQueryComponent):

    def __init__(self, minimum, maximum, on_change=None, value=None, step=None, orientation="horizontal"):
        assert maximum > minimum, "Bad slider range: " + repr((minimum, maximum))
        if value is None:
            value = minimum
        else:
            if value > maximum:
                value = maximum
            if value < minimum:
                value = minimum
        if step is None:
            step = (maximum - minimum) * 0.01
        super().__init__("")
        self.on_change = on_change
        self.minimum = minimum
        self.maximum = maximum
        self.value = value
        self.step = step
        self.orientation = orientation

    def dom_element_reference(self, gizmo):
        result = super().dom_element_reference(gizmo)
        options = dict(
            min=self.minimum,
            max=self.maximum,
            value=self.value,
            step=self.step,
            slide=self.change_value,
            change=self.change_value,
            orientation = self.orientation,
        )
        do(self.element.slider(options), to_depth=1)
        return result

    def set_value(self, value):
        "Set the value of the slider, triggering any attached callback."
        self.value = value
        do(self.element.slider("value", value))

    async def get_value(self):
        return await get(self.element.slider("value"), to_depth=1)

    def change_value(self, event, ui):
        self.last_event = event
        self.last_ui = ui
        v = self.value = ui["value"]
        c = self.on_change
        if c is not None:
            c(v)


class Stack(jQueryComponent):

    element_css_defaults = {
        "display": "grid",
        "grid-gap": "3px",
        "padding": "3px",
        "border-radius": "3px",
        "background-color": "#ddd",
        #"width": "100vw"
    }

    child_css_defaults = {
        "background-color": "white",
        "padding": "3px",
    }

    def __init__(self, children, tag="<div/>", css=None, child_css=None):
        super().__init__(init_text=None, tag=tag)
        self.children = children
        self.css = css or {}
        self.child_css = child_css or {}
        #self.children_name = H5Gizmos.new_identifier("JQuery_container")
        #self.children_reference = None

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        # also add child dependencies
        for child in self.children:
            child.add_dependencies(gizmo)

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
        references = [self.child_reference(child, gizmo) for child in children]
        #jq = gizmo.jQuery
        #references = [jq(child.dom_element_reference(gizmo)) for child in children]
        #seq = H5Gizmos.GizmoSequence(references, self.gizmo)  # not needed?
        #name(self.children_name, seq)
        css = self.main_css(children)
        css.update(self.element_css_defaults)
        css.update(self.css)
        do(self.element.css(css))
        for (index, childref) in enumerate(references):
            child_css = self.element_css(index)
            child_css.update(self.child_css_defaults)
            child_css.update(self.child_css)
            child_container = gizmo.jQuery("<div/>").css(child_css).appendTo(self.element)
            if childref is not None:
                do(childref.appendTo(child_container))
            else:
                #do(child_container)  # ???? is this needed?
                pass

    def child_reference(self, child, gizmo):
        if child is None:
            return None
        else:
            return gizmo.jQuery(child.dom_element_reference(gizmo))

    def main_css(self, children):
        row_template = "auto"
        col_template = " ".join(["auto"] * len(children))
        # https://stackoverflow.com/questions/47882924/preventing-double-borders-in-css-grid
        css = {
            "grid-template-columns": col_template,
            "grid-template-rows": row_template,
        }
        return css

    def element_css(self, index):
        child_css = {
            "grid-column": "1",
            "grid-row": str(index + 1),  # 1 based indexing
            #"width": "100%",
            #"width": "100%",
            #"overflow": "auto",
            #"padding": "15px",
        }
        return child_css

class Shelf(Stack):
   
    def main_css(self, children):
        col_template = "auto"
        row_template = " ".join(["auto"] * len(children))
        # https://stackoverflow.com/questions/47882924/preventing-double-borders-in-css-grid
        css = {
            "grid-template-columns": col_template,
            "grid-template-rows": row_template,
        }
        return css

    def element_css(self, index):
        child_css = {
            "grid-row": "1",
            "grid-column": str(index + 1),  # 1 based indexing
            #"width": "100%",
            #"width": "100%",
            #"overflow": "auto",
            #"padding": "15px",
        }
        return child_css 


class jQueryImage(jQueryComponent):

    # quick and dirty for now
    version = 0

    def __init__(self, filename, bytes_content, height=None, width=None, mime_type=None, alt="image"):
        self.filename = filename
        self.alt = alt
        self.tag = '<img src="%s" alt="%s"/>' % (self.versioned_link(), self.alt)
        super().__init__(None, self.tag)
        self.bytes_content = bytes_content
        self.height = height
        self.width = width
        self.content_type = mime_type

    '''def resize(self, height=None, width=None):
        #print("resizing", height, width)
        if height is not None:
            self.height = height
            do(self.element.height(height))
        if width is not None:
            self.width = width
            do(self.element.width(width))'''  # duplicate?

    def change_content(self, bytes_content):
        self.bytes_content = bytes(bytes_content)
        self.getter.set_content(bytes_content)
        do(self.element.attr("src", self.versioned_link()))

    def versioned_link(self):
        self.version += 1   # use versioning to foil browser caching.
        return "%s?v=%s" % (self.filename, self.version)

    def dom_element_reference(self, gizmo):
        result = super().dom_element_reference(gizmo)
        mgr = gizmo._manager
        self.getter = gizmo_server.BytesGetter(self.filename, self.bytes_content, mgr, self.content_type)
        #mgr.add_http_handler(self.filename, self.getter)
        gizmo._add_getter(self.filename, self.getter)
        self.resize(height=self.height, width=self.width)
        return result

# aliases
#Html = jQueryComponent

def Html(tag, init_text=None):
    tag = str(tag).strip()
    assert tag.startswith("<"), "The tag should be in a tag form like '<h1>this</h1>': " + repr(tag[:20])
    return jQueryComponent(tag=tag, init_text=init_text)

Button = jQueryButton
Image = jQueryImage
Input = jQueryInput

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
