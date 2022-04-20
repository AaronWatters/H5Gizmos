
from H5Gizmos import Html, serve

async def task():
    greeting = Html("""
        <h1>
        Hover over this header to see the title
        </h2>
    """)
    greeting.set_title("This is the title for the header.")
    await greeting.show()
    greeting.enable_tooltips()

serve(task())
