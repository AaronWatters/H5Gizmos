
import numpy as np
from H5Gizmos.python import gizmo_server
#from H5Gizmos.python.gz_resources import MISC_OPERATIONS_TEMPLATE
from . import gz_components
from . import H5Gizmos
from .H5Gizmos import do, get, schedule_task
import html
import io
import asyncio

# add Markdown(...)
# new method jqc.append(other_jqc)
# maybe Prints default to appending...

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
    on_click_depth = 1
    radio_on_click = None

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
        self.is_dialog = False
        self.on_click = None
        self.cached_dom_element_reference = None
        self.class_list = []

    def __repr__(self):
        def truncate(x):
            if x:
                x = str(x)
                if len(x) > 20:
                    x = x[:20] + "..."
            return x
        t = truncate(self.tag)
        i = truncate(self.init_text)
        return self.__class__.__name__ + repr( (t, i))

    def set_on_click(self, on_click):
        self.on_click = on_click
        if self.element is None:
            return  # not yet configured.
        if on_click is not None:
            do(self.element.on("click", on_click), to_depth=self.on_click_depth)
        else:
            do(self.element.off("click"))
        return self

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        #gizmo._css_file("../static/jquery-ui-1.12.1/jquery-ui.css")
        #gizmo._js_file("../static/jquery-ui-1.12.1/jquery.min.js")
        #gizmo._js_file("../static/jquery-ui-1.12.1/jquery-ui.js")
        gizmo._relative_css("GIZMO_STATIC/jquery-ui-1.12.1/jquery-ui.css")
        gizmo._relative_css("GIZMO_STATIC/JQuery_overrides.css")
        gizmo._relative_js("GIZMO_STATIC/jquery-ui-1.12.1/jquery.min.js")
        gizmo._relative_js("GIZMO_STATIC/jquery-ui-1.12.1/jquery-ui.js")
        gizmo._embedded_script(MISC_JAVASCRIPT)
        gizmo._initial_reference("jQuery")
        gizmo._initial_reference("websocket_error_callback", "add_websocket_error_callback()")

    def prepare_application(self, gizmo):
        super().prepare_application(gizmo)
        gizmo._on_callback_exception = self.on_callback_exception

    def on_callback_exception(self, error_text):
        error_text = "JQUERY GIZMO CALLBACK ERROR\n" + error_text
        error_text = error_text.replace("\n", "<br/>\n")
        #html = "<pre>%s</pre>" % error_text
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
        # xxxx need to change title if executing...
        ty = type(title_string)
        assert ty is str, "Element title must be a string: " + repr(ty)
        self.title_string = title_string
        return self

    def dom_element_reference(self, gizmo):
        result = self.cached_dom_element_reference
        if result is not None:
            return result
        super().dom_element_reference(gizmo)
        # ??? does it cause harm to always create an extra container around the element ???
        #self.container = name(self.container_name, gizmo.jQuery("<div/>"))
        self.container = self.cache("container", gizmo.jQuery("<div/>"))
        # Convenience access to jQuery reference:
        self.jQuery = gizmo.jQuery
        #divtext = "<div>%s</div>" % self.init_text
        self.element = self.cache("element", gizmo.jQuery(self.tag))
        self.resize(width=self.width, height=self.height)
        classes = " ".join(self.class_list)
        if classes:
            do(self.element.addClass(classes))
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
        # Set on_click after element has been configured -- order important for Button
        if self.radio_on_click is None:
            self.set_on_click(self.on_click)
        result = self.container[0]
        self.cached_dom_element_reference = result
        return result

    def add(self, component, title=None):
        """
        Append a JQuery component after a started gizmo.
        The new component should not require dependancies which have not been loaded
        before the gizmo started.
        Return the added component.
        """
        gizmo = self.gizmo
        assert gizmo is not None, "add() only to a component of a started gizmo."
        if not isinstance(component, jQueryComponent):
            ty = type(component)
            assert type(component) is str, "Only strings or jQuery components may be added: " + repr(ty)
            component = Text(component, title=title)
        else:
            if title:
                component.set_title(title)
        do(component.get_element(gizmo).appendTo(self.container))
        return component

    def add_pyplot(self, title=None):
        """
        Context manager to append a plot.  For example:

        from H5Gizmos import Html
        import matplotlib.pyplot as plt

        H = Html("<h2>an example plot</h2>")
        await H.browse()
        with H.add_pyplot():
            fig= plt.figure()
            plt.plot(range(10))
        """
        P = Plotter()
        return self.add(P, title=title)

    def add_dialog(self, text_or_component, dialog_options=None, title=None, to_depth=1):
        """
        Add a JQueryUI dialog after the gizmo has started.
        Options should be a dictionary of jQueryUI dialog options.
        See https://api.jqueryui.com/dialog/ for options documentation.
        Return the dialog component.
        """
        assert self.gizmo is not None, "add dialog only to a component of a started gizmo."
        if dialog_options is None:
            dialog_options = {}
        component = self.add(text_or_component, title)
        do(component.element.dialog(dialog_options), to_depth=to_depth)
        component.is_dialog = True
        return component

    def close_dialog(self):
        """
        Close this dialog.  Error if the component is not a jQueryUI dialog.
        """
        assert self.is_dialog, "This operation is only valid for dialogs."
        do(self.element.dialog("close"))
        return self

    def open_dialog(self):
        """
        Open this dialog.  Error if the component is not a jQueryUI dialog.
        """
        assert self.is_dialog, "This operation is only valid for dialogs."
        do(self.element.dialog("open"))
        return self

    def configure_jQuery_element(self, element):
        "For subclasses: configure the jQuery element by adding children or callbacks, etc."
        pass  # do nothing here.

    def js_init(self, js_function_body, to_depth=3, **argument_names_to_values):
        assert self.element is not None, "Gizmo must be displayed for js_init evaluation."
        argument_names = ["element"] + list(argument_names_to_values.keys())
        argument_values = [self.element] + [argument_names_to_values[n] for n in argument_names[1:]]
        function = self.function(argument_names, js_function_body)
        function_call = function(*argument_values)
        do(function_call, to_depth=to_depth)

    def js_debug(self):
        self.js_init("debugger;")

    def get_info_div(self):
        "Attach a DIV to the surrounding container for displaying miscellaneous information."
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
        return self

    def text(self, string_text):
        """
        Set the innerHTML for the element to plain HTML escaped text (not appropriate for all subclasses).
        """
        html_text = html.escape(string_text)
        return self.html(html_text)
        #return self

    def css(self, dict=None, **name_to_style):
        """
        Set CSS properties of the element before or after the Gizmo is displayed.
        """
        styles = {}
        styles.update(name_to_style)
        if dict is not None:
            styles.update(dict)
        if styles:
            if self.element is not None:
                do(self.element.css(styles))
            else:
                self.initial_css.update(styles)
        return self

    def addClass(self, class_string):
        classes = class_string.split()
        if classes:
            for css_class in classes:
                if css_class not in self.class_list:
                    self.class_list.append(css_class)
            if self.element is not None:
                do(self.element.addClass(class_string))
        return self

    def removeClass(self, class_string):
        classes = class_string.split()
        if classes:
            for css_class in classes:
                if css_class in self.class_list:
                    self.class_list.remove(css_class)
            if self.element is not None:
                do(self.element.removeClass(class_string))
        return self

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
                do(self.container.width(width))
            if height is not None:
                do(self.element.height(height))
                do(self.container.height(height))
        return self

    def on(self, event_name, callback, to_depth=1):
        "When an event of this type happens to this object, invoke the callback."
        do(self.element.on(event_name, callback), to_depth=to_depth)
        return self

    def off(self, event_name):
        "Cancel event callbacks of this type for this object."
        do(self.element.off(event_name))
        return self

    def empty(self):
        "Remove all content from this element."
        do(self.element.empty())
        return self

    def focus(self):
        "Set focus to this element."
        do(self.element.focus())
        return self

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
        #self.set_on_click(self.on_click) # called in super()

    def set_on_click(self, on_click):
        self.on_click = on_click
        if self.element is None:
            return  self # not yet configured.
        if on_click is not None:
            do(self.element.on("click", on_click), to_depth=self.on_click_depth)
            do(self.element.prop("disabled", False))
            do(self.element.css("opacity", 1.0))
        else:
            do(self.element.off("click"))
            do(self.element.prop("disabled", True))
            do(self.element.css("opacity", 0.5))
        return self

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
        #( "on_click", on_click)
        tag = "<fieldset/>"
        super().__init__(init_text="", tag=tag, title=title)
        assert len(label_value_pairs) > 0, "please provide labels and values."
        entry0 = label_value_pairs[0]
        if type(entry0) is str:
            # Allow list of strings as mapping to list of (s,s)
            pairs = []
            for s in label_value_pairs:
                assert type(s) is str, "please provide label value pairs or all string options."
                pairs.append((s,s))
            label_value_pairs = pairs
        label_value_pairs = [(label, value) for (label, value) in label_value_pairs]
        self.label_value_pairs = label_value_pairs
        #self.labels = [pair[0] for pair in label_value_pairs]
        self.values = [pair[1] for pair in label_value_pairs]
        #assert selected_value is None or selected_value in self.values, \
        #    "no such value to select: " + repr(selected_value)
        #self.selected_value = selected_value
        self.legend = legend
        self.radio_on_click = on_click
        self.options = options or {}
        self.id2value = None

    def set_on_click(self, on_click):
        self.radio_on_click = on_click

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
        on_click = self.radio_on_click
        #("calling update_values onclick")
        if on_click:
            on_click(value)

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
            if checked:
                value = id2value[identifier]
                selected_values.append(value)
        self.select_values(*selected_values)
        #("calling checkboxes on click")
        on_click = self.radio_on_click
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
        on_click = self.radio_on_click
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
        self.enter_callback = None
    
    def on_enter(self, callback):
        self.enter_callback = callback
        return self

    def on_keypress(self, event):
        keyCode = event["keyCode"]
        if keyCode == 13 and self.enter_callback:
            self.enter_callback(event)

    def configure_jQuery_element(self, element):
        do(element.on("input", self.on_change), to_depth=2)
        do(element.keypress(self.on_keypress), to_depth=1)

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
        delay=0.1,  # async delay in seconds for callback to avoid flooding
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
        self.change_pending = False
        self.change_delay = delay

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
        # only
        if c is not None and not self.change_pending:
            #c(v)
            self.change_pending = True
            schedule_task(self.delayed_callback())

    async def delayed_callback(self):
        "delay the change callback and ignore other change requests that arrive too quickly to prevent jitter"
        # xxxx this method should probably be used for other callbacks too...
        c = self.on_change
        if c is None:
            self.change_pending = False
            return
        self.change_pending = True  # redundant
        try:
            # sleep a little to prevent other changes coming in too quickly
            await asyncio.sleep(self.change_delay)
        finally:
            # allow other changes to arrive while the callback executes
            self.change_pending = False
        # use the current value which may have changed during the sleep
        v = self.value
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

