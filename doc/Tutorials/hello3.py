
from H5Gizmos import Html, Text, Button, Stack, serve
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

dashboard = Stack([
    greeting,
    [clicker, the_time]
])
dashboard.css({"justify-content": "center"})
greeting.css(color="salmon")
the_time.css(color="darkcyan")
clicker.css({"color": "darkred", "background-color": "pink"})

async def task():
    await dashboard.show()

serve(task())