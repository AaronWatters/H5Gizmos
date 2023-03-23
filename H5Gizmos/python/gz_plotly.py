
from . import gz_jQuery
from .gz_parent_protocol import do, get, schedule_task

class Plot(gz_jQuery.jQueryComponent):

    def __init__(self, data, layout=None, config=None, width=None, height=None, title=None):
        super().__init__(title=title)
        data = data or {}
        config = config or {}
        self.resize(width, height)
        self.plotly_data = data
        self.plotly_layout = layout
        self.plotly_config = config

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        self.add_plotly_dependency(gizmo)
        gizmo._initial_reference("Plotly")

    def add_plotly_dependency(self, gizmo):
        gizmo._relative_js("GIZMO_STATIC/plotly.1.58.5/plotly-latest.js")

    def dom_element_reference(self, gizmo):
        result = super().dom_element_reference(gizmo)
        assert self.element is not None
        do(self.element.empty())
        do(gizmo.Plotly.newPlot(
            self.element[0], 
            self.plotly_data, 
            self.plotly_layout, 
            self.plotly_config))
        return result