"""
Miscellaneous helpers for interacting with H5Gizmos.
"""

from .. import hex_to_bytearray
import numpy as np

def get_snapshot_array(pixel_info, invert=False):
    """
    Convert pixel data from an HTML canvas to an appropriate numpy array.
    Data coming from a 2d canvas is right side up -- data coming from WebGL must be inverted.
    """
    data_bytes = hex_to_bytearray(pixel_info["data"])
    width = pixel_info["width"]
    height = pixel_info["height"]
    bytes_per_pixel = 4
    array1d = np.array(data_bytes, dtype=np.ubyte)
    image_array = array1d.reshape((height, width, bytes_per_pixel))
    if invert:
        # invert the rows.
        image_array = image_array[::-1]
    return image_array
