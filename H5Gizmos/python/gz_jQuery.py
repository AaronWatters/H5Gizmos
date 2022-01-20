
from H5Gizmos.python import gizmo_server
from H5Gizmos.python.gz_resources import MISC_OPERATIONS_TEMPLATE
from . import gz_components
from . import H5Gizmos
from .H5Gizmos import do, get
import html

# add Markdown(...)
# new method jqc.append(other_jqc)
# maybe prints default to appending...

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
};
"""

class jQueryComponent(gz_components.Component):

    init_text = "" # default for subclasses
    title_string = None

    def __init__(self, init_text="Uninitialized JQuery Gizmo.", tag="<div/>", title=None):
        if title:
            self.set_title(title)
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
        self.tooltips_enabled = False

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

    def get_element(self, gizmo):
        if self.element is None:
            self.dom_element_reference(gizmo)
        return self.element

    def enable_tooltips(self):
        "Enable jQueryUI tool tips for the whole gizmo document."
        self.tooltips_enabled = True
        if self.gizmo:
            # only enable tooltips after gizmo connect...
            do(self.jQuery(self.window.document).tooltip())

    def set_title(self, title_string):
        ty = type(title_string)
        assert ty is str, "Element title must be a string: " + repr(ty)
        self.title_string = title_string

    def dom_element_reference(self, gizmo):
        super().dom_element_reference(gizmo)
        # ??? does it cause harm to always create an extra container around the element ???
        #self.container = name(self.container_name, gizmo.jQuery("<div/>"))
        self.container = self.cache("container", gizmo.jQuery("<div/>"))
        # Convenience access to jQuery reference:
        self.jQuery = gizmo.jQuery
        #divtext = "<div>%s</div>" % self.init_text
        self.element = self.cache("element", gizmo.jQuery(self.tag))
        self.resize(width=self.width, height=self.height)
        css = self.initial_css
        if css:
            do(self.element.css(css))
        if self.init_text:
            do(self.element.html(self.init_text))
        if self.title_string:
            do(self.element.prop("title", self.title_string))
        if self.tooltips_enabled:
            self.enable_tooltips()
        do(self.element.appendTo(self.container))
        self.configure_jQuery_element(self.element)
        return self.container[0]

    def add(self, component, title=None):
        """
        Add a JQuery component after this one or the last add.
        The new component should not require dependancies which have not been loaded
        previously into the gizmo.
        """
        gizmo = self.gizmo
        if not isinstance(component, jQueryComponent):
            ty = type(component)
            assert type(component) is str, "Only strings or jQuery components may be added: " + repr(ty)
            component = Text(component, title=title)
        do(component.get_element(gizmo).appendTo(self.container))
        return component

    def configure_jQuery_element(self, element):
        "For subclasses: configure the jQuery element by adding children or callbacks, etc."
        pass  # do nothing herre.

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
        Set the innerHTML for the element (not appropriate for all subclasses).
        """
        if self.element is None:
            self.init_text = html_text
        else:
            do(self.element.html(html_text))

    def text(self, string_text):
        """
        Set the innerHTML for the element to plain HTML escaped text (not appropriate for all subclasses).
        """
        html_text = html.escape(string_text)
        return self.html(html_text)

    def css(self, dict=None, **name_to_style):
        """
        Set CSS properties of the element before or after the Gizmo is displayed.
        """
        styles = {}
        styles.update(name_to_style)
        if dict is not None:
            styles.update(dict)
        if self.element is not None:
            do(self.element.css(styles))
        else:
            self.initial_css.update(styles)

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
    
    def __init__(self, init_text, tag="<button/>", on_click=None, options=None, title=None):
        super().__init__(init_text, tag, title=title)
        self.options = options
        self.on_click = on_click

    widget_name = "button"
    on_click_depth = 1

    def configure_jQuery_element(self, element):
        options = self.options
        initializer = element[self.widget_name]
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

