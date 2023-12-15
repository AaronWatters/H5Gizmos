
"""
Support functions for launching H5Gizmos from withing Jupyter.
"""

from H5Gizmos import new_identifier

def inject_html_in_jupyter(html_string):
    from IPython.display import HTML, display
    display(HTML(html_string))

suffix_at_js = """
function suffix_at(from_url, suffix, at_strings) {
    // for example
    //  var url = "http://localhost:8888/notebooks/repos/H5Gizmos/doc/Demo.ipynb";
    //  var at_strings = ["notebooks/", "lab/"];
    //  var suffix = "GizmoLink/connect/50732/gizmo/http/MGR_1702413571757_3/index.html";
    //  suffix_at(url, suffix, at_strings)
    //   ==> http://localhost:8888/GizmoLink/connect/50732/gizmo/http/MGR_1702413571757_3/index.html
    at_strings = at_strings || ["notebooks/", "lab/"];
    var prefix = from_url;
    for (var splitter of at_strings) {
        var prefix0 = from_url.split(splitter)[0];
        if (prefix0.length < prefix.length) {
            //console.log("choosing prefix", prefix0, splitter)
            prefix = prefix0;
        }
    }
    if (prefix.length >= from_url.length) {
        throw new Error("no split found: " + from_url);
    }
    //console.log("chose prefix", prefix, prefix.length, from_url.length);
    return prefix + suffix;
};
"""

open_suffix_in_tab_js = suffix_at_js + """
function open_suffix_in_tab(suffix, at_strings) {
    var url = suffix_at(window.location.href, suffix, at_strings);
    window.open(url, "_blank").focus();
};
"""

script_template = """
<script>
(function () {
%s
}) ();
</script>
"""

def anonymous_wrap_js_script(js_text):
    return script_template % js_text

def open_in_tab_html(suffix):
    vars = """
        var suffix = "{suffix}";
    """.format(suffix=suffix);
    call = "open_suffix_in_tab(suffix);"
    code = vars.strip() + open_suffix_in_tab_js + call
    feedback = "<p>New tab: " + repr(suffix) + "</p>"
    return feedback + anonymous_wrap_js_script(code)

link_template = """
var ident = "{ident}";
var suffix = "{suffix}";
var div = document.getElementById(ident);
var url = suffix_at(window.location.href, suffix);
link = document.createElement("a");
link.href = url;
link.target = "_blank";
link.innerHTML = url;
div.appendChild(link);
"""

def show_link(suffix):
    ident = new_identifier("gizmo_href")
    D = dict(ident=ident, suffix=suffix)
    code = link_template.format(**D)
    anchor = '<div id="{ident}">Link:&nbsp;</div>'.format(**D)
    #anchor = '<a href="_blank" target="_blank" id="{ident}">open {suffix}.</a>'.format(**D)
    return anchor + anonymous_wrap_js_script(suffix_at_js + code)

def display_link(suffix):
    show = show_link(suffix)
    inject_html_in_jupyter(show)

# https://blog.addpipe.com/camera-and-microphone-access-in-cross-oirigin-iframes-with-feature-policy/
# https://stackoverflow.com/questions/9162933/make-iframe-height-dynamic-based-on-content-inside-jquery-javascript
# https://stackoverflow.com/questions/22086722/resize-cross-domain-iframe-height

iframe_structure = """

<iframe id="{identifier}"
    title="{title}"
    width="100%"
    height="{min_height}px"
    src='about:blank'
    {allow_list}
> </iframe>

<script>
(function () {{
{suffix_at_js}
{event_listener_js}
    var identifier = "{identifier}";
    var suffix = "{suffix}"
    var margin = {margin};
    var min_height = {min_height};
    window.addEventListener("message", event_listener);
    var this_frame = document.getElementById(identifier);
    var url = suffix_at(window.location.href, suffix);
    this_frame.src = url;
}}) ();
</script>
"""

STD_ALLOW_LIST = 'allow="camera;microphone;display-capture;autoplay"'

event_listener_js = """
function event_listener(e) {
    if ((this_frame) && (this_frame.contentWindow === e.source)) {
        var height = Math.max(min_height, e.data.height + margin)
        var height_px = (height) + "px";
        this_frame.height = height_px;
        this_frame.style.height = height_px;
    }
};
"""

def open_in_iframe_html(suffix, margin=10, min_height=20):
    identifier = new_identifier("gizmo_iframe")
    iframe_html = iframe_structure.format(
        suffix = suffix,
        identifier = identifier,
        title = identifier,
        margin = 10,
        min_height = min_height,
        allow_list = STD_ALLOW_LIST,
        suffix_at_js = suffix_at_js,
        event_listener_js = event_listener_js,
    )
    return iframe_html

def display_iframe(suffix):
    show = open_in_iframe_html(suffix)
    inject_html_in_jupyter(show)

if __name__ == "__main__":
    #print(open_in_tab_html("/test/suffix"))
    #print (show_link("/test/suffix"))
    print (open_in_iframe_html("test/suffix"))
