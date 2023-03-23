"""
Gizmo implementations for extracting images and animations from the screen.

XXXX -- this is experimental and only works in some browsers under some security settings.
"""

from ..python import gz_jQuery
from .. import do, get, schedule_task
from .gz_tools import get_snapshot_array, get_snapshot_arrays
from .gz_get_blob import BytesPostBack
#from . import H5Gizmos
from . import gz_parent_protocol as H5Gizmos
import numpy as np
from imageio import imsave, mimsave
#import pyperclip  -- problematic install!
import os
import html
import asyncio
import math
import time
#from . import H5Gizmos
from H5Gizmos.python import gz_tools

from H5Gizmos.python import gz_get_blob

class ScreenCapCanvas(gz_jQuery.jQueryComponent):

    def __init__(self, size_callback=None, snap_callback=None, defer_media=True):
        super().__init__("Screen capture, not yet attached.")
        self.size_callback = size_callback
        self.snap_callback = snap_callback
        self.defer_media = defer_media

    def add_dependencies(self, gizmo):
        super().add_dependencies(gizmo)
        gizmo._js_file("../js/screen_capture_canvas.js")

    def dom_element_reference(self, gizmo):
        result = super().dom_element_reference(gizmo)
        # initialize the screen capture
        #print("initializing size callback", self.size_callback)
        do(gizmo.H5Gizmos.screen_capture(self.element, self.size_callback, self.snap_callback, self.defer_media))
        return result

    def set_rectangle(self, x1, y1, x2, y2):
        do(self.element.screen_capture.set_rectangle(x1, y1, x2, y2))

    #async def get_snapshot_array(self):
    #    pixel_info = await get(C.element.screen_capture.snapshot(), to_depth=3)
    #    return get_snapshot_array(pixel_info)

class ScreenAssemblyMixin:

    "Common operations for screen shot and animation."

    width = height = None

    def info(self, text):
        self.info_text.html(text)

    def prepare_path(self):
        #image_array = get_snapshot_array(pixel_info)
        filename = self.file_input.value
        path = os.path.expanduser(filename)
        path = os.path.abspath(path)
        #self.info("Saving %s to %s." % (image_array.shape, repr(path)))
        #imsave(path, image_array)
        self.filename = filename
        self.path = path
        self.copy_path_button.set_on_click(self.copy_path)
        self.copy_tag_button.set_on_click(self.copy_tag)
        return path

    def copy_tag(self, *ignored):
        "copy tag button callback."
        try:
            import pyperclip
        except Exception:
            print("Please install pyperclip manually to enable this feture")
            raise
        filename = self.filename
        tag = '<img src="%s"/>' % filename
        pyperclip.copy(tag)
        qtag = html.escape(tag)
        self.info(repr(qtag) + " copied to clipboard.")

    def copy_path(self, *ignored):
        "copy path button callback."
        try:
            import pyperclip
        except Exception:
            print("Please install pyperclip manually to enable this feture")
            raise
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
        self.enable_capture()

    def enable_capture(self):
        raise NotImplementedError("implement in subclass.")

    def check_labelled_input(self, input, low_value, high_value, default):
        assert default >= low_value and default <= high_value, "bad range " +repr((low_value, high_value, default))
        value_str = input.value
        label = repr(input.label_text)
        bounds_complaint = "%s should be between %s and %s -- please try again" % (label, low_value, high_value)
        try:
            value = float(value_str)
        except ValueError:
            self.info(bounds_complaint)
            input.set_value(str(default))
            return None
        if value < low_value or value > high_value:
            self.info(bounds_complaint)
            input.set_value(str(default))
            return None
        return value

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

class jQuerySnapSuperClass(gz_jQuery.Stack, ScreenAssemblyMixin):

    aborted = False

    def configure_jQuery_element(self, element):
        result = super().configure_jQuery_element(element)
        self.add("""
        This screen capture gizmo is only known to work using recent version of the Chrome browser.
        You may need to change the security settings to permit screen access.
        """)
        self.attach_button.set_on_click(self.get_media_method_reference()) # xxxx
        self.postback = gz_get_blob.BytesPostBack()
        gizmo = self.gizmo
        self.end_point = H5Gizmos.new_identifier("snapshot_endpoint")
        gizmo._add_getter(self.end_point, self.postback)
        self.stopped = False
        dialog_options = dict(
            autoOpen=False,
            buttons={"Stop": self.stop_click, "Abort": self.abort_click},
            resizable=False,
            modal=True,
        )
        self.status_dialog = self.add_dialog("Status dialog.", dialog_options, "Status")

    def status(self, message):
        d = self.status_dialog
        d.open_dialog()
        d.html(message)

    def abort_click(self, *ignored):
        self.aborted = True
        self.stop_click()

    def stop_click(self, *ignored):
        self.stopped = True
        self.status_dialog.close_dialog()

    def get_media(self, *ignored):
        C = self.capture
        do(C.element.screen_capture.get_media())

    def get_media_method_reference(self):
        # get media must be called directly from gesture callback in Safari...
        C = self.capture
        return C.element.screen_capture._get_media