class RadioButtons(jQueryComponent):

    # based on https://api.jqueryui.com/checkboxradio/

    input_type = "radio"

    def __init__(
        self, 
        label_value_pairs, 
        selected_value=None, 
        legend=None, 
        on_click=None, 
        options=None,
        title=None,
        ):
        """
        Create a radio button fieldset for the label/pair values.
        If onclick is provided it will be called with on_click(value) when the corresponding
        radio button is selected.
        """
        self.checkbox_radio_common_init(
            label_value_pairs,
            legend,
            on_click,
            options,
            title
        )
        self.select_values(selected_value)

    def checkbox_radio_common_init(
        self,
        label_value_pairs,
        legend,
        on_click,
        options,
        title
        ):
        tag = "<fieldset/>"
        super().__init__(init_text="", tag=tag, title=title)
        label_value_pairs = [(label, value) for (label, value) in label_value_pairs]
        self.label_value_pairs = label_value_pairs
        #self.labels = [pair[0] for pair in label_value_pairs]
        self.values = [pair[1] for pair in label_value_pairs]
        #assert selected_value is None or selected_value in self.values, \
        #    "no such value to select: " + repr(selected_value)
        #self.selected_value = selected_value
        self.legend = legend
        self.on_click = on_click
        self.options = options or {}
        self.id2value = None

    def select_values(self, *values):
        selected_values = []
        for value in values:
            if value is not None:
                assert value in self.values, \
                    "no such value to select: " + repr((value, self.values))
                selected_values.append(value)
        self.selected_values = selected_values

    def configure_jQuery_element(self, element):
        id2value = {}
        gizmo = self.gizmo
        legend = self.legend
        options = self.options
        #selected_value = self.selected_value
        label_value_pairs = self.label_value_pairs
        jQuery = gizmo.jQuery
        name = H5Gizmos.new_identifier("gzRadioName")
        if legend:
            legend_tag = "<legend>%s</legend>" % legend
            do(jQuery(legend_tag).appendTo(element))
        ty = self.input_type
        for (label, value) in label_value_pairs:
            checked = ""
            if value in self.selected_values:
                checked = " checked "
            #input_options = options.copy()
            #input_options["label"] = label
            identity = H5Gizmos.new_identifier("gzRadio")
            id2value[identity] = value
            label_tag = '<label for="%s">%s</label>' % (identity, label)
            do(jQuery(label_tag).appendTo(self.element))
            input_tag = '<input type="%s" name="%s" id="%s" value="%s" %s/>' %(
                ty, name, identity, identity, checked
            )
            do(jQuery(input_tag).appendTo(element))
        selector = "input[name=%s]" % name
        self.selector_checked = selector + ":checked"
        do(self.element.find(selector).checkboxradio(options))
        do(self.element.find(selector).change(self.check_value), to_depth=1)
        self.id2value = id2value

    def check_value(self, *ignored):
        #print("check", ignored)
        #self.add("clicked!")
        H5Gizmos.schedule_task(self.update_value())

    async def update_value(self):
        gizmo = self.gizmo
        jQuery = gizmo.jQuery
        selector = self.selector_checked
        id = await get(jQuery(selector).attr("id"))
        value = self.id2value[id]
        #self.add("got id %s with value %s" % (repr(id), repr(value)))
        #self.selected_value = value
        self.select_values(value)
        on_click = self.on_click
        if on_click:
            on_click(value)
        #print("update done!")

class CheckBoxes(RadioButtons):

    input_type = "checkbox"

    def __init__(
        self, 
        label_value_pairs, 
        selected_values=(), 
        legend=None, 
        on_click=None, 
        options=None,
        title=None,
        ):
        """
        Create a radio button fieldset for the label/pair values.
        If onclick is provided it will be called with on_click(value) when the corresponding
        radio button is selected.
        """
        self.checkbox_radio_common_init(
            label_value_pairs,
            legend,
            on_click,
            options,
            title
        )
        self.select_values(*selected_values)

    async def update_value(self):
        gizmo = self.gizmo
        jQuery = gizmo.jQuery
        id2value = self.id2value
        selected_values = []
        for identifier in id2value:
            checked = await get(jQuery("#" + identifier)[0].checked)
            #print("for", identifier, "checked is", checked)
            if checked:
                value = id2value[identifier]
                selected_values.append(value)
        self.select_values(*selected_values)
        on_click = self.on_click
        if on_click:
            on_click(selected_values)