class ChildContainerSuper(jQueryComponent):

    # defaults
    children = ()
    _css = {}
    child_css = {}

    def check_children(self, children):
        checked = []
        for c in children:
            if not isinstance(c, jQueryComponent):
                tc = type(c)
                if tc is list:
                    c = self.listChild(c)
                else:
                    assert tc is str, "child must be jQueryComponent, list, or string: " + repr((tc, c))
                    # automatically convert string to Html or Text
                    cs = c.strip()
                    if cs.startswith("<"):
                        c = Html(cs)
                    else:
                        c = Text(c)
            checked.append(c)
        return checked

    def listChild(self, seq):
        return Stack(seq)

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
        raise NotImplementedError("this must be defined in a subclass.")

    def child_reference(self, child, gizmo):
        if child is None:
            return None
        else:
            return gizmo.jQuery(child.dom_element_reference(gizmo))


class Template(ChildContainerSuper):

    def __init__(self, html_template, title=None, empty_targets=True):
        self.html_template = html_template
        super().__init__(init_text=None, tag=html_template, title=title)
        self.class_child_pairs = []
        self.empty_targets = empty_targets

    def put(self, child_component, at_class):
        assert self.gizmo is None, "Cannot attach after gizmo is started."
        assert at_class in self.html_template, "class string not found in template: " + repr(at_class)
        [component] = self.check_children([child_component])
        self.class_child_pairs.append([at_class, component])
        return self

    def __repr__(self):
        L = [self.__class__.__name__ + "(["]
        indent = "    "
        for (to_id, component) in self.class_child_pairs:
            crepr = repr(component)
            idrepr = repr(to_id)
            rc = idrepr + " << " + crepr
            rc = rc.replace("\n", "\n" + indent)
            L.append( indent + rc + ",")
        L[-1] = L[-1] + "])"
        return "\n".join(L)

    def configure_jQuery_element(self, element):
        gizmo = self.gizmo
        pairs = self.class_child_pairs
        classes = set(p[0] for p in pairs)
        ref_pairs = []
        class_to_ref = {}
        # find all references first
        for (classname, c) in pairs:
            class_ref = element.find("." + classname)
            class_to_ref[classname] = class_ref
        # then attach children later to avoid classname collision in sub-components
        for (classname, c) in pairs:
            class_ref = class_to_ref[classname]
            child_ref = self.child_reference(c, gizmo)
            ref_pairs.append((class_ref, child_ref))
        if self.empty_targets:
            for class_ref in class_to_ref.values():
                do(class_ref.empty())
        for (class_ref, child_ref) in ref_pairs:
            do(child_ref.appendTo(class_ref))
        self.ref_pairs = ref_pairs

    async def validate_classes(self):
        "After gizmo start, find the class names in the template via the DOM."
        for pair in self.ref_pairs:
            class_ref = pair[0]
            ln = await get(class_ref.length)
            assert ln > 0, "Class ref not found: " + repr(class_ref)

