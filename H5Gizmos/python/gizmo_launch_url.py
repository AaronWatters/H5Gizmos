
from .gizmo_server import FileGetter, STDInterface, get_gizmo
from .H5Gizmos import new_identifier

class LaunchGizmoAndRedirect(FileGetter):

    def __init__(self, component_maker, title="launched gizmo", proxy=False, parent_component=None):
        self.title = title
        self.component_maker = component_maker
        self.proxy = proxy
        self.parent_component = parent_component

    async def handle_get(self, info, request, interface=STDInterface):
        #redirect_url = "https://www.yahoo.com"
        component = self.component_maker()
        gizmo = await get_gizmo(title=self.title)
        component.prepare_application(gizmo)
        nonce = new_identifier("N")
        #redirect_url = gizmo._entry_url(proxy=self.proxy)
        redirect_url = "../%s/%s?nonce=%s" % (gizmo._manager.identifier, gizmo._filename, nonce)  # use relative url
        parent_component = self.parent_component
        if parent_component is not None:
            parent_component.add("created new gizmo at" + repr(redirect_url))
        sbody = 'redirect to: <a href="%s">%s</a>.' % (redirect_url, redirect_url)
        bbody = sbody.encode("utf8")
        response = interface.respond(body=bbody, content_type="text/html", status=301)
        response.headers["location"] = redirect_url
        response.headers["Cache-Control"] = "no-store"
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
    return (relative_url, full_url)
