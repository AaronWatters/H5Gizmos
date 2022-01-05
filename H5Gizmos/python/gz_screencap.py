"""
Gizmo implementations for extracting images and animations from the screen.
"""

from ..python import gz_jQuery
from .. import do, get, schedule_task
from .gz_tools import get_snapshot_array
import numpy as np
from imageio import imsave
import pyperclip
import os
import html
import asyncio

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
        self.copy_tag_button = gz_jQuery.Button("Copy tag")
        self.copy_path_button = gz_jQuery.Button("Copy path")
        #title = gz_jQuery.Text("filename:")
        self.info_text = gz_jQuery.Text("Select a window to snapshot.")
        self.file_input = gz_jQuery.Input(filename, size=100)
        label = gz_jQuery.jQueryLabel("file path", self.file_input)
        self.delay_input = gz_jQuery.Input("0", size=4)
        delay_label = gz_jQuery.jQueryLabel("delay seconds", self.delay_input)
        top = gz_jQuery.Shelf(
            [self.capture, self.y_slider],
            css={"grid-template-rows": "auto min-content"},
            )
        middle = gz_jQuery.Shelf(
            [self.x_slider, self.snap_button],
            css={"grid-template-rows": "auto min-content"},
            )
        bottom = gz_jQuery.Shelf(
            #[title, self.file_input, self.copy_tag_button, self.copy_path_button],
            [label, self.copy_tag_button, self.copy_path_button, delay_label],
            #css={"grid-template-rows": "min-content auto"},
            child_css={"width": "min-content"},
            )
        children = [
            top,
            middle,
            bottom,
            self.info_text,
        ]
        self.filename = None  # no filename until image is saved.
        self.path = None
        super().__init__(children)

    def info(self, text):
        self.info_text.html(text)

    def snap_callback(self, pixel_info):
        image_array = get_snapshot_array(pixel_info)
        filename = self.file_input.value
        path = os.path.expanduser(filename)
        path = os.path.abspath(path)
        self.info("Saving %s to %s." % (image_array.shape, repr(path)))
        imsave(path, image_array)
        self.filename = filename
        self.path = path
        self.copy_path_button.set_on_click(self.copy_path)
        self.copy_tag_button.set_on_click(self.copy_tag)

    def copy_tag(self, *ignored):
        "copy tag button callback."
        filename = self.filename
        tag = '<img src="%s"/>' % filename
        pyperclip.copy(tag)
        qtag = html.escape(tag)
        self.info(repr(qtag) + " copied to clipboard.")

    def copy_path(self, *ignored):
        "copy path button callback."
        path = self.path
        pyperclip.copy(path)
        self.info(repr(path) + " copied to clipboard.")

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
        delay_str = self.delay_input.value
        try:
            delay = float(delay_str)
        except ValueError:
            self.info("INVALID DELAY -- PLEASE TRY AGAIN.")
            self.delay_input.set_value("0")
            return
        if delay <= 1:
            self.do_snapshot()
        else:
            schedule_task(self.delay_snapshot(delay))

    async def delay_snapshot(self, delay):
        import math
        counter = math.ceil(delay)
        while counter > 0:
            self.info("Delay Countdown: " + str(counter))
            counter -= 1
            await asyncio.sleep(1)
        self.do_snapshot()

    def do_snapshot(self):
        C = self.capture
        self.info("Taking snapshot.")
        do(C.element.screen_capture.snapshot())