class ScreenSnapShotAssembly(jQuerySnapSuperClass):

    "Gizmo interface for capturing a PNG from the screen."

    def __init__(self, filename="snapshot.png", timeout=60):
        self.timeout = timeout
        defer_media = True
        self.capture = ScreenCapCanvas(self.size_callback, snap_callback=None, defer_media=defer_media)
        self.x_slider = gz_jQuery.RangeSlider(-10, 100, step=1.0, on_change=self.on_change)
        self.y_slider = gz_jQuery.RangeSlider(-10, 100, step=1.0, orientation="vertical", on_change=self.on_change)
        #self.snap_button = gz_jQuery.Button("Snap!", on_click=self.snap_click)
        self.snap_button = gz_jQuery.Button("Snap!")
        # get media must be called from gesture callback directly (not via Python)
        self.attach_button = gz_jQuery.Button("Attach media")
        # self.attach_button = gz_jQuery.Button("Attach media", on_click=self.get_media)
        self.copy_tag_button = gz_jQuery.Button("Copy tag")
        self.copy_path_button = gz_jQuery.Button("Copy path")
        #title = gz_jQuery.Text("filename:")
        self.info_text = gz_jQuery.Text("Select a window to snapshot.")
        self.file_input = gz_jQuery.Input(filename, size=100)
        label = gz_jQuery.jQueryLabel("file path", self.file_input)
        self.delay_input = gz_jQuery.LabelledInput("delay seconds", "0", size=4)
        #delay_label = gz_jQuery.jQueryLabel("delay seconds", self.delay_input)
        top = gz_jQuery.Shelf(
            [self.capture, self.y_slider],
            css={"grid-template-rows": "auto min-content"},
            )
        middle = gz_jQuery.Shelf(
            [self.x_slider, self.snap_button, self.attach_button],
            css={"grid-template-rows": "auto min-content"},
            )
        bottom = gz_jQuery.Shelf(
            #[title, self.file_input, self.copy_tag_button, self.copy_path_button],
            [label, self.copy_tag_button, self.copy_path_button, self.delay_input.label_container],
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

    def snap_callback(self, pixel_info):
        path = self.prepare_path()
        image_array = get_snapshot_array(pixel_info)
        #filename = self.file_input.value
        #path = os.path.expanduser(filename)
        #path = os.path.abspath(path)
        self.status("Saving %s to %s." % (image_array.shape, repr(path)))
        imsave(path, image_array)
        #self.status_dialog.close_dialog()
        self.info("Saved %s to %s." % (image_array.shape, repr(path)))
        print("Saved", repr(path))
        #self.filename = filename
        #self.path = path
        #self.copy_path_button.set_on_click(self.copy_path)
        #self.copy_tag_button.set_on_click(self.copy_tag)

    def enable_capture(self):
        self.snap_button.set_on_click(self.snap_click)

    currently_snapping = False

    def snap_click(self, *ignored):
        if self.currently_snapping:
            return # ignore dup
        delay = self.check_labelled_input(self.delay_input, 0, 100, 0)
        if delay is None:
            return
        #if delay <= 1:
        #    self.do_snapshot()
        #else:
        #    schedule_task(self.delay_snapshot(delay))
        self.stopped = False
        self.aborted = False
        schedule_task(self.delay_snapshot(delay))

    async def delay_snapshot(self, delay):
        try:
            counter = math.ceil(delay)
            while counter > 0:
                if self.stopped:
                    if self.aborted: 
                        return
                    break
                self.status("Delay Countdown: " + str(counter))
                counter -= 1
                await asyncio.sleep(1)
            await self.do_snapshot()
            self.status("Snapshot saved.")
            await asyncio.sleep(1)
            self.status_dialog.close_dialog()
        finally:
            self.currently_snapping = False

    async def do_snapshot(self):
        C = self.capture
        self.status("Taking snapshot.")
        do(C.element.screen_capture.post_snapshot(self.end_point))
        data = await self.postback.wait_for_post(timeout=self.timeout, on_timeout=self.on_timeout)
        (body, query) = data
        info = query.copy()
        info["data"] = body
        self.snap_callback(info)

    def on_timeout(self, *ignored):
        self.info("Snapshot timed out.")
        self.status_dialog.close_dialog()

class ScreenAnimationAssembly(jQuerySnapSuperClass):

    "Gizmo interface for capturing an animated GIF from the screen."

    def __init__(self, filename="screen_animation.gif", timeout=10):
        self.timeout = timeout
        defer_media = True
        self.capture = ScreenCapCanvas(self.size_callback, snap_callback=None, defer_media=defer_media)
        self.x_slider = gz_jQuery.RangeSlider(-10, 100, step=1.0, on_change=self.on_change)
        self.y_slider = gz_jQuery.RangeSlider(-10, 100, step=1.0, orientation="vertical", on_change=self.on_change)
        self.record_button = gz_jQuery.Button("Record")
        self.copy_tag_button = gz_jQuery.Button("Copy tag")
        self.attach_button = gz_jQuery.Button("Attach media")  # on_click is automatically attached
        #self.stop_button = gz_jQuery.Button("Stop")
        self.copy_path_button = gz_jQuery.Button("Copy path")
        #title = gz_jQuery.Text("filename:")
        self.info_text = gz_jQuery.Text("Select a window to snapshot.")
        self.file_input = gz_jQuery.LabelledInput("file path", filename, size=100)
        #label = gz_jQuery.jQueryLabel("file path", self.file_input)
        self.delay_input = gz_jQuery.LabelledInput("delay seconds", "0", size=4)
        #delay_label = gz_jQuery.jQueryLabel("delay seconds", self.delay_input)
        self.fps_input = gz_jQuery.LabelledInput("FPS", "5", size=4)
        self.limit_input = gz_jQuery.LabelledInput("limit seconds", "60", size=4)
        top = gz_jQuery.Shelf(
            [self.capture, self.y_slider],
            css={"grid-template-rows": "auto min-content"},
            )
        middle = gz_jQuery.Shelf(
            [self.x_slider, self.record_button, self.attach_button],
            css={"grid-template-rows": "auto min-content min-content"},
            )
        bottom = gz_jQuery.Shelf(
            #[title, self.file_input, self.copy_tag_button, self.copy_path_button],
            [
                self.file_input.label_container,
                self.copy_tag_button,
                self.copy_path_button,
                self.delay_input.label_container,
                self.limit_input.label_container,
                self.fps_input.label_container,
            ],
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
        self.stopped = True
        self.aborted = False
        self.image_arrays = None
        super().__init__(children)

    def enable_capture(self):
        self.record_button.set_on_click(self.record_click)

    currently_recording = False

    def record_click(self, *ignored):
        #assert not self.currently_recording, "Rejecting duplicate record_click"
        if self.currently_recording:
            return # ignore duplicate click
        self.currently_recording = True
        delay = self.check_labelled_input(self.delay_input, 0, 100, 0)
        limit = self.check_labelled_input(self.limit_input, 1, 999, 100)
        fps = self.check_labelled_input(self.fps_input, 1, 60, 30)
        if None in [delay, limit, fps]:
            return  # bad parameter -- message in info.
        self.info("(delay, limit, fps): " + repr((delay, limit, fps)))
        #return # debugging...
        time_interval_seconds = 1.0 / fps
        schedule_task(self.get_frames(time_interval_seconds, delay, limit))

    async def get_frames(self, time_interval_seconds, delay, limit):
        try:
            assert self.currently_recording
            self.stopped = False
            self.aborted = False
            C = self.capture
            do(C.element.screen_capture.reset_snapshot_list())
            try:
                self.record_button.set_on_click(None)
                self.image_arrays = []
                counter = math.ceil(delay)
                #self.stop_button.set_on_click(self.stop_click)
                while counter > 0:
                    self.status("Delay Countdown: " + str(counter))
                    counter -= 1
                    await asyncio.sleep(1)
                    if self.stopped:
                        if self.aborted:
                            return
                        break
                elapsed = 0
                started = time.time()
                count = 0
                while not self.stopped and (elapsed < limit):
                    self.status("Captured %s. Elapsed %s." % (count, elapsed))
                    do(C.element.screen_capture.snapshot())
                    await asyncio.sleep(time_interval_seconds)
                    elapsed = time.time() - started
                    count += 1
                if self.stopped:
                    if self.aborted:
                        return
            finally:
                #self.stop_click()
                self.enable_capture()
            # wait for a final capture -- force websocket to sync (?)
            self.status("Final snapshot.")
            await get(C.element.screen_capture.snapshot(True), timeout=None)
            self.status("Preparing data transfer.")
            error_message = await get(C.element.screen_capture.prepare_all_snapshots())
            if error_message:
                self.info(error_message)
                self.status("Data transfer error: " + repr(error_message))
                return
            path = self.prepare_path()
            self.status("Posting data to parent process.")
            do(C.element.screen_capture.post_all_snapshots(self.end_point))
            data = await self.postback.wait_for_post(timeout=self.timeout, on_timeout=self.on_timeout)
            self.status("Got postback from parent process.")
            (body, query) = data
            info = query.copy()
            info["data"] = body
            self.status("Preparing snapshot arrays.")
            self.image_arrays = get_snapshot_arrays(info)
            self.info("Storing %s to %s. Elapsed %s." % (len(self.image_arrays), repr(path), (elapsed, limit, count)))
            #return # DEBUGGING
            self.status("Storing arrays to " + repr(path))
            mimsave(path, self.image_arrays, format='GIF', duration=time_interval_seconds)
            self.info("Saved %s to %s. Elapsed %s." % (len(self.image_arrays), repr(path), elapsed))
            self.status("Store complete: " + repr(path))
            print("wrote animated gif", path)
            await asyncio.sleep(1)
            self.status_dialog.close_dialog()
        finally:
            self.currently_recording = False

    #def stop_click(self, *ignored):
    #    self.stopped = True
    #    self.stop_button.set_on_click(None)

    def on_timeout(self, *ignored):
        self.info("Data transfer timed out.")

    """def snap_callback(self, pixel_info):
        image_array = get_snapshot_array(pixel_info)
        self.image_arrays.append(image_array) # not used """
