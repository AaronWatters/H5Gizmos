"""
Special methods for getting large BLOB data
from a gizmo child process.
"""

from . import gizmo_server
#from . import H5Gizmos
from . import gz_parent_protocol as H5Gizmos
import json
import urllib.parse

class BytesPostBack(gizmo_server.FileGetter):

    """
    Getter to accept a POST request sending binary content.
    """

    def __init__(self, processor=None, response_content_type="text/plain"):
        """
        Process POSTs to this end point with the processor function.

            (text, status) = processor(body, json)

        where body is bytes and json is a dict-like.
        The text is returned as the response to the POST.
        The status should be None or an HTTP status code (like 404 meaning not found.)
        """
        if processor is None:
            processor = self.default_processor
        self.processor = processor
        self.content_type = response_content_type
        self.post_future = None
        self.unhandled_data = None  # for debugging

    def default_processor(self, body, json):
        ln = len(body)
        future = self.post_future
        data = (body, json)
        if future is None or future.done(): # pragma: no cover
            self.unhandled_data = data
            text = "Unexpected POST of length %s" % ln
            status = 404 # not found
        else:
            future.set_result(data)
            text = "Expected POST of length %s" % ln
            status = None  # use the default status.
        return (text, status)

    async def wait_for_post(self, timeout=None, on_timeout=None):
        assert self.processor == self.default_processor, "wait_for_post only works with the default processor."
        future = self.post_future
        if future is None or future.done():
            future = self.post_future = H5Gizmos.make_future(timeout=None, on_timeout=on_timeout)
        await future
        return future.result()

    async def handle_get(self, info, request, interface=gizmo_server.STDInterface): # pragma: no cover
        text = "This end point only accepts POST requests."
        status = 405
        return interface.respond(body=text, content_type="text/plain", status=status)

    async def handle_post(self, info, request, interface=gizmo_server.STDInterface):
        body = await request.read()
        query = request.query
        json_str = query.get("json")
        #print ("json_str", json_str)
        json_ob = {}
        if json_str is not None:
            json_str = urllib.parse.unquote(json_str)
            #print ("json_str", json_str)
            json_ob = json.loads(json_str)
        # xxxx catch exception?
        (text, status) = self.processor(body, json_ob)
        if status is None:
            status = 200
        return interface.respond(body=text, content_type=self.content_type, status=status)

'''commented until a use case is found...
class GetBytesViaPost:

    def __init__(self, from_gizmo, callable_link, h5_link):
        """
        Get bytes from a POST end point.

        The callable_link should link to a child callable returning

            [binary_data, meta_data]

        where meta_data is a mapping.
        
        The h5_link should link to the global H5Gizmos object in the child.
        """
        self.from_gizmo = from_gizmo
        self.callable_link = callable_link
        self.h5_link = h5_link
        self.postback = BytesPostBack(self.processor)
        self.end_point = H5Gizmos.new_identifier("post_endpoint")
        from_gizmo._add_getter(self.end_point, self.postback)
        self.future = None

    async def get_data(self, link_arguments, timeout=None, final=True):
        assert self.future is None, "cannot get_data -- future is waiting."
        def on_timeout():
            self.future = None
        callable_link = self.callable_link
        end_point = self.end_point
        post_call = self.h5_link.post_call
        if timeout is None:
            future = H5Gizmos.make_future()
        else:
            future = H5Gizmos.make_future(timeout=timeout, on_timeout=on_timeout)
        self.future = future
        try:
            H5Gizmos.do(post_call(end_point, callable_link, link_arguments))
            await future
        finally:
            self.future = None
            if final:
                self.finalize()
        data = future.result()
        return data

    def processor(self, body, query):
        "Process the POST body and query."
        future = self.future
        if future is not None:
            if not future.done():
                data = PostBackData(body, query)
                future.set_result(data)
            self.future = None
        else:
            # xxxx ignore posts when no future is waiting?
            pass
        result = "got %s bytes in post body." % (len(body),)
        return result

    def finalize(self):
        self.from_gizmo.remove_getter(self.end_point)
        self.from_gizmo = None

class PostBackData:

    def __init__(self, body, query):
        self.body = body
        self.query = query
'''
