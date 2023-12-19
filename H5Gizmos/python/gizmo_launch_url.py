
from .gizmo_server import FileGetter, STDInterface, get_gizmo
from H5Gizmos import new_identifier
from .gz_jQuery import Html
from .gz_parent_protocol import schedule_task
import traceback
import html

ERR_TEMPLATE = """
<p>
Exception encountered when creating component to launch:
</p>

<pre>
%s
</pre>
"""

REDIRECT_PAGE = """
<!DOCTYPE html>
<html>
    <head>
    <meta charset="UTF-8">
    <script>
    function open_gizmo() {{
        window.location.href = "{redirect_url}";
    }}
    setTimeout(open_gizmo, {delay_ms});
    </script>
    </head>

    <body id="GIZMO_BODY" class="gizmobody">
    Redirecting: {redirect_url}.
    </body>
</html>
"""

class LaunchGizmoAndRedirect(FileGetter):

    def __init__(self, component_maker, title="launched gizmo", proxy=False, parent_component=None):
        self.title = title
        self.component_maker = component_maker
        self.proxy = proxy
        self.parent_component = parent_component
        self.delay_ms = 50  # hardcoded for now.

    async def handle_get(self, info, request, interface=STDInterface):
        #redirect_url = "https://www.yahoo.com"
        try:
            component = self.component_maker()
        except:
            return self.error_response(interface)
        gizmo = await get_gizmo(title=self.title)
        component.prepare_application(gizmo)
        component.add_std_icon(gizmo)
        #print("schedule round-trip communication test...")
        schedule_task(gizmo._has_started())
        nonce = new_identifier("N")
        #redirect_url = gizmo._entry_url(proxy=self.proxy)
        redirect_url = "../%s/%s?nonce=%s" % (gizmo._manager.identifier, gizmo._filename, nonce)  # use relative url
        parent_component = self.parent_component
        if parent_component is not None:
            parent_component.add("created new gizmo at " + repr(redirect_url))
        #sbody = 'redirect to: <a href="%s">%s</a>.' % (redirect_url, redirect_url)
        sbody = REDIRECT_PAGE.format(redirect_url=redirect_url, delay_ms=self.delay_ms)
        bbody = sbody.encode("utf8")
        response = interface.respond(body=bbody, content_type="text/html", status=200)
        #response = interface.respond(body=bbody, content_type="text/html", status=301)
        #response.headers["location"] = redirect_url
        response.headers["Cache-Control"] = "no-store"
        return response
    
    def error_response(self, interface):
        err_str = traceback.format_exc()
        err_html = html.escape(err_str)
        err_fmt = ERR_TEMPLATE % (err_html,)
        response = interface.respond(body=err_fmt.encode("utf8"), content_type="text/html")
        return response

def add_launcher(to_gizmo, component_maker, filename=None, parent_component=None):
    if filename is None:
        filename = new_identifier("gizmo_launcher")
    launcher = LaunchGizmoAndRedirect(component_maker, parent_component=parent_component)
    mgr = to_gizmo._manager
    mgr.add_http_handler(filename, launcher)
    relative_url = to_gizmo.relative_url(filename)
    #print ("relative_url", repr(relative_url))
    full_url = mgr.local_url(for_gizmo=to_gizmo, method="http", filename=filename)
    #print ("full url", repr(full_url))
    return (relative_url, full_url, filename)

class Launcher:

    def __init__(self, component, component_maker, filename=None):
        self.to_gizmo = component.gizmo
        self.component_maker = component_maker
        (self.relative_url, self.full_url, self.filename) = add_launcher(
            self.to_gizmo, component_maker, filename)
        self.active = True

    def anchor_string(self, text=None, relative=True):
        assert self.active, "Launcher link is not active: " + repr(self.filename)
        url = self.relative_url
        if not relative:
            url = self.full_url
        if text is None:
            text = url
        return '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (url, text)

    def anchor(self, text=None, relative=True):
        link = self.anchor_string(text, relative)
        return Html(link)

    def finalize(self):
        if not self.active:
            return
        self.active = False
        self.to_gizmo.remove_getter(self.filename)
        self.to_gizmo = None
