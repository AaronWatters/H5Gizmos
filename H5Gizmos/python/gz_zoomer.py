"""
Zoomer Gizmo for H5Gizmos.

Zoom and pan an image of an array.
"""


import numpy as np
from . import gz_jQuery

def extract_panel(arr, A, B, C, D, M, N):
    """Resize arr[A:B, C:D] to (M, N) by selecting/repeating values."""
    panel = arr[A:B, C:D]
    h, w = panel.shape[:2]

    if h == 0 or w == 0 or M <= 0 or N <= 0:
        raise ValueError("Source panel and output dimensions must be nonempty")

    # Map output pixel centers to source indices.
    rows = np.minimum(((np.arange(M) + 0.5) * h / M).astype(np.intp), h - 1)
    cols = np.minimum(((np.arange(N) + 0.5) * w / N).astype(np.intp), w - 1)

    return panel[np.ix_(rows, cols)]

class Zoomer(gz_jQuery.jQueryComponent):

    def __init__(self, img_data, width, height, on_click=None, title=None):
        self.img_data = img_data
        self.view_data = None
        self.canvas_width = width
        self.canvas_height = height
        self.title = title
        # callback with signature (row, col, data)
        self._on_click_callback = on_click
        self.set_view_data()
        result = super().__init__(title=title)
        self.call_when_started(self._on_started)
        return result

    def on_click_callback(self, row, col):
        callback = self._on_click_callback
        data = self.img_data[row, col]
        if callback is not None:
            callback(row, col, data)

    def add_dependencies(self, gizmo):
        result = super().add_dependencies(gizmo)
        self.add_zoomer_dependencies(gizmo)
        return result

    def _on_started(self):
        container_proxy = self.proxy()
        window_proxy = self.window_proxy()
        view_data = self.view_data
        view_shape = list(view_data.shape)
        print("view_shape:", view_shape)
        zoomer_proxy = window_proxy.Zoomer.new(
            container_proxy,
            self.update_call_back,
            self.canvas_width,
            self.canvas_height,
            view_shape,
        )
        self.zoomer_proxy = zoomer_proxy
        zoomer_proxy.on_click_callback(self.on_click_callback)

    def update_call_back(self, rowStart, rowStop, colStart, colStop, width, height, requestId):
        panel = extract_panel(self.view_data, rowStart, rowStop, colStart, colStop, height, width)
        self.zoomer_proxy.update(panel.ravel(), width, height, requestId)

    def update_img(self, img_data):
        # don't allow change of shape (for now)
        if img_data.shape != self.img_data.shape:
            raise ValueError("New image must have the same shape as the original")
        self.img_data = img_data
        self.set_view_data(img_data)
        self.zoomer_proxy.reload()

    def set_view_data(self, img=None):
        if img is None:
            img = self.img_data
        self.img_data = img
        shape = img.shape
        # copy uint8 of shape (I,J) or (I,J,3) or (I,J,4)
        if img.dtype == np.uint8:
            if len(shape) == 2:
                self.view_data = img.copy()
            elif len(shape) == 3 and shape[2] in (3, 4):
                self.view_data = img.copy()
            else:
                raise ValueError("Unsupported uint8 image shape")
        else:
            if len(shape) == 2:
                # Convert to uint8 by scaling to 0-255
                m = img.min()
                M = img.max()
                if M > m:
                    self.view_data = ((img - m) * 255 / (M - m)).astype(np.uint8)
                else:
                    # set to gray
                    self.view_data = np.full_like(img, 128, dtype=np.uint8)
            else:
                raise ValueError("Unsupported non-uint8 image shape {}".format(shape))
        return self.view_data

    def add_zoomer_dependencies(self, gizmo):
        gizmo._relative_js("GIZMO_STATIC/zoomer.js")