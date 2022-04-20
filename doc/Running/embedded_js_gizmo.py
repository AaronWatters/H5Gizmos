
from H5Gizmos import Html, serve

async def task():
    greeting = Html("""
        <p>
        Please check the javascript console to see
        the log message issued by the embedded javascript.
        </p>
    """)
    greeting.embedded_script('console.log("embedded javascript reporting for duty!")')
    await greeting.show()

serve(task())
