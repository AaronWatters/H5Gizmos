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

async def use_proxy():
    "Harden proxy URL paths in a Jupyter notebook, for example inside Binder."
    from .gz_jQuery import Html
    from .gizmo_server import set_url_prefix, PREFIX_ENV_VAR
    from H5Gizmos import get
    msg = Html("<h4>Hardening GizmoLink proxy access</h4>")
    await msg.iframe(proxy=True)
    # eg:
    # http://localhost:8888/GizmoLink/connect/61735/gizmo/http/MGR_1653507873775_2/index.html
    href = await get(msg.gizmo.window.location.href)
    msg.add("window location: " + href)
    split_href = href.split("/")
    # eg: http://localhost:8888/GizmoLink/
    prefix = "/".join(split_href[:-6]) + "/"
    msg.add("Proxy prefix:")
    msg.add(Html(
        '<textarea rows="4" cols="80">export %s=%s</textarea>' 
        % (PREFIX_ENV_VAR, prefix)))
    set_url_prefix(prefix)

TEST_ENVIRONMENT_VARIABLES = set([
    'BINDER_SERVICE_PORT',
    'BINDER_REQUEST',
    'JUPYTERHUB_USER',
    'JUPYTERHUB_HOST',
])

async def use_proxy_if_remote(test_vars=TEST_ENVIRONMENT_VARIABLES):
    "If the environment seems to be running in binder or jupyter hub, harden the proxy."
    import os
    env_vars = set(os.environ.keys())
    indicators = env_vars & test_vars
    if indicators:
        print("Found remote indicator env vars: ", list(indicators))
        return await use_proxy()
    else:
        print("No remote indicator variables found in environment.")
