
from H5Gizmos import Html, serve

async def task():
    greeting = Html("""
        <div>
        A tall thin division area with red text and a yellow background.
        </div>
    """)
    greeting.resize(width=95, height=200)
    greeting.css({"color": "red", "background-color": "yellow"})
    await greeting.show()

serve(task())
