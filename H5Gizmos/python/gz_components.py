"""
Composable gizmo factories.
"""

#from . import gizmo_server
from H5Gizmos import do, run, get_gizmo

class Component:

    gizmo = None   # default until gizmo is attached.

    def attach_gizmo(self, gizmo):
        self.gizmo = gizmo
        self.add_dependencies(gizmo)

    def run(self):
        run(self.run_main)

    def prepare_application(self, gizmo):
        self.attach_gizmo(gizmo)
        self.configure_page(gizmo)

    async def run_main(self, gizmo):
        self.prepare_application(gizmo)
        await gizmo.start_in_browser()

    async def iframe(self):
        gizmo = await get_gizmo()
        self.prepare_application(gizmo)
        await gizmo.start_in_iframe()

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

class HelloComponent(Component):
    
    def __init__(self, text="Hello world"):
        self.text = text

    def dom_element_reference(self, gizmo):
        return self.text

def test_standalone():
    hello = HelloComponent()
    hello.run()
