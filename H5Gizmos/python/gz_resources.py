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
    #print ("exists test", result, my_dir)
    assert os.path.exists(result), "no such file " + repr((filename, result, user_path))
    return result


STD_HTML_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html>
    <head>
{HEAD}
    </head>

    <body>
{BODY}
    </body>
</html>
"""

class DelegatePOSTtoGETMixin:

    def handle_post(self, info, request, interface=None):
        interface = interface or gizmo_server.STDInterface
        return self.handle_get(info, request, interface=interface)


class HTMLPage(DelegatePOSTtoGETMixin):

    def __init__(self, title="Gizmo", embed_gizmo=True, template=None):
        if template is None:
            template = STD_HTML_PAGE_TEMPLATE
        self.template = template
        self.head_resources = []
        self.body_resources = []
        if title is not None:
            self.add_head_resource(PageTitle(title))

    def handle_get(self, info, request, interface=None):
        interface = interface or gizmo_server.STDInterface
        bytes = self.as_string().encode("utf-8")
        return interface.respond(body=bytes, content_type="text/html")

    def as_string(self):
        template = self.template
        head_string = self.resource_strings(self.head_resources)
        body_string = self.resource_strings(self.body_resources)
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

    def embedded_script(self, script_text, in_body=True):
        return self.remote_js(script_text, in_body=in_body, init=EmbeddedScript)

    def insert_html(self, text):
        return self.remote_js(text, in_body=True, init=InsertHTML)

    def add_resource(self, resource, in_body=True):
        if in_body:
            self.add_body_resource(resource)
        else:
            self.add_head_resource(resource)

class Resource:

    "Superclass for resources."

    def html_embedding(self):
        return None

    def configure_in_gizmo_manager(self):
        "Configure the GizmoManager to serve this resource if needed."
        return None

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
        return '<link rel=stylesheet href="%s"/>' % (self.url,)


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

class InsertHTML(Resource):

    def __init__(self, text):
        self.text = text

    def html_embedding(self):
        return self.text

