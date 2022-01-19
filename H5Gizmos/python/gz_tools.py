"""
Miscellaneous helpers for interacting with H5Gizmos.
"""

from .. import hex_to_bytearray
import numpy as np

def get_snapshot_arrays(pixel_info, invert=False):
    """
    Convert pixel data from an HTML canvas to an appropriate numpy array.
    Data coming from a 2d canvas is right side up -- data coming from WebGL must be inverted.
    """
    data_bytes = pixel_info["data"]
    #print ("pixel_info", list(pixel_info.keys()))
    #print ("got data bytes", len(data_bytes), type(data_bytes), data_bytes[:10])
    ty = type(data_bytes)
    if ty is str:
        data_bytes = hex_to_bytearray(pixel_info["data"])
    elif ty is bytes:
        data_bytes = bytearray(data_bytes)
    width = pixel_info["width"]
    height = pixel_info["height"]
    count = pixel_info.get("count", 1)
    bytes_per_pixel = pixel_info.get("bands", 4)
    array1d = np.array(data_bytes, dtype=np.ubyte)
    image_array = array1d.reshape((count, height, width, bytes_per_pixel))
    if invert:
        # invert the rows.
        image_array = image_array[:, ::-1]
    return image_array

def get_snapshot_array(pixel_info, invert=False):
    arrays = get_snapshot_arrays(pixel_info, invert)
    assert len(arrays) == 1, "too many arrays: " + repr(len(arrays))
    return arrays[0]
