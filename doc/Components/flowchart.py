
"""
A flow chart visualizer.
Based on an example contributed by https://github.com/psychemedia.
"""

from H5Gizmos import jQueryComponent, do, serve
import asyncio

class FlowChart(jQueryComponent):

    def __init__(self, flowchart_description, width="500", height="300"):
        super().__init__(init_text="flowchart should appear here.")
        self.description = flowchart_description
        self.width = width
        self.height = height

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        # Load the libraries for the flowchart implementation.
        self.remote_js("https://cdnjs.cloudflare.com/ajax/libs/raphael/2.3.0/raphael.min.js")
        self.remote_js("https://flowchart.js.org/flowchart-latest.js")
        # Connect the 'flowchart' global javascript object to 'gizmo.flowchart'
        self.initial_reference("flowchart")

    def configure_jQuery_element(self, element):
        super().configure_jQuery_element(element)
        self.resize(self.width, self.height)
        # Parse the description.
        self.chart = self.cache("chart", self.gizmo.flowchart.parse(self.description))

    def draw(self, *ignored):
        # Draw into the DOM object contained in the jQuery element: self.element[0]
        # Clear out temporary placeholder text.
        do(self.element.empty())
        do(self.chart.drawSVG(self.element[0]))

# === Example script usage below

example_description = """
st=>start: Start|past:>http://www.google.com[blank]
e=>end: End|future:>http://www.google.com
op1=>operation: My Operation|past
op2=>operation: Stuff|current
sub1=>subroutine: My Subroutine|invalid
cond=>condition: Yes
or No?|approved:>http://www.google.com
c2=>condition: Good idea|rejected
io=>inputoutput: catch something...|future

st->op1(right)->cond
cond(yes, right)->c2
cond(no)->sub1(left)->op1
c2(yes)->io->e
c2(no)->op2->e
"""

async def example_task():
    chart = FlowChart(example_description)
    # Hack around a library defect -- flowchart.js seems to need a delay before drawing the chart.
    await chart.show()
    # wait a little bit...
    await asyncio.sleep(0.2)
    chart.draw()

if __name__ == "__main__":
    serve(example_task())
