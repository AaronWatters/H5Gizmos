
from H5Gizmos import Html, serve

async def task():
    greeting = Html("""
    <div>
    <h1>This header should be brown</h1>
    But this plain text should be salmon.
    </div>
    """)
    greeting.embedded_css("""
        body {
            color: salmon;
        }
        h1 {
            color: brown;
        }
    """)
    await greeting.show()

serve(task())