class DropDownSelect(RadioButtons):

    def configure_jQuery_element(self, element):
        id2value = {}
        gizmo = self.gizmo
        jQuery = gizmo.jQuery
        legend = self.legend
        options = self.options
        label_value_pairs = self.label_value_pairs
        name = H5Gizmos.new_identifier("gzSelectName")
        if legend:
            legend_tag = '<label for="%s">%s</label>' % (name, legend)
            do(jQuery(legend_tag).appendTo(element))
        select_tag = '<select name="%s" id="%s"/>'
        select = self.cache("select", jQuery(select_tag))
        do(select.appendTo(element))
        for (label, value) in label_value_pairs:
            selected = ""
            if value in self.selected_values:
                selected = " selected "
            identity = H5Gizmos.new_identifier("gzOption")
            option_tag = '<option value="%s" %s>%s</option>' % (identity, selected, label)
            do(jQuery(option_tag).appendTo(select))
            id2value[identity] = value
        self.id2value = id2value
        do(select.selectmenu(options))
        do(select.on('selectmenuchange', self.check_value), to_depth=1)
        self.select = select

    async def update_value(self):
        identifier = await get(self.select.val())
        value = self.id2value[identifier]
        self.select_values(value)
        on_click = self.on_click
        if on_click:
            on_click(value)

class jQueryInput(jQueryComponent):

    def __init__(
        self, 
        initial_value="", 
        input_type="text", 
        size=None, 
        change_callback=None,
        title=None):
        sizetext = ""
        if size is not None:
            sizetext = ' size="%s"' % size
        tag = '<input type="%s" value="%s" %s/>' % (input_type, initial_value, sizetext)
        super().__init__("", tag=tag, title=title)
        self.value = initial_value
        self.last_event = None # for debug
        self.change_callback = change_callback

    def configure_jQuery_element(self, element):
        do(element.on("input", self.on_change), to_depth=2)

    def on_change(self, event):
        self.last_event = event   # for debugging
        target = event.get("target")
        if target is not None:
            value = target.get("value")
            if value is not None:
                self.value = value
                if self.change_callback is not None:
                    self.change_callback(value)

    def set_value(self, value):
        # https://stackoverflow.com/questions/4088467/get-the-value-in-an-input-text-box?rq=1
        do(self.element.val(value))
        self.value = value

    async def get_value(self):
        value = await get(self.element.val())
        self.value = value


class Slider(jQueryComponent):

    def __init__(
        self, 
        minimum, 
        maximum, 
        on_change=None, 
        value=None, 
        step=None, 
        orientation="horizontal",
        title=None,
        ):
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
        super().__init__("", title=title)
        self.on_change = on_change
        self.minimum = minimum
        self.maximum = maximum
        self.value = value
        self.step = step
        self.orientation = orientation

    def configure_jQuery_element(self, element):
        options = dict(
            min=self.minimum,
            max=self.maximum,
            value=self.value,
            step=self.step,
            slide=self.change_value,
            change=self.change_value,
            orientation = self.orientation,
        )
        do(element.slider(options), to_depth=1)

    def set_value(self, value):
        "Set the value of the slider, triggering any attached callback."
        self.value = value
        do(self.element.slider("value", value))

    async def get_value(self):
        value = await get(self.element.slider("value"), to_depth=1)
        self.value = value
        return value

    def change_value(self, event, ui):
        self.last_event = event
        self.last_ui = ui
        v = self.value = ui["value"]
        c = self.on_change
        if c is not None:
            c(v)

