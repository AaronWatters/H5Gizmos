"""
HTML/HTTP Resource access, such as javascript scripts and CSS files.
"""

from . import gizmo_server
import os

my_dir = os.path.dirname(__file__)

def get_file_path(filename, local=True, relative_to_module=None, my_dir=my_dir):
    """
    Look for an existing path matching filename.
    Try to resolve relative to the module location if the path cannot by found
    using "normal" resolution.
    """
    # override my_dir if module is provided
    if relative_to_module is not None:
        my_dir = os.path.dirname(relative_to_module.__file__)
        #print("reset my_dir for", relative_to_module, my_dir)
    user_path = result = filename
    if local:
        user_path = os.path.expanduser(filename)
        result = os.path.abspath(user_path)
        if os.path.exists(result):
            return result  # The file was found normally
    # otherwise look relative to the module.
    result = os.path.join(my_dir, filename)
    result = os.path.abspath(result)
    #print ("exists test", result, my_dir)
    assert os.path.exists(result), "no such file " + repr((filename, result, user_path))
    return result


STD_HTML_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
    <meta charset="UTF-8">
{HEAD}
    </head>

    <body id="GIZMO_BODY" class="gizmobody">
{BODY}
    </body>
</html>
"""

HEAD_FRAGMENT_BEFORE = "</head>"
HEAD_FRAGMENT_AFTER = """
{HEAD}
    </head>
"""

BODY_FRAGMENT_BEFORE = "</body>"
BODY_FRAGMENT_AFTER = """
{BODY}
        <div id="GIZMO_BODY"></div>
    </body>
"""

def custom_html_page_template(from_html):
    """
    Create a custom HTML template by replacing strings.
    """
    head_pos = from_html.find(HEAD_FRAGMENT_BEFORE)
    body_pos = from_html.find(BODY_FRAGMENT_BEFORE)
    assert head_pos >= 0, "HEAD fragment not found"
    assert body_pos >= 0, "BODY fragment not found"
    # quote any curly braces
    from_html = from_html.replace("{", "{{").replace("}", "}}")
    html = from_html.replace(HEAD_FRAGMENT_BEFORE, HEAD_FRAGMENT_AFTER)
    html = html.replace(BODY_FRAGMENT_BEFORE, BODY_FRAGMENT_AFTER)
    return html

def custom_html_file(file_path):
    """
    Create a custom HTML template by replacing strings.
    """
    with open(file_path, "r") as f:
        html = f.read()
    return custom_html_page_template(html)

class DelegatePOSTtoGETMixin:

    async def handle_post(self, info, request, interface=None):
        interface = interface or gizmo_server.STDInterface
        return await self.handle_get(info, request, interface=interface)


class HTMLPage(DelegatePOSTtoGETMixin):

    def __init__(
        self, 
        #ws_url, 
        title="Gizmo", 
        log_messages=False,
        embed_gizmo=True, 
        template=None, 
        message_delay=1000, # milliseconds
        identifier=None
        ):
        self.identifier = identifier or title
        self.message_delay = message_delay
        self.log_messages = log_messages
        #self.ws_url = ws_url
        if template is None:
            template = STD_HTML_PAGE_TEMPLATE
        self.embed_gizmo = embed_gizmo
        self.template = template
        self.head_resources = []
        self.body_resources = []
        # set this once the HTML page has been sent
        self.materialized = False
        if title is not None:
            self.add_head_resource(PageTitle(title))
        if embed_gizmo:
            self.ref_id_and_js_expression = []

    def link_reference(self, identity, js_expression):
        assert self.embed_gizmo, "Embed gizmo must be enabled for standard link references."
        self.ref_id_and_js_expression.append([identity, js_expression])

    async def handle_get(self, info, request, interface=None):
        interface = interface or gizmo_server.STDInterface
        bytes = self.as_string().encode("utf-8")
        self.materialized = True
        return interface.respond(body=bytes, content_type="text/html")

    def as_string(self):
        template = self.template
        head_string = self.resource_strings(self.head_resources)
        body_string = self.resource_strings(self.body_resources)
        if self.embed_gizmo:
            #std_init = standard_embedded_initialization_code(self.ref_id_and_js_expression)
            std_init = self.standard_embedded_initialization_code()
            embed_init = EmbeddedScript(std_init)
            body_string = "%s\n%s" % (body_string, embed_init.html_embedding())
        result = template.format(HEAD=head_string, BODY=body_string)
        return result

    def add_head_resource(self, resource):
        self.head_resources.append(resource)

    def add_body_resource(self, resource):
        self.body_resources.append(resource)

    def resource_strings(self, resource_list):
        embeddings = [resource.html_embedding() for resource in resource_list]
        embed_list = [x for x in embeddings if x is not None]
        return "\n".join(embed_list)

    def remote_js(self, url, in_body=False, init=None):
        if init is None:
            init = RemoteJavascript
        r = init(url)
        self.add_resource(r, in_body=in_body)

    def remote_css(self, url):
        return self.remote_js(url, in_body=False, init=RemoteCSS)

    def embedded_css(self, text):
        return self.remote_js(text, in_body=False, init=EmbeddedStyle)

    def embedded_script(self, script_text, in_body=True):
        return self.remote_js(script_text, in_body=in_body, init=EmbeddedScript)

    def insert_html(self, text, in_body=True):
        return self.remote_js(text, in_body=in_body, init=InsertHTML)

    def add_resource(self, resource, in_body=True):
        if in_body:
            self.add_body_resource(resource)
        else:
            self.add_head_resource(resource)

    def misc_operations(self):
        "Miscellaneous initialization after references have been created."
        return MISC_OPERATIONS_TEMPLATE.format(
            delay=self.message_delay,
            identifier=self.identifier,
            )

    def standard_embedded_initialization_code(self):
        ref_id_and_js_expression = self.ref_id_and_js_expression
        #L = [PIPELINE_WEBSOCKET_TEMPLATE.format(ws_url=repr(self.ws_url))]
        L = []
        if (self.log_messages):
            L.append("\n\t\t" + "tr.log_messages = true;\n")
        for [identity, expression] in ref_id_and_js_expression:
            id_repr = repr(identity)
            set_code = SET_REFERENCE_TEMPLATE.format(id_string=id_repr, js_expression=expression)
            L.append(set_code)
        L.append(self.misc_operations())
        all_set_code = "".join(L).strip()
        result = STD_INIT_TEMPLATE.replace("[SET_REFERENCES_HERE]", all_set_code)
        return result
        
MISC_OPERATIONS_TEMPLATE = """
        H5Gizmos.periodically_send_height_to_parent("{identifier}", {delay});
        tr.send_keepalive_periodically();
