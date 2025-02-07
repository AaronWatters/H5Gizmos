
"""
Convert an HTML page to a Gizmo standalone application.
"""

# Usually not suitable for combination with other components.

from . import gz_jQuery
from . import gz_resources

class HTMLPage(gz_jQuery.jQueryComponent):

    def __init__(self, html=None, file_path=None, tag="<div></div>", title="Gizmo", init_text=None):
        assert html is not None or file_path is not None, "HTMLPage requires either html or file_path"
        super().__init__(tag=tag, init_text=init_text, title=title)
        if html is not None:
            self.template = gz_resources.custom_html_page_template(html)
        else:
            self.template = gz_resources.custom_html_file(file_path)