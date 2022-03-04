
from H5Gizmos import Html, Text, Button, serve
import asyncio, time

greeting = Html("<h1>Hello</h1>")
the_time = Text("No time like the present")
clicker = Button("Click me!")
count = 0

def click_callback(*ignored):
    global count
    count += 1
    greeting.html("<em>That tickles</em>")
    the_time.text("%s: the time is now %s" % (count, time.ctime()))

clicker = Button("Click me!", on_click=click_callback)

async def task():
    await greeting.show()
    greeting.add(the_time)
    greeting.add(clicker)

serve(task())