"""

STD_INIT_TEMPLATE = """
// This is the container for the web connection and related objects.
var H5GIZMO_INTERFACE;

(function () {
    function initialize_gizmo() {
        // Initialize the H5GIZMO_INTERFACE using window as default this
        var tr = new H5Gizmos.Translator(window);
        H5GIZMO_INTERFACE = tr;
        
        tr.pipeline_websocket(tr.get_ws_url(window.location));

        [SET_REFERENCES_HERE]
        console.log("gizmo interface initialized");
    };
    // https://stackoverflow.com/questions/33785313/javascript-loading-multiple-functions-onload
    window.addEventListener("load", initialize_gizmo, true);
})();
"""

SET_REFERENCE_TEMPLATE = """
        tr.set_reference({id_string}, {js_expression});
"""

PIPELINE_WEBSOCKET_TEMPLATE = """
        tr.pipeline_websocket({ws_url})
"""

class Resource:

    "Superclass for resources."

    def html_embedding(self):
        return None

    #def configure_in_gizmo_manager(self):  # xxxx not used ???
    #    "Configure the GizmoManager to serve this resource if needed."
    #    return None

class PageTitle(Resource):

    def __init__(self, text):
        self.text = text

    def html_embedding(self):
        return "<title>%s</title>" % self.text

class RemoteJavascript(Resource):

    def __init__(self, url):
        self.url = url

    def html_embedding(self):
        return '<script src="%s"></script>' % (self.url,)

class RemoteCSS(RemoteJavascript):

    def html_embedding(self):
        return '<link rel="stylesheet" href="%s"/>' % (self.url,)


HTML_EMBED_SCRIPT_TEMPLATE = """
<script>
{script_text}
</script>
"""

class EmbeddedScript(Resource):

    def __init__(self, script_text):
        self.script_text = script_text

    def html_embedding(self):
        return HTML_EMBED_SCRIPT_TEMPLATE.format(script_text=self.script_text)


STYLE_EMBED_TEMPLATE = """
<style type="text/css">
{style_text}
</style>
"""

class EmbeddedStyle(Resource):

    def __init__(self, style_text):
        self.style_text = style_text

    def html_embedding(self):
        return STYLE_EMBED_TEMPLATE.format(style_text=self.style_text)


class InsertHTML(Resource):

    def __init__(self, text):
        self.text = text

    def html_embedding(self):
        return self.text