class GridStack(ChildContainerSuper):

    '''element_css_defaults = {
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
    }'''

    default_class = "H5Gizmo-stack"

    def __init__(
        self, 
        children, 
        tag="<div/>", 
        css=None, 
        child_css=None,
        title=None,
        css_class=None
        ):
        super().__init__(init_text=None, tag=tag, title=title)
        self.children = self.check_children(children)
        self._css = css or {}
        self.child_css = child_css or {}
        css_class = css_class or self.default_class
        self.addClass(css_class)
        #self.children_name = H5Gizmos.new_identifier("JQuery_container")
        #self.children_reference = None

    def __repr__(self):
        L = [self.__class__.__name__ + "(["]
        indent = "    "
        for c in self.children:
            rc = repr(c)
            rc = rc.replace("\n", "\n" + indent)
            L.append( indent + rc + ",")
        #L.append("])")
        L[-1] = L[-1] + "])"
        return "\n".join(L)

    def listChild(self, seq):
        return GridShelf(seq)

    def attach_children(self, children):
        gizmo = self.gizmo
        assert gizmo is not None, "gizmo must be attached."
        do(self.element.empty())
        children = self.children = self.check_children(children)
        # xxxx maybe use child.element?
        references = [self.child_reference(child, gizmo) for child in children]
        #jq = gizmo.jQuery
        #references = [jq(child.dom_element_reference(gizmo)) for child in children]
        #seq = H5Gizmos.GizmoSequence(references, self.gizmo)  # not needed?
        #name(self.children_name, seq)
        css = self.main_css(children)
        #css.update(self.element_css_defaults)
        css.update(self._css)
        do(self.element.css(css))
        for (index, childref) in enumerate(references):
            child_css = self.element_css(index)
            #child_css.update(self.child_css_defaults)
            child_css.update(self.child_css)
            child_container = gizmo.jQuery("<div/>").css(child_css).appendTo(self.element)
            if childref is not None:
                do(childref.appendTo(child_container))
            else:
                #do(child_container)  # ???? is this needed?
                pass

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
            #"grid-row": str(index + 1),  # 1 based indexing
            #"width": "100%",
            #"width": "100%",
            #"overflow": "auto",
            #"padding": "15px",
        }
        return child_css

