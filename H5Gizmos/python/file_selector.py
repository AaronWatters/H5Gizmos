"""
Gizmo mechanisms for selecting a server side file.
"""

import H5Gizmos as gz
import os

def splitall(path):
    "split path into multiple components"
    [prefix, filename] = os.path.split(path)
    if not filename:
        if not prefix:
            return []
        return [prefix]
    if not prefix:
        return [filename]
    # otherwise, recursive case
    prefix_split = splitall(prefix)
    return prefix_split + [filename]

def fix_path(path):
    no_user = os.path.expanduser(path)
    return os.path.abspath(no_user)

class FileSelector:

    def __init__(self, title=None, root_folder=".", start_location="", input_width=100):
        root_folder = fix_path(root_folder)
        if title is None:
            title = "Select file from " + repr(root_folder)
        self.title = title
        self.root_folder = root_folder
        assert os.path.isdir(root_folder), "Root folder should be a directory: " + repr(root_folder)
        self.start_location = start_location
        self.current_location = start_location
        self.title_text = gz.Text(title)
        self.input_area = gz.Input(self.current_location, size=input_width)
        child = self.listing_gizmo()
        self.listing_container = gz.Stack([child])
        self.info_area = gz.Text("root: " + repr(self.root_folder))
        self.gizmo = gz.Stack([ 
            self.title_text,
            self.input_area,
            self.listing_container,
            self.info_area,
        ])
    
    def listing_gizmo(self):
        current_path = ""
        components = splitall(self.current_location)
        return self.listing_gizmo_recursive(current_path, components)

    def listing_gizmo_recursive(self, current_path, components):
        full_path = os.path.join(self.root_folder, current_path)
        is_dir = os.path.isdir(full_path)
        if not components:
            # base case
            if is_dir:
                # do a directory listing
                files = os.listdir(full_path)
                children = []
                for filename in sorted(files):
                    filepath = os.path.join(current_path, filename)
                    full_filepath = os.path.join(self.root_folder, filepath)
                    is_subdir = os.path.isdir(full_filepath)
                    selector = PathSelector(self, filename, filepath, is_subdir)
                    children.append(selector.gizmo)
                result = gz.Stack(children)
            else:
                # just list the file
                return None
        else:
            assert is_dir, "intermediate path not a dir: " + repr(full_path)
            this_component = components[0]
            next_path = os.path.join(current_path, this_component)
            next_full_path = os.path.join(self.root_folder, next_path)
            #next_is_dir = os.path.isdir(next_full_path)
            other_components = components[1:]
            sublisting = self.listing_gizmo_recursive(next_path, other_components)
            selector = PathSelector(self, this_component, current_path, is_dir=True, flag="--")
            children = [selector.gizmo]
            if sublisting is not None:
                children.append(sublisting)
            result = gz.Stack(children)
        result.css({"margin-left": "20px"})
        return result

    def set_current_path(self, to_path):
        self.current_location = to_path
        self.reset()

    def reset(self):
        to_path = self.current_location
        value = self.get_value()
        if os.path.isdir(value):
            to_path += "/"
        self.input_area.set_value(to_path)
        gizmo = self.listing_gizmo()
        self.listing_container.attach_children([gizmo])

    def get_value(self):
        return os.path.join(self.root_folder, self.current_location)

class PathSelector:

    def __init__(self, file_selector, component, current_path, is_dir=False, flag="++"):
        self.file_selector = file_selector
        self.component = component
        self.current_path = current_path
        title = repr(component)
        if is_dir:
            title += " " + flag
        self.gizmo = gz.ClickableText(title, on_click=self.callback)

    def callback(self, *ignored):
        self.file_selector.set_current_path(self.current_path)
