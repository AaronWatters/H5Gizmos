"""
A quick and dirty server side file browser gizmo component.
"""

from H5Gizmos import ClickableText, Text, Shelf, Stack, Html, Button, Input
import os

def default_tester(path):
    test_result = False
    message = "Please choose a regular file."
    if os.path.isfile(path):
        test_result = True
        (_, filename) = os.path.split(path)
        message = "Click to select " + repr(filename)
    return (test_result, message)

class FileSelector:

    def __init__(
        self,
        root="/",
        on_select=None,
        tester=default_tester,
        header="<em>Choose file</em>",
        button_text="choose",
        **file_chooser_options,
    ):
        self.root = root
        self.tester = tester
        self.on_select = on_select
        self.file_chooser = FileChooser(path_callback=self.path_callback, **file_chooser_options)
        self.header_html = Html(header)
        self.button = Button(button_text)
        self.gizmo = Stack(children=[self.header_html, self.button, self.file_chooser.gizmo])
        self.selected_value = None

    def get_value(self):
        return self.selected_value

    def path_callback(self, path):
        (test_result, message) = self.tester(path)
        self.header_html.text(message)
        if test_result:
            self.button.set_on_click(self.button_click)
            self.button.focus()
        else:
            self.button.set_on_click(None)
            self.selected_value = None

    def button_click(self, *ignored):
        path = self.file_chooser.current_path
        self.selected_value = path
        on_select = self.on_select
        (_, filename) = os.path.split(path)
        message = "selected: " + repr(filename)
        self.header_html.text(message)
        if on_select is not None:
            on_select(path)

    def add_as_dialog_to(self, parent_gizmo, options=None):
        if options is None:
            # default dialog options
            options = dict(height="auto", width=800, modal=True, autoOpen=False)
        dialog = parent_gizmo.add_dialog(self.gizmo, dialog_options=options)
        return dialog


class FileChooser:
    
    def __init__(
        self,
        root="/",
        label="path: ",
        path_callback=None,
        label_color="red",
        marker_color="darkgreen",
        file_marker="*&nbsp;",
        expand_state_mark = {False: ">&nbsp;", True: "V&nbsp;"},
        expand_state_color="darkorange",
    ):
        root = os.path.abspath(os.path.expanduser(root))
        assert os.path.isdir(root), "No such folder: " + repr(root)
        self.root = root
        self.path_callback = path_callback
        self.marker_color = marker_color
        self.file_marker = file_marker
        self.expand_state_mark = expand_state_mark
        self.expand_state_color = expand_state_color
        self.path_display = Input(root, size=50, readonly=True)
        label_display = Text(label, css={"color": label_color}, break_spaces=False)
        self.tree = self.path_node(root)
        self.gizmo = Stack(children=[[label_display, self.path_display], self.tree.gizmo])
        self.current_path = root

    def display_path(self, path):
        #self.path_display.text(path)
        self.current_path = path
        self.path_display.set_value(path)
        if self.path_callback is not None:
            self.path_callback(path)
        
    def path_node(self, path, parent_folder_node=None):
        if os.path.isdir(path):
            return FolderNode(path, self, parent_folder_node)
        else:
            return FileNode(path, self)


class FileNode:

    def __init__(self, path, chooser):
        assert not os.path.isdir(path), "path should not be a folder: " + repr(path)
        #assert os.path.exists(path), "path should exist: " + repr(path)
        self.path = path
        [self.parent, self.filename] = os.path.split(path)
        assert len(self.filename) > 0, "file name should not be empty: " + repr(path)
        self.chooser = chooser
        mark = chooser.file_marker
        self.marker = ClickableText("", on_click=self.click, color=chooser.marker_color)
        self.marker.html(mark)
        self.header = ClickableText(self.filename, on_click=self.click)
        #self.listing = Stack(children = [self.header])
        self.gizmo = Shelf(children = [self.marker, self.header])
    
    def click(self, *ignored):
        self.chooser.display_path(self.path)     
        
    def update_gizmo(self):
        pass


class ExceptionNode:
    
    def __init__(self, exc):
        self.gizmo = Text(" !! " + repr(exc))    
        
    def update_gizmo(self):
        pass


class FolderNode:
    
    _children = None
    
    def __init__(self, path, chooser, parent_folder_node=None):
        assert os.path.isdir(path), "path should be a folder: " + repr(path)
        self.expand_state_mark = chooser.expand_state_mark
        self.path = path
        [self.parent, self.filename] = os.path.split(path)
        self.relative_folder = self.filename + "/"
        self.chooser = chooser
        self.parent_folder_node = parent_folder_node
        self.expanded = False
        mark = self.state_mark()
        self.marker = ClickableText("", on_click=self.state_click, color=chooser.expand_state_color)
        self.marker.html(mark)
        self.header = Text(self.relative_folder)
        self.listing = Stack(children = [self.header])
        self.gizmo = Shelf(children = [self.marker, self.listing])
        
    def state_mark(self):
        return self.expand_state_mark[self.expanded]
    
    def state_click(self, *ignored):
        self.chooser.display_path(self.path)
        p = self.parent_folder_node
        siblings = []
        if p is not None:
            siblings = p.get_children()
        expanded = not self.expanded
        for sibling in siblings:
            sibling.expanded = False
        self.expanded = expanded
        if p is not None:
            for sibling in siblings:
                sibling.update_gizmo()
            p.update_gizmo()
        else:
            self.update_gizmo()
        
    def update_gizmo(self):
        self.marker.html(self.state_mark())
        if self.expanded:
            children = [self.header] + list(self.child_gizmos())
        else:
            children = [self.header]
        self.listing.attach_children(children)
        
    def child_gizmos(self):
        #return [child.gizmo for child in self.get_children()]
        result = []
        for child in self.get_children():
            g = child.gizmo
            assert g is not None, "None gizmo: " + repr(child)
            result.append(g)
        return result
        
    def get_children(self):
        children = self._children
        if children is None:
            try:
                listdir = sorted(os.listdir(self.path))
            except Exception as e:
                #children = [Text(" !! " + repr(e), break_spaces=False)]
                children = [ExceptionNode(e)]
            else:
                children = []
                for filename in listdir:
                    filepath = os.path.join(self.path, filename)
                    child = self.chooser.path_node(filepath, self)
                    children.append(child)
            self._children = children
        return children
