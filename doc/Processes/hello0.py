
from H5Gizmos import Html, serve

async def task():
    greeting = Html("<h1>Hello</h1>")
    await greeting.show()

serve(task())
