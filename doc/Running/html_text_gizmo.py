
from H5Gizmos import Html, serve

async def task():
    greeting = Html("<h1>text and html</h1>")
    await greeting.show()

    greeting.add("The next line shows quoted html text.")
    txt = greeting.add("dummy text")
    txt.text("<b><em> Bold and emphasized text </em></b>")

    greeting.add("The next line shows formatted html text.")
    h = greeting.add("dummy text")
    h.html("<b><em> Bold and emphasized text </em></b>")

serve(task())