class RangeSlider(jQueryComponent):

    # xxx cut/paste from Slider -- too hard to refactor for now

    def __init__(
        self, 
        minimum, 
        maximum, 
        on_change=None, 
        low_value=None, 
        high_value=None, 
        step=None, 
        orientation="horizontal",
        title=None,
        ):
        assert maximum > minimum, "Bad slider range: " + repr((minimum, maximum))
        if low_value is None:
            low_value = minimum
        if high_value is None:
            high_value = maximum
        lw = min(low_value, high_value, maximum)
        hg = max(high_value, low_value, minimum)
        low_value = min(lw, hg)
        high_value = max(lw, hg)
        if step is None:
            step = (maximum - minimum) * 0.01
        super().__init__("", title=title)
        self.on_change = on_change
        self.minimum = minimum
        self.maximum = maximum
        self.low_value = low_value
        self.high_value = high_value
        self.step = step
        self.orientation = orientation
        self.values = None

    def configure_jQuery_element(self, element):
        options = dict(
            min=self.minimum,
            max=self.maximum,
            values=[self.low_value, self.high_value],
            step=self.step,
            slide=self.change_value,
            change=self.change_value,
            orientation = self.orientation,
        )
        do(element.slider(options), to_depth=2)

    def set_range(self, minimum=None, maximum=None, step=None):
        if minimum is not None:
            self.minimum = minimum
        if maximum is not None:
            self.maximum = maximum
        if step is not None:
            self.step = step
        do(self.element.slider("option", "min", self.minimum))
        do(self.element.slider("option", "max", self.maximum))
        #do(self.element.slider("step", self.step))

    def set_values(self, low_value=None, high_value=None):
        "Set the value of the slider, triggering any attached callback."
        if low_value is not None:
            self.low_value = low_value
        if high_value is not None:
            self.high_value = high_value
        values = [self.low_value, self.high_value]
        do(self.element.slider("values", values))

    async def get_values(self):
        values = await get(self.element.slider("values"), to_depth=1)
        [self.low_value, self.high_value] = values
        self.values = values
        return values

    def change_value(self, event, ui):
        self.last_event = event
        self.last_ui = ui
        values = ui["values"]
        self.values = values
        [self.low_value, self.high_value] = values
        c = self.on_change
        if c is not None:
            c(values)


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

    def __init__(
        self, 
        children, 
        tag="<div/>", 
        css=None, 
        child_css=None,
        title=None,
        ):
        super().__init__(init_text=None, tag=tag, title=title)
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

    def add_deferred_dependencies(self, gizmo):
        super().add_deferred_dependencies(gizmo)
        # also add child dependencies
        for child in self.children:
            child.add_deferred_dependencies(gizmo)

    def configure_jQuery_element(self, element):
        self.attach_children(self.children)

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

    def __init__(
        self, 
        filename, 
        bytes_content, 
        height=None, 
        width=None, 
        mime_type=None, 
        alt="image",
        title=None,
        ):
        self.filename = filename
        self.alt = alt
        self.tag = '<img src="%s" alt="%s"/>' % (self.versioned_link(), self.alt)
        super().__init__(None, self.tag, title=title)
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

    def configure_jQuery_element(self, element):
        gizmo = self.gizmo
        mgr = gizmo._manager
        self.getter = gizmo_server.BytesGetter(self.filename, self.bytes_content, mgr, self.content_type)
        #mgr.add_http_handler(self.filename, self.getter)
        gizmo._add_getter(self.filename, self.getter)
        self.resize(height=self.height, width=self.width)

# aliases
#Html = jQueryComponent

class jQueryLabel(jQueryComponent):

    def __init__(self, label_text, label_for_component, title=None):
        self.label_text = label_text
        self.label_for_component = label_for_component
        super().__init__(init_text=label_text, tag="<label/>", title=title)

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        # also add child dependencies
        self.label_for_component.add_dependencies(gizmo)

    def add_deferred_dependencies(self, gizmo):
        super().add_deferred_dependencies(gizmo)
        # also add child dependencies
        self.label_for_component.add_deferred_dependencies(gizmo)

    def configure_jQuery_element(self, element):
        gizmo = self.gizmo
        #label_for_ref = gizmo.jQuery(self.label_for_component.dom_element_reference(self.gizmo))
        label_for_ref = self.label_for_component.get_element(gizmo)
        do(label_for_ref.appendTo(element))

def contain_in_label(label_text, component, title=None):
    """
    Add a container surrounding the component.
    Access the container using `component.label_container`.
    Use the container instead of the component, for exampla, as a child of Stack.
    """
    component.label_container = jQueryLabel(label_text, component, title=title)
    component.label_text = label_text
    return component

class LabelledjQueryInput(jQueryInput):

    def __init__(
        self, 
        label_text, 
        initial_value="", 
        input_type="text", 
        size=None, 
        change_callback=None,
        title=None,
        ):
        super().__init__(initial_value, input_type, size, change_callback)
        contain_in_label(label_text, self, title=title)


def Html(tag, init_text=None, title=None):
    tag = str(tag).strip()
    assert tag.startswith("<"), "The tag should be in a tag form like '<h1>this</h1>': " + repr(tag[:20])
    return jQueryComponent(tag=tag, init_text=init_text, title=title)

def Text(content, title=None):
    "Simple text, escaped."
    econtent = html.escape(content)
    return Html("<div>%s</div>"  % str(econtent), title=title)

Button = jQueryButton
Image = jQueryImage
Input = jQueryInput
LabelledInput = LabelledjQueryInput

# Tests and Demos:

def hello_jquery(message="<h2>Hello world: click me.</h2>", auto_start=False):
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

    E.run(task, auto_start=auto_start)
