
from H5Gizmos import Html, serve
import os

def main():
    """
    A "hello world" Gizmo script which lists the environment variables for the parent process.
    """
    serve(task(), verbose=True)

async def task():
    paragraph = Html("<h1>Hello.  Here is my environment</h1>")
    await paragraph.show()
    for (name, value) in sorted(os.environ.items()):
        paragraph.add(Html("<h4>%s</h4>" % name))
        paragraph.add(Html("<blockquote>%s</blockquote>" % repr(value)))
    paragraph.add("Goodbye.")

if __name__ == "__main__":
    main()
