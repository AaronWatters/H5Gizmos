
import H5Gizmos as gz

dashboard = gz.Stack([])
dashboard.serve_folder("local_files", "./example_folder")

dog_page = """
<div>
<h3>This is a dog</h3>
<img src="local_files/dog.png" width="200" height="200"/>
</div>
"""

more_info = """
<div>
<h3>Dog</h3>
<h5>From Wikipedia, the free encyclopedia</h5>
<p>The dog (Canis familiaris or Canis lupus familiaris) is a domesticated descendant of the wolf...</p>
</div>
"""

def show_page():
    link = dashboard.launcher_link(
        "More information about dogs.", info_launcher_function)
    dashboard.attach_children([
        gz.Html(dog_page),
        link,
    ])

def info_launcher_function():
    return gz.Html(more_info)

dashboard.call_when_started(show_page)

gz.serve(dashboard.show())