class GridShelf(GridStack):
   
    def main_css(self, children):
        col_template = "auto"
        row_template = " ".join(["auto"] * len(children))
        # https://stackoverflow.com/questions/47882924/preventing-double-borders-in-css-grid
        css = {
            "grid-template-columns": col_template,
            "grid-template-rows": row_template,
        }
        return css

    def listChild(self, seq):
        return GridStack(seq)

    def element_css(self, index):
        child_css = {
            "grid-row": "1",
            #"grid-column": str(index + 1),  # 1 based indexing
            #"width": "100%",
            #"width": "100%",
            #"overflow": "auto",
            #"padding": "15px",
        }
        return child_css 


class FlexColumn(GridStack):

    flex_direction = "column"
    default_class = "H5Gizmo-Column"

    def main_css(self, children):
        css = {}
        css["display"] = "flex"
        css["flex-direction"] = self.flex_direction
        return css

    def listChild(self, seq):
        return FlexRow(seq)

    def element_css(self, index):
        css = {}
        return css


class FlexRow(FlexColumn):

    flex_direction = "row"

    def listChild(self, seq):
        return FlexColumn(seq)


class LazyExpander(Template):

    """
    Open/Close container for a single child component.
    Create the component on open.  Discard the component on close.
    Any extra dependencies for the created child must be added elsewhere.
    """

    default_template = """
    <div style="display:flex;" class="lazy-expander-gizmo">
         <div class="TOGGLE">XXX</div>
         <div class="CONTENT">YYY</div>
    </div>
    """.strip()

    def __init__(
        self, 
        preview_maker_or_text,
        child_maker, 
        auto_open=False, 
        more_text="+", 
        less_text="-", 
        title=None, 
        template=None,
        padding="5px",
    ):
        if template is None:
            template = self.default_template
        super().__init__(title=title, html_template=template)
        self.preview_maker = preview_maker_or_text
        if isinstance(preview_maker_or_text, str):
            def maker():
                return Text(preview_maker_or_text)
            self.preview_maker = maker
        self.child_maker = child_maker
        self.more_text = more_text
        self.less_text = less_text
        self.toggle_text = ClickableText(more_text, "open", on_click=self.toggle)
        if padding:
            self.toggle_text.css(padding=padding)
        self.is_open = auto_open
        #self.toggle_text = ClickableText(self.more_text, "open", on_click=self.toggle)
        self.content_area = Html("<div/>")
        self.put(self.toggle_text, 'TOGGLE')
        self.put(self.content_area, "CONTENT")

    def toggle(self, *ignored):
        if self.is_open:
            self.close()
        else:
            self.open()

    def open(self):
        self.is_open = True
        self.display_content()

    def close(self):
        self.is_open = False
        self.display_content()

    def configure_jQuery_element(self, element):
        super().configure_jQuery_element(element)
        self.display_content()

    def display_content(self):
        gizmo = self.gizmo
        if self.is_open:
            txt = self.less_text
            content = self.child_maker()
        else:
            txt = self.more_text
            content = self.preview_maker()
        self.toggle_text.html(txt)
        content_element = self.content_area.get_element(gizmo)
        do(content_element.empty())
        do(content.get_element(gizmo).appendTo(content_element))


