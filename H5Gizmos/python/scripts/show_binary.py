
from H5Gizmos import Html, Stack, Shelf, Slider, Button, serve, bytearray_to_hex
#from H5Gizmos.python.qd_file_browser import FileSelector
from H5Gizmos.python.file_selector import FileSelector

import os

def main():
    """
    Display binary file content.
    """
    serve(task(), verbose=True)

class Dumper:

    def __init__(self, filepath):
        self.filepath = filepath
        # KISS -- could be fancier for large files...
        self.filecontent = open(filepath, "rb").read()

    def size(self):
        return len(self.filecontent)

    def hexchunk(self, start, length):
        chunk = self.chunk(start, length)
        return bytearray_to_hex(chunk)

    def chunk(self, start, length):
        return self.filecontent[start: start+length]

    def display_texts(self, start, width, num_lines):
        repr_list = []
        hex_list = []
        size = self.size()
        cursor = start
        count = 0
        while cursor < size and count<num_lines:
            header = "%09d: " % cursor
            hex_list.append(header + self.hexchunk(cursor, width))
            repr_list.append(header + repr(self.chunk(cursor, width)))
            cursor = cursor + width
            count += 1
        return ("\n".join(hex_list), "\n".join(repr_list))

info = Html("<em>Please select a file</em>")
detail = Html("<b>No file selected</b>")
select_button = Button("select file")
hex_display = Html("<pre></pre>")
repr_display = Html("<pre></pre>")
repr_display.css(border="2px solid black")
dumps = Shelf(children=[hex_display, repr_display])
dashboard = Stack(children=[info, select_button, detail, dumps])

async def task():
    await dashboard.show()
    selector.add_as_dialog_to(dashboard)

def open_click(*ignored):
    selector.gizmo.open_dialog()

select_button.set_on_click(open_click)

def select_click(*ignored):
    dashboard.clear_error_message()
    path = selector.get_value()
    info.text("path: " + repr(path))
    detail.empty()
    hex_display.empty()
    repr_display.empty()
    selector.gizmo.close_dialog()
    dumper = Dumper(path)
    (dhex, drepr) = dumper.display_texts(0, 40, 50)
    size = dumper.size()
    if size > 0:
        detail.text("Size: " + str(dumper.size()))
        hex_display.text(dhex)
        repr_display.text(drepr)
    else:
        detail.text("Empty file: " + repr(path))
        hex_display.text("")
        repr_display.text("")

start = os.path.abspath(".")
selector = FileSelector(on_select=select_click, root_folder="/", start_location=start)

if __name__ == "__main__":
    main()
