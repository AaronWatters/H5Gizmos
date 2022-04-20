
from H5Gizmos import Html, serve

async def task():
    greeting = Html(
        """
        <p>
        Please check the javascript console to see
        the log message issued by the js_file_example.js
        javascript module.
        </p>
        """
    )
    greeting.js_file("./js_file_example.js")
    await greeting.show()

serve(task())