SMALL_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00'
    b'\x00%\xdbV\xca\x00\x00\x00\x03PLTE\x00\x00\x00\xa7z=\xda\x00\x00\x00\x01tRNS\x00@\xe6'
    b'\xd8f\x00\x00\x00\nIDAT\x08\xd7c`\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82')


class jQueryImage(jQueryComponent):

    # quick and dirty for now
    version = 0

    def __init__(
        self, 
        filename=None,   # filename of None generates a fresh "don't care" name.
        bytes_content=None, 
        height=None, 
        width=None, 
        mime_type=None, 
        alt="image",
        title=None,
        ):
        if filename is None:
            filename = H5Gizmos.new_identifier("jQueryImage")
        if mime_type is None and bytes_content is None:
            mime_type = "img/png"
            bytes_content = SMALL_PNG_BYTES
        self.filename = filename
        self.alt = alt
        self.tag = '<img src="%s" alt="%s"/>' % (self.versioned_link(), self.alt)
        super().__init__(None, self.tag, title=title)
        self.bytes_content = bytes_content
        self.height = height
        self.width = width
        self.content_type = mime_type

    def change_content(self, bytes_content, mime_type=None):
        self.bytes_content = bytes(bytes_content)
        self.getter.set_content(bytes_content, mime_type)
        do(self.element.attr("src", self.versioned_link()))

    def change_content_url(self, bytes_content, mime_type):
        url = content_url(bytes_content, mime_type)
        do(self.element.attr("src", url))

    def change_array(self, array, url=True, scale=False, epsilon=1e-12):
        from PIL import Image
        m = array.min()
        M = array.max()
        if scale:
            if (M - m) > epsilon:
                A = array.astype(np.float)
                scaled = 255 * (A - m) / (M - m)
                array = scaled.astype(np.uint8)
            else:
                array = np.zeros(A.shape, dtype=np.uint8)
                array[:] = 128  # arbitrary grey.
        else:
            assert m >= 0 and M < 256, "Array not in range 0..255 " + repr((m,M))
            array = array.astype(np.uint8)
        im = Image.fromarray(array)
        f = io.BytesIO()
        im.save(f, format="PNG")
        byt = f.getvalue()
        mime_type = "img/png"
        if url:
            self.change_content_url(byt, mime_type)
        else:
            self.change_content(byt, mime_type)

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

