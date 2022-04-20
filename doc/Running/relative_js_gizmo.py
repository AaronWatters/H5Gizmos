
from H5Gizmos import Html, serve

async def task():
    greeting = Html(
        """
        <p>
        Please check the javascript console to see
        the log message issued by the example_folder/relative_js_example.js
        javascript module.
        </p>
        """
    )
    greeting.serve_folder("local_files", "./example_folder")
    greeting.relative_js("local_files/relative_js_example.js")
    await greeting.show()

serve(task())
