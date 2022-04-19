
from H5Gizmos import Button, serve

async def task():
    button = Button("Click Me")
    def on_click(*ignored):
        button.add("Hi there! Thanks!")
    button.set_on_click(on_click)
    button.remote_css(
        "https://aaronwatters.github.io/visualization_prototypes/css/base.css"
    )
    await button.show()

serve(task())