def content_url(bytes_content, mime_type):
    import base64
    prefix = 'data:%s;base64,' % mime_type
    b64 = base64.b64encode(bytes_content)
    url = prefix + b64.decode("utf8")
    return url

class Plotter(jQueryImage):

    """
    Context manager to capture matplotlib output.
    """

    def __init__(self, alt="matplotlib plot"):
        super().__init__(
            filename=None,
            bytes_content=SMALL_PNG_BYTES,  # initial default
            mime_type="image/png",
            alt=alt
        )
        self.png_content = None

    def __enter__(self):
        pass

    def __exit__(self, type, value, traceback):
        # https://stackoverflow.com/questions/47816175/pandas-dataframe-and-seaborn-graph-interaction-with-html-webpage
        import matplotlib.pyplot as plt
        if type is None:
            # no error
            figfile = io.BytesIO()
            plt.savefig(figfile, format='png')
            figfile.seek(0)
            figbytes = figfile.getvalue()
            self.change_content_url(figbytes, mime_type="image/png")
            plt.close()  # don't display the figure anywhere else (?)
            self.png_content = figbytes

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


def Html(tag, init_text=None, title=None, css=None):
    tag = str(tag).strip()
    assert tag.startswith("<"), "The tag should be in a tag form like '<h1>this</h1>': " + repr(tag[:20])
    result = jQueryComponent(tag=tag, init_text=init_text, title=title)
    if css:
        result.css(css)
    return result

def Text(content, title=None, css=None):
    "Simple text, escaped."
    econtent = html.escape(content)
    result = Html("<div>%s</div>"  % str(econtent), title=title)
    if css:
        result.css(**css)
    return result

def ClickableText(content, title=None, on_click=None, color="blue"):
    css = dict(color=color, cursor="pointer")
    # https://stackoverflow.com/questions/20165590/make-a-clickable-link-with-onclick-but-without-href/20165626
    result = Html("<tag/>", content, title=title, css=css)
    if on_click:
        result.set_on_click(on_click)
    return result

Button = jQueryButton
Image = jQueryImage
Input = jQueryInput
LabelledInput = LabelledjQueryInput
Label = jQueryLabel
Stack = FlexColumn
Shelf = FlexRow

# Tests and Demos:

def hello_jquery(message="<h2>Hello world: click me.</h2>", auto_start=False):
    from .H5Gizmos import do
    E = jQueryComponent("initializing jquery component.")
    E.counter = 0

    async def task():
        #("setting message", message)
        do(E.element.html(message))
        #("setting on click", click_callback)
        do(E.element.on("click", click_callback))
        info = E.get_info_div()
        do(info.html("info here."))

    def click_callback(*ignored):
        E.counter += 1
        do(E.element.html("<h1><em>That tickles!</em></h1>"))
        do(E.get_info_div().html("click " + repr(E.counter)))

    E.run(task, auto_start=auto_start)
