
"""
Use an HTML source tree to make a gizmo page.
"""

from . import gz_jQuery
from . import gz_resources
import os

class PageGizmo(gz_jQuery.jQueryComponent):

    def __init__(self, entry_page_path, folder_prefix="page_files"):
        [folder, filename] = entry_page_path.rsplit("/", 1)
        # check that the file exists as a text file
        assert os.path.isfile(entry_page_path), "no such file: " + repr(entry_page_path)
        assert os.path.isdir(folder), "no such folder: " + repr(folder)
        # read and customize the html source
        html = gz_resources.custom_html_file(entry_page_path)
        #print("html")
        #print(html)
        #print("end html")
        super().__init__(init_text="")
        self.template = html
        for filename in os.listdir(folder):
            filepath = os.path.join(folder, filename)
            if os.path.isdir(filepath):
                self.serve_folder(filename, filepath)
            else:
                self.add_content(filepath)

    def locate(self, selector):
        """
        Locate an element in the page by jQuery selector.
        Return a jQueryComponent for that element.
        """
        result = SelectedElement(selector)
        result.gizmo = self.gizmo
        result.dom_element_reference(self.gizmo)
        return result
    
    def locate_id(self, id):
        """
        Locate an element in the page by id.
        Return a jQueryComponent for that element.
        """
        return self.locate("#" + id)
    

class SelectedElement(gz_jQuery.jQueryComponent):
    """
    A jQueryComponent that is a selection of elements from an existing page.
    """

    def __init__(self, selector):
        self.selector = selector
        self.location = None # set when attached to a gizmo
        super().__init__(init_text="", tag=selector)

    def dom_element_reference(self, gizmo):
        #super().dom_element_reference(gizmo)
        self.element = gizmo.jQuery(self.selector)
        #print("element", self.element)
        return self.element[0]
