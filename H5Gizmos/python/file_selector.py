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

def test_regular_file(path):
    test_result = False
    message = "Please choose a regular file."
    if os.path.isfile(path):
        test_result = True
        (_, filename) = os.path.split(path)
        message = "Click to select " + repr(filename)
    return (test_result, message)

def test_accept_any(path):
    return (True, "")

def select_any_file(
        title=None, 
        root_folder=".", 
        on_select=None,
        start_location="",
        #tester=test_regular_file,
        input_width=100,
    ):
    return FileSelector(
            title=title, 
            root_folder=root_folder, 
            on_select=on_select,
            start_location=start_location,
            tester=test_accept_any,
            input_width=input_width,
            )

class FileSelector:

    def __init__(
            self, 
            title=None, 
            root_folder=".",
            start_location="",
            on_select=None,
            tester=test_regular_file,
            input_width=100,
            button_text="Select",
            dialog_width=500,
        ):
        self.tester = tester
        self.on_select = on_select
        self.dialog_width = dialog_width
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
        value = self.get_value()
        enabled = tester(value)[0]
        self.select_button = gz.Button(button_text, on_click=self.select_file)
        self.select_button.set_enabled(enabled)
        child = self.listing_gizmo()
        self.listing_container = gz.Stack([child])
        self.info_area = gz.Text("root: " + repr(self.root_folder))
        self.gizmo = gz.Stack([ 
            self.title_text,
            [self.select_button, self.input_area],
            self.info_area,
            self.listing_container,
        ])

    def add_as_dialog_to(self, parent_gizmo, options=None):
        if options is None:
            # default dialog options
            options = dict(height="auto", width=self.dialog_width, modal=True, autoOpen=False)
        dialog = parent_gizmo.add_dialog(self.gizmo, dialog_options=options)
        return dialog

    def select_file(self, *ignored):
        value = self.get_value()
        if self.on_select is not None:
            self.on_select(value)
            self.info_area.text("selected: " + repr(value))
        else:
            self.info_area.text("no select action for " + repr(value))
    
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
            #next_full_path = os.path.join(self.root_folder, next_path)
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
        value = self.get_value()
        (enabled, msg) = self.tester(value)
        self.select_button.set_enabled(enabled)
        self.info_area.text(msg)

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
