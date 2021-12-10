"""
Composable gizmo factories.
"""

#from . import gizmo_server
from H5Gizmos import do, run, get_gizmo

class Component:

    gizmo = None   # default until gizmo is attached.
    task = None

    def attach_gizmo(self, gizmo):
        self.gizmo = gizmo
        self.add_dependencies(gizmo)

    def run(self, task=None):
        self.task = task
        run(self.run_main)

    def prepare_application(self, gizmo):
        self.attach_gizmo(gizmo)
        self.configure_page(gizmo)

    async def run_main(self, gizmo):
        self.prepare_application(gizmo)
        do(gizmo.window.addEventListener("unload", self.shutdown), to_depth=1)
        self.add_std_icon(gizmo)
        await gizmo.start_in_browser()
        #gizmo._start_report_error_task()
        task = self.task
        if task is not None:
            await task()

    def add_std_icon(self, gizmo):
        # https://www.w3.org/2005/10/howto-favicon
        gizmo._add_content(os_path="../static/icon.png", content_type="image/png")
        gizmo._insert_html('<link rel="icon" type="image/png" href="./icon.png"/>', in_body=False)

    async def iframe(self):
        gizmo = await get_gizmo()
        self.prepare_application(gizmo)
        await gizmo.start_in_iframe()

    async def browse(self):
        gizmo = await get_gizmo()
        self.prepare_application(gizmo)
        await gizmo.start_in_browser()

    def configure_page(self, gizmo):
        self.window = gizmo.window
        self.document = gizmo.document
        body = self.body = gizmo.GIZMO_BODY
        interface = gizmo.H5GIZMO_INTERFACE
        element = self.dom_element_reference(gizmo)
        do(interface._set("Target", element))
        target = self.target = interface.Target
        do(body.append(target))

    def add_dependencies(self, gizmo):
        """
        Add libraries, css files, references, or other resources required by the component to the gizmo.
        """
        gizmo._initial_reference("window")
        gizmo._initial_reference("document")
        gizmo._initial_reference("H5GIZMO_INTERFACE")
        gizmo._initial_reference("H5Gizmos")
        gizmo._initial_reference("GIZMO_BODY", 'document.getElementById("GIZMO_BODY")')

    def dom_element_reference(self, gizmo):
        """
        Get a reference to the DOM element for this component.
        """
        raise NotImplementedError("this method must be implemented in the subclass")
        
    def shutdown(self, *args):
        "Graceful shutdown"
        import sys
        print("shutting down.")
        sys.exit()

class HelloComponent(Component):
    
    def __init__(self, text="Hello world"):
        self.text = text

    def dom_element_reference(self, gizmo):
        return self.text

def test_standalone():
    hello = HelloComponent()
    hello.run()
