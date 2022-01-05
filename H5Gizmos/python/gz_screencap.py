"""
Gizmo implementations for extracting images and animations from the screen.
"""

from ..python import gz_jQuery
from .. import do, get
from .gz_tools import get_snapshot_array
import numpy as np
from imageio import imsave

from H5Gizmos.python import gz_tools

class ScreenCapCanvas(gz_jQuery.jQueryComponent):

    def __init__(self, size_callback=None, snap_callback=None):
        super().__init__("Screen capture, not yet attached.")
        self.size_callback = size_callback
        self.snap_callback = snap_callback

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        gizmo._js_file("../js/screen_capture_canvas.js")

    def dom_element_reference(self, gizmo):
        result = super().dom_element_reference(gizmo)
        # initialize the screen capture
        print("initializing size callback", self.size_callback)
        do(gizmo.H5Gizmos.screen_capture(self.element, self.size_callback, self.snap_callback))
        return result

    def set_rectangle(self, x1, y1, x2, y2):
        do(self.element.screen_capture.set_rectangle(x1, y1, x2, y2))

    async def get_snapshot_array(self):
        pixel_info = await get(C.element.screen_capture.snapshot(), to_depth=3)
        return get_snapshot_array(pixel_info)

class ScreenSnapShotAssembly(gz_jQuery.Stack):

    width = height = None

    def __init__(self, filename="snapshot.png"):
        self.capture = ScreenCapCanvas(self.size_callback, self.snap_callback)
        self.x_slider = gz_jQuery.RangeSlider(-10, 100, step=1.0, on_change=self.on_change)
        self.y_slider = gz_jQuery.RangeSlider(-10, 100, step=1.0, orientation="vertical", on_change=self.on_change)
        self.snap_button = gz_jQuery.Button("Snap!", on_click=self.snap_click)
        title = gz_jQuery.Text("filename:")
        self.info_text = gz_jQuery.Text("Select a window to snapshot.")
        self.file_input = gz_jQuery.Input(filename, size=100)
        top = gz_jQuery.Shelf(
            [self.capture, self.y_slider],
            css={"grid-template-rows": "auto min-content"},
            )
        middle = gz_jQuery.Shelf(
            [self.x_slider, self.snap_button],
            css={"grid-template-rows": "auto min-content"},
            )
        bottom = gz_jQuery.Shelf(
            [title, self.file_input],
            css={"grid-template-rows": "min-content auto"},
            child_css={"width": "min-content"},
            )
        children = [
            top,
            middle,
            bottom,
            self.info_text,
        ]
        super().__init__(children)

    def info(self, text):
        self.info_text.html(text)

    def snap_callback(self, pixel_info):
        image_array = get_snapshot_array(pixel_info)
        filename = self.file_input.value
        self.info("Saving %s to %s." % (image_array.shape, repr(filename)))
        imsave(filename, image_array)

    def size_callback(self, width, height):
        self.width = width
        self.height = height
        SH = self.x_slider
        SV = self.y_slider
        SH.resize(width=width)
        SH.set_range(0, width)
        SH.set_values(0, width)
        SV.resize(height=height)
        SV.set_range(0, height)
        SV.set_values(0, height)
        self.info("Adjust sliders for snapshot: " + repr((width, height)))

    def on_change(self, *ignored):
        SH = self.x_slider
        SV = self.y_slider
        C = self.capture
        x1 = SH.low_value
        x2 = SH.high_value
        y1 = SV.maximum - SV.high_value
        y2 = SV.maximum - SV.low_value
        self.info("Adjusting window: " + repr((x1, y1, x2, y2)))
        do(C.element.screen_capture.set_rectangle(x1, y1, x2, y2))

    def snap_click(self, *ignored):
        C = self.capture
        self.info("Taking snapshot.")
        do(C.element.screen_capture.snapshot())
