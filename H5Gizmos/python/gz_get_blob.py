"""
Special methods for getting large BLOB data
from a gizmo child process.
"""

from . import gizmo_server
from . import H5Gizmos
from aiohttp import web

class BytesPostBack(gizmo_server.FileGetter):

    """
    Accept a POST request including binary content.
    """

    def __init__(self, processor, response_content_type="text/plain"):
        """
        Process POSTs to this end point with the processor function.

            text = processor(body, header_query)

        the text is returned as the response to the POST.
        """
        self.processor = processor
        self.content_type = response_content_type

    def handle_get(self, info, request, interface=gizmo_server.STDInterface):
        raise NotImplementedError("Please use POST for this end point.")

    async def handle_post(self, info, request, interface=gizmo_server.STDInterface):
        body = await request.read()
        query = request.query
        text = self.processor(body, query)
    