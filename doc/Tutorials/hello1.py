
from H5Gizmos import Html, Text, serve
import asyncio, time

greeting = Html("<h1>Hello</h1>")
the_time = Text("No time like the present")

async def task():
    await greeting.show()
    greeting.add(the_time)
    for i in range(60):
        await asyncio.sleep(1)
        the_time.text("%s: the time is now %s" % (i, time.ctime()))
    the_time.html("<b>Sorry, now I'm tired</b>")

serve(task())